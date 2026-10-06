from backend.models.v2.experiment import (
    LiveCase, LiveExperimentConfig, LiveTemplate, ParameterCapability,
)

CAPABILITY_REVISION = "case8.capability.p2.1"
PROTOCOL_ID = "CANONICAL_STRONG_SHOCK_TRANSVERSE_PERTURBATION"
SOURCE_CASE = "solver/cases/flagship_cross_modal_case8.py"
SOURCE_PROTOCOL = "jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json"
SOURCE_FLUX = "solver/fluxes/cross_mode_ec_unified_v1.py"


def templates() -> list[LiveTemplate]:
    result = []
    for key, aa, at in (("A_u", 13.2, 0.0), ("B_u", 3.96, 0.0), ("C_u", 13.2, 0.396), ("D_u", 3.96, 0.396)):
        result.append(LiveTemplate(
            template_id=f"case8.paper.{key}", label=f"{key} · 论文标准配置", profile="paper",
            benchmark_status="NOT_APPLICABLE", config=LiveExperimentConfig(
                case_id="case8", profile="paper", grid={"nx": 128, "ny": 32},
                time={"cfl": 0.05, "final_time": 0.08}, method={"q_aa": aa, "q_at": at},
            ),
        ))
    result.insert(0, LiveTemplate(
        template_id="case8.fast.D_u", label="D_u · fast（已通过 P2 benchmark）", profile="fast",
        benchmark_status="PASSED", config=LiveExperimentConfig(
            case_id="case8", profile="fast", grid={"nx": 64, "ny": 16},
            time={"cfl": 0.05, "final_time": 0.04}, method={"q_aa": 3.96, "q_at": 0.396},
        ),
    ))
    return result


def case8() -> LiveCase:
    capabilities = []

    def add(path, label, support, values, unit, source, reason, scope="INPUT"):
        capabilities.append(ParameterCapability(
            field_path=path, label=label, support=support,
            verified_values=values if support == "FIXED" else [],
            candidate_values=values if support == "CANDIDATE" else [],
            unit=unit, source_refs=[source], required_stage="P2" if scope == "INPUT" else "P4",
            validation_ready=support != "UNSUPPORTED" and scope == "INPUT", scope=scope, reason=reason,
            execution_verified=support != "UNSUPPORTED",
        ))

    for path, label, values, unit, source in (
        ("method.q_aa", "q_aa", [3.96, 13.2], "model coefficient", SOURCE_FLUX),
        ("method.q_at", "q_at", [0.0, 0.396], "model coefficient", SOURCE_FLUX),
        ("grid.nx", "Nx", [64, 128], "cells", SOURCE_CASE),
        ("grid.ny", "Ny", [16, 32], "cells", SOURCE_CASE),
        ("time.final_time", "终止时间 T", [0.04, 0.08], "model time", SOURCE_PROTOCOL),
    ):
        add(path, label, "CANDIDATE", values, unit, source, "登记值已通过 P2 独立执行/参数生效核查；不构成全部组合的稳定性证明。")
    default = templates()[1].config.model_dump(mode="json")
    for group in ("physics", "discretization", "output"):
        add(group, {"physics": "物理与初始条件", "discretization": "离散与边界条件", "output": "快照策略"}[group],
            "FIXED", [default[group]], "model", SOURCE_CASE, "首期沿用完整源协议。")
    for path, label, value, unit in (
        ("physics.mach", "Mach", 6.0, "dimensionless"),
        ("physics.gamma", "γ", 1.4, "dimensionless"),
        ("grid.domain", "计算域", default["grid"]["domain"], "model length"),
        ("time.cfl", "CFL", 0.05, "dimensionless"),
        ("time.integrator", "积分器", "SSP_RK3", "none"),
        ("time.dt_strategy", "步长策略", "INITIAL_STATE_FIXED_STEP", "none"),
        ("method.method_id", "通量方法", "cross_mode_ec_unified_v1", "none"),
    ):
        add(path, label, "FIXED", [value], unit, SOURCE_PROTOCOL, "首期固定；P2 真求解与 P3 网页调度已验收。")
    for path, label, reason in (
        ("physics.epsilon", "epsilon", "Case 8 存在两种不同物理扰动；通用 epsilon 语义未确定且未支持。"),
        ("method.gate", "Gate", "目标通量没有 Gate 入参。"),
        ("discretization.higher_order", "高阶重构", "首期只支持一阶。"),
        ("output.snapshot_interval", "自由快照间隔", "新驱动及快照资源上限待实现。"),
    ):
        add(path, label, "UNSUPPORTED", [], "none", SOURCE_CASE, reason)
    for path, label in (("fields", "流场"), ("entropy", "熵预算"), ("metrics", "宏观指标"), ("allocation", "累计原生 face 空间分配")):
        add(path, label, "FIXED", [], "model", "backend/postprocess/case8.py",
            "P4 新 Run 独立结果；可用性由本 Run 实际产物决定。旧 Run 未保存累计 face 时明确不可用。", scope="OUTPUT")
    return LiveCase(
        label="Case 8 · 强激波横向扰动", capability_revision=CAPABILITY_REVISION,
        source_manifest_revision="v2-p2.1", protocol_id=PROTOCOL_ID,
        grid_pairs=[(64, 16), (128, 32)], capabilities=capabilities, templates=templates(),
        limitations=["独立 CLI 已通过 P2 真求解验收；网页提交需要后台运行服务在线。", "fast 已通过本机重复 benchmark；实际耗时取决于机器与负载，不承诺稳定性或 ETA。",
                     "论文标准配置不代表本次科学复现已成功。", "自定义仅限登记候选值及网格组合，连续范围尚未开放。"],
    )
