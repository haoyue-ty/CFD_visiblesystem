import hashlib
import json

from backend.models.v2.experiment import (
    LiveExperimentConfig, V2FieldIssue, V2ProtocolDiff, ValidateExperimentRequest, ValidatedExperiment,
)
from backend.registry.v2.cases import CAPABILITY_REVISION, case8


class ExperimentError(Exception):
    def __init__(self, code, message, status=422, details=None, retryable=False):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
        self.details, self.retryable = details or [], retryable


def check_revision(revision: str):
    if revision != CAPABILITY_REVISION:
        raise ExperimentError("CAPABILITY_REVISION_CONFLICT", "能力版本已更新，请重新加载并验证配置。", 409)


def flatten(value, prefix=""):
    result = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


def normalize_numbers(value):
    if isinstance(value, float):
        return 0.0 if value == 0 else value
    if isinstance(value, dict):
        return {key: normalize_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_numbers(item) for item in value]
    return value


def validate_experiment(request: ValidateExperimentRequest) -> ValidatedExperiment:
    """Always call again at future Run submission; preview labels are never authority."""
    check_revision(request.submission.capability_revision)
    registry = case8()
    registered = {item.template_id: item for item in registry.templates}
    template_id = request.submission.template_id
    template = registered.get(template_id) if template_id else None
    if template_id and template is None:
        raise ExperimentError("INVALID_REQUEST", "未知实验模板。", 400,
                              [V2FieldIssue(field="submission.template_id", reason="模板未登记。")])
    if request.submission.input_mode == "template" and template is None:
        raise ExperimentError("INVALID_REQUEST", "模板入口必须指定模板。", 400)
    if request.submission.input_mode == "natural_language" and (
        not request.submission.natural_language_text or not request.submission.parser_version
    ):
        raise ExperimentError("INVALID_REQUEST", "自然语言入口需要原文与解析版本。", 400)
    payload = normalize_numbers(request.config.model_dump(mode="json"))
    flat = flatten(payload)
    unsupported = []
    for capability in registry.capabilities:
        if capability.scope != "INPUT" or not capability.validation_ready:
            continue
        value = payload
        for key in capability.field_path.split("."):
            value = value[key]
        allowed = capability.verified_values + capability.candidate_values
        if value not in allowed:
            # For fixed groups report exact changed fields, not a vague group error.
            expected = allowed[0] if allowed else None
            if isinstance(expected, dict):
                for path, original in flatten(expected, capability.field_path).items():
                    if flat[path] != original:
                        unsupported.append(V2FieldIssue(field=path, reason="首期固定值不可修改。"))
            else:
                unsupported.append(V2FieldIssue(field=capability.field_path, reason="值不在已登记的验证能力中。"))
    if unsupported:
        issues = {item.field: item for item in unsupported}
        raise ExperimentError("UNSUPPORTED_PARAMETER", "配置包含未支持的参数值。", details=list(issues.values()))
    if (payload["grid"]["nx"], payload["grid"]["ny"]) not in registry.grid_pairs:
        raise ExperimentError("UNSUPPORTED_COMBINATION", "仅登记 64×16 与 128×32 网格。",
                              details=[V2FieldIssue(field="grid", reason="混合网格组合未核查。")])
    requested_profile = request.config.profile
    differences, output_diff = [], []
    if template:
        expected = flatten(template.config.model_dump(mode="json"))
        for field, original in expected.items():
            if field in ("profile", "schema_version", "protocol_revision") or original == flat[field]:
                continue
            diff = V2ProtocolDiff(field=field, expected=original, actual=flat[field])
            (output_diff if field.startswith("output.") else differences).append(diff)
    classification = "CUSTOM_RUN"
    if template and template.profile == "paper":
        classification = "PAPER_SCALE_CUSTOM" if differences else "LIVE_PAPER_PROFILE"
    elif template and template.profile == "fast" and template.benchmark_status == "PASSED" and not differences:
        classification = "LIVE_FAST_RUN"
    warnings = list(registry.limitations[:3])
    if requested_profile == "paper" and classification != "LIVE_PAPER_PROFILE":
        warnings.append("请求 paper profile 不会赋予论文标准身份；请检查模板来源与协议差异。")
    if template and template.profile == "paper" and differences:
        warnings.append("论文模板参数已修改；按实际网格与时间展示自定义实验。")
    normalized = LiveExperimentConfig.model_validate_json(json.dumps(payload, allow_nan=False))
    hash_payload = normalized.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
    return ValidatedExperiment(
        normalized_config=normalized, requested_profile=requested_profile, classification=classification,
        protocol_diff=differences, output_diff=output_diff, warnings=warnings, unsupported_fields=[],
        config_hash=digest, capability_revision=CAPABILITY_REVISION,
    )
