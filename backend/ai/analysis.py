"""Run-bound interpretation cache and stateless, selection-aware assistant."""
import hashlib
import json
import re
import math
from uuid import uuid4
from pydantic import ValidationError
from backend.ai.context_builder import build_context
from backend.ai.prompts import INTERPRET, CHAT, PROMPT_VERSION
from backend.api.catalog import _json_object, _reject_json_constant
from backend.models.v2.ai import AIAnalysis, InterpretationContent, AssistantContent
from backend.services.v2.experiments import ExperimentError
from backend.solver_runtime.artifacts import target, write_json, utc_now
from backend.solver_runtime.run_store import file_lock


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def matches_scalar(value, fact):
    if fact.availability != 'AVAILABLE' or type(fact.value) not in (int, float):
        return False
    if type(fact.value) is int or fact.value == 0:
        return value == fact.value
    return (value >= 0) == (fact.value >= 0) and math.isclose(value, fact.value, rel_tol=5e-6, abs_tol=1e-12)


def validate_prose(content, context):
    facts = {fact.evidence_id: fact for fact in context.evidence}
    claims = [content.summary, *content.key_findings, *content.observations] if isinstance(content, InterpretationContent) else content.answer
    if isinstance(content, InterpretationContent):
        if content.summary.kind != "INTERPRETATION" or any(c.kind != "FACT" for c in content.observations):
            raise ValueError("Claim category")
    for claim in claims:
        if any(ref not in facts for ref in claim.evidence_refs):
            raise ValueError("Unknown evidence")
        if claim.kind != "LIMITATION" and any(facts[ref].availability != "AVAILABLE" for ref in claim.evidence_refs):
            raise ValueError("Unavailable fact")
    # Any literal scalar must match a numeric fact cited by this very claim;
    # a valid but unrelated evidence ID cannot hide a fabricated quantity.
    texts = [c.text for c in claims] + content.limitations
    if isinstance(content, InterpretationContent):
        texts += content.suggested_questions
    for text in texts:
        numeric_text = re.sub(r"Case\s*8|SSP[-_]RK3|(?<![A-Za-z0-9])(?:V2|P[0-7])(?![A-Za-z0-9])|cross_mode_ec_unified_v1|p(?:10|50|90)|进一步|一个", "", text, flags=re.I)
        numeric_claims = [c for c in claims if c.text == text]
        for number in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", numeric_text):
            value = float(number)
            if not numeric_claims or not all(any(matches_scalar(value, facts[ref])
                for ref in c.evidence_refs) for c in numeric_claims):
                raise ValueError("Unbound numeric prose: " + number[:24] + (" / claim" if numeric_claims else " / limitation-or-question"))
        match = re.search(r"[零〇一二三四五六七八九十百千万亿两]+(?:\s*(?:倍|%|％|个|步|秒|网格|比率|比例|百分之))|百分之|[%％]", numeric_text)
        if match:
            raise ValueError("Unbound numeric prose: " + match.group()[:8])
        if re.search(r"<[^>]*>|[A-Za-z]:[\\/]|(?:sk-|Bearer\s)[A-Za-z0-9_-]+", text):
            raise ValueError("Unsafe prose")
        if isinstance(content, InterpretationContent) and text in content.suggested_questions:
            continue
        # Conservative assertion guard, permitting explicit negative boundaries.
        for match in re.finditer(r"普适稳定|普遍稳定|保证稳定|最优(?:系数|方法|配置)|最佳(?:方法|配置)|所有模态(?:均|都)?改善|universally stable|guaranteed stability|best method|all.mach robust", text, re.I):
            if not re.search(r"不能|不可|不代表|无法|不足|不证明|未证明|没有|不支持|不构成|不应|不宜|不意味|尚无|缺乏|未能|不能据此|not|cannot", text[max(0, match.start()-30):match.start()], re.I):
                raise ValueError("Unsupported universal assertion")
        if re.search(r"(?:E_at|熵耗散).{0,16}(?:越大越好|越高越好|更大.*更好)", text, re.I):
            raise ValueError("Entropy ranking")


class ScientificAIService:
    def __init__(self, store, client):
        self.store, self.client = store, client

    @property
    def model(self):
        return getattr(self.client, "model", self.store.settings.deepseek_model)

    def generate(self, context, message=None):
        payload = {"scientific_context": context.model_dump(mode="json")}
        if message is not None:
            payload["user_message"] = message
        system = CHAT if message is not None else INTERPRET
        # At most one format/evidence repair. Rejected text is untrusted data;
        # the same authoritative scientific context and all guards still apply.
        for attempt in range(2):
            raw = self.client.complete_json(system, json.dumps(payload, ensure_ascii=False, allow_nan=False))
            try:
                data = json.loads(raw, object_pairs_hook=_json_object, parse_constant=_reject_json_constant)
                content = (AssistantContent if message is not None else InterpretationContent).model_validate(data)
                validate_prose(content, context)
                break
            except (ValueError, TypeError, ValidationError) as error:
                known = {'summary','key_findings','observations','limitations','suggested_questions','answer','kind','text','evidence_refs'}
                reason = [{"type":e['type'], "loc":[p if type(p) is int or p in known else '[extra]' for p in e['loc']]} for e in error.errors()] if isinstance(error, ValidationError) else str(error) if type(error) is ValueError else type(error).__name__
                if isinstance(error, json.JSONDecodeError): reason = "INVALID_JSON"
                root = self.store.directory(context.run_id)
                write_json(root, f"ai/rejected-{uuid4()}.json", dict(created_at=utc_now(), model=self.model,
                    prompt_version=PROMPT_VERSION, output_sha256=hashlib.sha256(str(raw).encode()).hexdigest(), reason=reason, repair_attempt=attempt))
                if attempt:
                    raise ExperimentError("AI_INVALID_OUTPUT", "AI 解读未通过格式、数值或证据校验，请重试。", 502, retryable=True) from None
                system += "\n上次响应未通过，请完全重新生成，不保留旧 prose。此次必须删除所有数字字面量、百分比与中文数词数量；不要写时刻、网格数量、参数值、步数或统计数值，也不要重复用户问题中的数字。数值只通过 evidence_refs 对应的证据卡展示。例如写‘所选区域的 Mach 范围与均值见对应证据’，引用 view.minimum/view.maximum/view.mean 的完整 ID，不在 text 中填写其值。每条 claim 必须一至六个现有完整 evidence_id。缺失数据必须用 LIMITATION；summary=INTERPRETATION，observations=FACT。不猜测，不作普适或最优断言。"
                payload['validation_issue'] = reason
        return AIAnalysis(run_id=context.run_id, result_hash=context.result_hash,
            context_hash=digest(context.model_dump(mode="json")), prompt_version=PROMPT_VERSION,
            model=self.model, created_at=utc_now(), cached=False, evidence=context.evidence,
            limitations=context.limitations, current_view=context.current_view,
            interpretation=content if message is None else None, assistant=content if message is not None else None)

    def interpret(self, run_id):
        context = build_context(self.store, run_id)
        key = digest([context.result_hash, PROMPT_VERSION, self.model])
        root = self.store.directory(run_id)
        try:
            with file_lock(target(root, "ai/interpret.lock"), blocking=False):
                path = target(root, f"ai/interpret-{key}.json")
                if path.exists():
                    try:
                        cached = AIAnalysis.model_validate_json(path.read_text(encoding="utf-8"))
                        if (cached.run_id != run_id or cached.result_hash != context.result_hash or cached.model != self.model
                            or cached.prompt_version != PROMPT_VERSION or cached.context_hash != digest(context.model_dump(mode="json"))
                            or cached.evidence != context.evidence or cached.limitations != context.limitations
                            or cached.interpretation is None or cached.assistant is not None):
                            raise ValueError("Cache drift")
                        validate_prose(cached.interpretation, context)
                        return cached.model_copy(update={"cached": True})
                    except (ValueError, TypeError, ValidationError):
                        raise ExperimentError("AI_CACHE_INVALID", "缓存解读校验失败，需修复后端缓存。", 500) from None
                analysis = self.generate(context)
                write_json(root, f"ai/interpret-{key}.json", analysis.model_dump(mode="json"))
                return analysis
        except RuntimeError:
            raise ExperimentError("AI_BUSY", "该 Run 的解读正在生成，请稍后重试。", 429, retryable=True) from None

    def cached_interpretation(self, run_id):
        """Read and validate the current interpretation without contacting a provider."""
        context = build_context(self.store, run_id)
        key = digest([context.result_hash, PROMPT_VERSION, self.model])
        path = target(self.store.directory(run_id), f"ai/interpret-{key}.json")
        if not path.exists():
            return None
        try:
            cached = AIAnalysis.model_validate_json(path.read_text(encoding="utf-8"))
            if (cached.run_id != run_id or cached.result_hash != context.result_hash or cached.model != self.model
                    or cached.prompt_version != PROMPT_VERSION or cached.context_hash != digest(context.model_dump(mode="json"))
                    or cached.evidence != context.evidence or cached.limitations != context.limitations
                    or cached.interpretation is None or cached.assistant is not None or cached.current_view is not None):
                raise ValueError("Cache drift")
            validate_prose(cached.interpretation, context)
            return cached.model_copy(update={"cached": True})
        except (ValueError, TypeError, ValidationError):
            raise ExperimentError("AI_CACHE_INVALID", "缓存解读校验失败。", 500) from None

    def chat(self, body):
        if not body.message.strip():
            raise ExperimentError("INVALID_REQUEST", "请输入科研问题。", 400)
        context = build_context(self.store, body.run_id, body.view)
        analysis = self.generate(context, body.message)
        # Persist safe validated response/context identity, not user messages.
        key = digest([analysis.context_hash, body.message, self.model, PROMPT_VERSION])
        root = self.store.directory(body.run_id)
        with file_lock(target(root, "ai/chat.lock")):
            write_json(root, f"ai/chat-{key}.json", analysis.model_dump(mode="json"))
        return analysis
