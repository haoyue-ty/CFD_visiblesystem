"""Compact scientific projection: never send arrays, server paths or raw files."""
from backend.models.v2.ai import EvidenceFact, ScientificAIContext
from backend.models.v2.result import ViewContextQuery
from backend.services.v2.results import ScientificResultService

BOUNDARIES = [
    "单次 Case 8 结果不能证明普适稳定性、最优系数或跨协议性能排名。",
    "E_at 较大只描述此运行的熵通道预算，不能直接判断方法更好。",
    "瞬时 Pi、全轨迹累计空间分配和累计标量 E 是不同量。",
    "未提供对照运行、误差范数、局部 face 区域统计或论文参考差值；这些结论不可用。",
    "新运行不继承历史冻结状态；模板匹配不等于复现核查成功。",
]


def build_context(store, run_id, view=None):
    service = ScientificResultService(store)
    result = service.result(run_id)
    scope = result.identity.evidence_id
    facts = []

    def add(key, label, value, unit="", definition="本 Run 的确定性结果", availability="AVAILABLE", reason=None):
        facts.append(EvidenceFact(evidence_id=f"{scope}#{key}", label=label, value=value,
            unit=unit, definition=definition, availability=availability, reason=reason))

    config = result.config.normalized_config
    for key, value in (("grid.nx", config.grid.nx), ("grid.ny", config.grid.ny),
        ("time.cfl", config.time.cfl), ("time.final_time", config.time.final_time),
        ("method.q_aa", config.method.q_aa), ("method.q_at", config.method.q_at),
        ("physics.mach", config.physics.mach), ("physics.gamma", config.physics.gamma)):
        add(key, key, value, definition="后端归一化并确认的输入，不代表性能结论")
    registered = {f.evidence_id.rsplit('#',1)[1] for f in facts}
    def numeric_leaves(value, prefix):
        if isinstance(value, dict):
            for key,item in value.items(): numeric_leaves(item, f"{prefix}.{key}" if prefix else key)
        elif isinstance(value, list):
            for index,item in enumerate(value): numeric_leaves(item, f"{prefix}.{index}")
        elif type(value) in (int,float) and prefix not in registered:
            add(prefix,prefix,value,definition="本 Run 后端确认的配置或确定性定义标量；不是性能结论")
            registered.add(prefix)
    numeric_leaves(config.model_dump(mode='json'),'')
    numeric_leaves(result.runtime.model_dump(mode='json'),'runtime')
    numeric_leaves(result.entropy.rk_weights,'entropy.rk_weights')
    numeric_leaves({k:v for k,v in result.allocation.model_dump(mode='json').items() if k!='arrays'},'allocation')
    add("identity", "新运行身份", result.identity.classification, definition=result.identity.verification)
    for key, value in result.entropy.totals.items():
        add(f"entropy.{key}", key, value, result.entropy.unit, result.entropy.cumulative_rule)
    for metric in result.metrics:
        add(f"metric.{metric.metric_id}", metric.label, metric.value, metric.unit,
            f"{metric.definition}; {metric.detector}; {metric.window}; {metric.normalization}; {metric.applicable_conditions}",
            metric.availability, metric.reason)
    add("allocation", "累计空间分配", result.allocation.availability,
        definition=result.allocation.definition, availability=result.allocation.availability, reason=result.allocation.reason)
    current = service.context(ViewContextQuery(run_id=run_id, **view.model_dump())) if view else None
    if current:
        for key in ("time", "selected_count", "minimum", "maximum", "mean"):
            value = getattr(current, key)
            add(f"view.{key}", f"{current.field} · {key}", value, current.unit if key in ("minimum", "maximum", "mean") else "",
                f"真实 cell center; snapshot={current.snapshot_id}; sha256={current.snapshot_sha256}; region={current.region}",
                "UNAVAILABLE" if value is None else "AVAILABLE", current.reason if value is None else None)
        if current.region: numeric_leaves(current.region,'view.region')
        selected=next(s for s in result.snapshots if s.snapshot_id==current.snapshot_id)
        add('view.step','所选真实快照接受步',selected.step,definition=f"{selected.snapshot_id}; t={selected.time}")
    return ScientificAIContext(run_id=run_id, result_hash=result.result_hash,
        config=config.model_dump(mode="json"), identity=result.identity.model_dump(mode="json"),
        runtime=result.runtime.model_dump(mode="json"),
        entropy={key: value for key, value in result.entropy.model_dump(mode="json").items() if key != "rows"},
        allocation={key: value for key, value in result.allocation.model_dump(mode="json").items() if key != "arrays"},
        metrics=[m.model_dump(mode="json") for m in result.metrics], current_view=current,
        limitations=list(dict.fromkeys(result.limitations + BOUNDARIES)), evidence=facts)
