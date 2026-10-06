import json
import os
import socket
import time
import hashlib
import threading
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from backend.core.settings import Settings, WORKSPACE_ROOT
from backend.solver_runtime.artifacts import target, write_json, utc_now
from backend.solver_runtime.run_store import file_lock
from backend.services.v2.experiments import ExperimentError


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DeepSeekClient:
    """Bounded JSON provider with safe audit, token reservation and finite retries."""
    def __init__(self, settings: Settings, *, audit_root=None):
        self.settings = settings
        self.audit_root = audit_root or WORKSPACE_ROOT / "runtime" / "ai"
        self._slots = threading.BoundedSemaphore(2)
        self.max_retries = settings.deepseek_max_retries
        self.model = settings.deepseek_model
        self.timeout = settings.deepseek_timeout_seconds
        self.base_url = settings.deepseek_base_url.rstrip("/")
        parsed = urlsplit(self.base_url)
        if (parsed.scheme != "https" or parsed.hostname != "api.deepseek.com" or parsed.port not in (None, 443)
                or parsed.path not in ("", "/v1") or parsed.query or parsed.fragment or parsed.username):
            raise ValueError("DeepSeek endpoint must be the official HTTPS API base URL")
        # Never put secrets in Settings, a DTO, prompt, log, or the frontend.
        self._key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self._opener = build_opener(NoRedirects())

    @property
    def available(self):
        return bool(self._key)

    def complete_json(self, system: str, text: str) -> str:
        if len(system) + len(text) > self.settings.ai_max_input_chars:
            raise ExperimentError("AI_INPUT_LIMIT", "AI 上下文超过长度限制。", 413)
        if not self.available:
            raise ExperimentError("AI_UNAVAILABLE", "AI 服务未配置密钥；已有科学结果仍可使用。", 503)
        if not self._slots.acquire(blocking=False):
            raise ExperimentError("AI_BUSY", "AI 请求繁忙，请稍后重试。", 429, retryable=True)
        deadline = time.monotonic() + self.timeout
        try:
            for attempt in range(self.max_retries + 1):
                call_id = str(uuid4())
                # UTF-8 bytes conservatively bound input tokens. Reserve before
                # sending, including failed attempts: the spend cap cannot race.
                reserved = len((system + text).encode("utf-8")) + self.settings.ai_max_output_tokens + 128
                with file_lock(target(self.audit_root, "budget.lock")):
                    path = target(self.audit_root, "budget.json")
                    day = utc_now()[:10]
                    budget = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                    used = budget.get("reserved_tokens", 0) if budget.get("day_utc") == day else 0
                    refunded = set(budget.get("refunded_calls", [])) if budget.get("day_utc") == day else set()
                    # Successful provider responses report actual billed token
                    # usage. Reconcile each once; interrupted/failed attempts
                    # retain their full reservation, so capacity cannot overspend.
                    for audit in self.audit_root.glob("calls/*.json"):
                        row = json.loads(audit.read_text(encoding="utf-8"))
                        usage = row.get("usage") or {}
                        actual = usage.get("total_tokens")
                        if (row.get("status") == "SUCCESS" and row.get("created_at", "")[:10] == day
                            and row.get("call_id") not in refunded and type(actual) is int
                            and 0 <= actual <= row.get("reserved_tokens", 0)
                            and actual == usage.get("prompt_tokens", -1) + usage.get("completion_tokens", -1)):
                            used -= row["reserved_tokens"] - actual
                            refunded.add(row["call_id"])
                    if used + reserved > self.settings.ai_daily_token_budget:
                        raise ExperimentError("AI_BUDGET_LIMIT", "AI 当日 token 预算已达上限；已有结果仍可使用。", 429)
                    write_json(self.audit_root, "budget.json", dict(day_utc=day, reserved_tokens=max(0, used) + reserved, refunded_calls=sorted(refunded)))
                record = dict(call_id=call_id, model=self.model, attempt=attempt + 1, created_at=utc_now(),
                    input_sha256=hashlib.sha256((system + text).encode()).hexdigest(),
                    input_chars=len(system) + len(text), reserved_tokens=reserved, max_output_tokens=self.settings.ai_max_output_tokens,
                    status="STARTED", usage=None)
                write_json(self.audit_root, f"calls/{call_id}.json", record)
                began = time.monotonic()
                try:
                    content, usage = self._request(system, text, deadline)
                    record.update(status="SUCCESS", usage=usage)
                    return content
                except ExperimentError as error:
                    record.update(status=error.code, error_class=getattr(error, "provider_error_class", error.code), retryable=error.retryable)
                    if not error.retryable or attempt == self.max_retries or deadline - time.monotonic() < .3:
                        raise
                    time.sleep(min(.2 * (attempt + 1), max(0, deadline - time.monotonic())))
                finally:
                    record["elapsed_seconds"] = round(time.monotonic() - began, 6)
                    write_json(self.audit_root, f"calls/{call_id}.json", record)
        finally:
            self._slots.release()

    def _request(self, system, text, deadline):
        payload = {"model": self.model, "messages": [{"role": "system", "content": system},
                   {"role": "user", "content": text}], "response_format": {"type": "json_object"},
                   "thinking": {"type": "disabled"}, "max_tokens": self.settings.ai_max_output_tokens, "stream": False}
        req = Request(self.base_url + "/chat/completions", data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + self._key}, method="POST")
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            with self._opener.open(req, timeout=remaining) as response:
                # Cap output and total read time, including provider keep-alive lines.
                chunks, size = [], 0
                while True:
                    # Content-Length responses can close their socket as soon
                    # as the last byte is read; chunked responses close later.
                    if response.fp is None:
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    response.fp.raw._sock.settimeout(remaining)
                    chunk = response.read1(min(65536, 262145 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > 262144:
                        raise ValueError("Response limit")
            result = json.loads(b"".join(chunks))
            choice = result["choices"][0]
            if choice["finish_reason"] != "stop" or not isinstance(choice["message"]["content"], str):
                raise ValueError("Incomplete response")
            content = choice["message"]["content"]
            if not content.strip():
                raise ValueError("Empty response")
            usage = result.get("usage", {})
            safe_usage = {key: value for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                          if type(value := usage.get(key)) is int and value >= 0} if isinstance(usage, dict) else {}
            return content, safe_usage
        except HTTPError as error:
            # Provider response/error text may echo credentials or internal paths.
            error.close()
            failure = ExperimentError("AI_UNAVAILABLE", "AI 服务拒绝请求，请检查后端配置。", 503,
                                  retryable=error.code == 429 or error.code >= 500)
            failure.provider_error_class = "RATE_LIMIT" if error.code == 429 else "PROVIDER_5XX" if error.code >= 500 else "AUTH" if error.code in (401, 403) else "HTTP_REJECTED"
            raise failure from None
        except (TimeoutError, socket.timeout):
            failure = ExperimentError("AI_UNAVAILABLE", "AI 服务超时，请重试。", 503, retryable=True)
            failure.provider_error_class = "TIMEOUT"
            raise failure from None
        except (URLError, OSError):
            failure = ExperimentError("AI_UNAVAILABLE", "AI 服务连接失败。", 503, retryable=True)
            failure.provider_error_class = "CONNECTION"
            raise failure from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise ExperimentError("AI_INVALID_OUTPUT", "AI 服务返回了空内容或不完整响应。", 502, retryable=True) from None
