"""Protocol-aware comparisons of verified live results; never rank methods."""
import math

from backend.models.v2.comparison import RunComparison
from backend.models.v2.result import RunFieldQuery
from backend.services.v2.experiments import ExperimentError
from backend.services.v2.results import ScientificResultService


def flatten(value, prefix=""):
    if isinstance(value, dict):
        return {k: v for key, item in value.items() for k, v in flatten(item, f"{prefix}.{key}" if prefix else key).items()}
    return {prefix: value}


def metric_definition(metric):
    return {key: getattr(metric, key) for key in ("unit", "definition", "detector", "window", "normalization", "applicable_conditions")}


class ComparisonService:
    def __init__(self, store):
        self.scientific = ScientificResultService(store)

    def compare(self, request):
        a, b = self.scientific.result(request.run_a), self.scientific.result(request.run_b)
        protocols = []
        for result in (a, b):
            protocol = flatten(result.config.normalized_config.model_dump(mode="json"))
            protocol.update(flatten({"provenance": {"method_sha256": result.provenance.method_sha256,
                "source_manifest_sha256": result.provenance.source_manifest_sha256,
                "postprocess_version": result.provenance.postprocess_version,
                "postprocess_sha256": result.provenance.postprocess_sha256},
                "entropy_definition": {k: getattr(result.entropy, k) for k in
                    ("unit", "rk_weights", "stage_states", "face_measure_rule", "spatial_scope", "cumulative_rule")},
                "detectors": {m.metric_id: metric_definition(m) for m in result.metrics}}))
            protocols.append(protocol)
        differences = []
        for key in sorted(protocols[0].keys() | protocols[1].keys()):
            x, y = protocols[0].get(key), protocols[1].get(key)
            if x != y:
                affects = key not in ("profile", "method.q_aa", "method.q_at") and not key.startswith("output.")
                differences.append(dict(field=key, a=x, b=y, affects_conditions=affects))
        same = not any(d["affects_conditions"] for d in differences)
        common = [(x, y) for x in a.snapshots for y in b.snapshots
                  if math.isclose(x.time, y.time, rel_tol=0, abs_tol=1e-12)]
        selected = common[-1] if common and request.snapshot_time is None else next(
            ((x, y) for x, y in common if math.isclose(x.time, request.snapshot_time or 0., rel_tol=0, abs_tol=1e-12)), None)
        if request.snapshot_time is not None and selected is None:
            raise ExperimentError("COMPARISON_TIME_UNAVAILABLE", "所选时间没有两份真实快照；请选择共同时间，不进行插值或最近帧替换。", 409)
        fa = fb = None
        low = high = None
        if selected:
            fa, fb = [self.scientific.field(RunFieldQuery(run_id=r.identity.run_id,
                snapshot_id=s.snapshot_id, field=request.field)) for r, s in zip((a, b), selected)]
            if (fa.unit, fa.definition) != (fb.unit, fb.definition):
                raise ExperimentError("COMPARISON_DEFINITION_MISMATCH", "字段单位或定义不一致，无法统一色标。", 409)
            low, high = min(fa.minimum, fb.minimum), max(fa.maximum, fb.maximum)
        metrics = []
        ma, mb = {m.metric_id: m for m in a.metrics}, {m.metric_id: m for m in b.metrics}
        for key in sorted(ma.keys() | mb.keys()):
            x, y = ma.get(key), mb.get(key)
            ref = x or y
            compatible = bool(same and x and y and metric_definition(x) == metric_definition(y)
                              and math.isclose(x.time, y.time, rel_tol=0, abs_tol=1e-12))
            available = bool(compatible and x.availability == y.availability == "AVAILABLE"
                             and x.value is not None and y.value is not None)
            reason = None if available else ("非同条件或指标定义/测量时间不一致。" if not compatible else
                "指标不可用：" + (x.reason or y.reason or "缺少有效数值。"))
            metrics.append(dict(metric_id=key, label=ref.label, unit=ref.unit, definition=ref.definition,
                comparable=available, reason=reason, a=x.value if x else None, b=y.value if y else None,
                b_minus_a=y.value-x.value if available else None))
        return RunComparison(same_conditions=same, differences=differences, a=a, b=b,
            common_snapshot_times=[x.time for x, _ in common], snapshot_time=selected[0].time if selected else None,
            field_a=fa, field_b=fb, color_min=low, color_max=high,
            field_reason=None if selected else "没有共同的真实快照时间。", metrics=metrics,
            limitations=["同条件仅表示已登记协议与科学定义一致；q_aa/q_at 是允许变化的比较因素。",
                "宏观指标取各 Run 终态；流场取所选共同真实时间，不插值。",
                "非同条件仅供并列观察，不提供指标差值。单个 Case 不支持通用性能排行榜。",
                "色标由两份原生 cell 字段的联合最小/最大值确定，网格不重采样。"])
