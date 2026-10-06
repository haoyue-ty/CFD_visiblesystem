"""Pure Run-file projections. No V1 fallback and no scientific-source imports."""
import hashlib
import json
from pathlib import Path

import numpy as np

from backend.models.v2.experiment import ValidatedExperiment
from backend.models.v2.result import ScientificRunResult, ScientificField, NativeFaceArray
from backend.solver_runtime.artifacts import sha256, target

VERSION = "case8.postprocess.p4.1"
FIELD_DEFINITIONS = {
    "density": ("Density", "model density", "rho = U[...,0]"),
    "pressure": ("Pressure", "model pressure", "p = (gamma-1)*(U[...,3] - (U[...,1]^2+U[...,2]^2)/(2*rho))"),
    "velocity_x": ("Velocity x", "model velocity", "u = U[...,1]/rho"),
    "velocity_y": ("Velocity y", "model velocity", "v = U[...,2]/rho"),
    "speed": ("Speed", "model velocity", "speed = sqrt(u^2+v^2)"),
    "mach": ("Mach", "dimensionless", "Mach = speed/sqrt(gamma*p/rho)"),
}
ALLOCATION_RULE = "A_channel(face)=sum_steps dt*sum_stages w_s*Pi_channel(U_s,face); E=dy*sum(A_x)+dx*sum(A_y); no face-to-cell conversion"


def read(root, name):
    return json.loads(target(root, name).read_text(encoding="utf-8"))


def content_hash(value):
    payload = dict(value)
    payload.pop("result_hash", None)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def primitive_fields(state, gamma):
    if state.ndim != 3 or state.shape[-1] != 4 or not np.all(np.isfinite(state)):
        raise ValueError("Invalid conservative state")
    rho = state[..., 0]
    if np.any(rho <= 0):
        raise ValueError("Nonpositive density")
    p = (gamma - 1) * (state[..., 3] - (state[..., 1] ** 2 + state[..., 2] ** 2) / (2 * rho))
    if np.any(p <= 0) or not np.all(np.isfinite(p)):
        raise ValueError("Nonpositive pressure")
    u, v = state[..., 1] / rho, state[..., 2] / rho
    speed = np.sqrt(u * u + v * v)
    fields = dict(density=rho, pressure=p, velocity_x=u, velocity_y=v, speed=speed,
                  mach=speed / np.sqrt(gamma * p / rho))
    if any(not np.all(np.isfinite(a)) for a in fields.values()):
        raise ValueError("Nonfinite derived field")
    return fields


def cell_axes(root, config):
    with np.load(target(root, "initial_state.npz"), allow_pickle=False) as data:
        x, y = data["x"], data["y"]
    x = x[0, :] if x.ndim == 2 else x
    y = y[:, 0] if y.ndim == 2 else y
    if x.shape != (config.grid.nx,) or y.shape != (config.grid.ny,):
        raise ValueError("Coordinate shape mismatch")
    expected_x = config.grid.domain.x[0] + (np.arange(config.grid.nx) + .5) * np.diff(config.grid.domain.x)[0] / config.grid.nx
    expected_y = config.grid.domain.y[0] + (np.arange(config.grid.ny) + .5) * np.diff(config.grid.domain.y)[0] / config.grid.ny
    if not np.allclose(x, expected_x, rtol=0, atol=1e-14) or not np.allclose(y, expected_y, rtol=0, atol=1e-14):
        raise ValueError("Coordinate values mismatch")
    return x, y


def field_from_snapshot(root, config, run_id, snapshot, field):
    path = target(root, f"snapshots/{snapshot.snapshot_id}.npz")
    with np.load(path, allow_pickle=False) as data:
        state = data["state"]
        if state.shape != (config.grid.ny, config.grid.nx, 4):
            raise ValueError("Snapshot shape mismatch")
        if int(data["step"]) != snapshot.step or float(data["time"]) != snapshot.time:
            raise ValueError("Snapshot time mismatch")
        values = primitive_fields(state, config.physics.gamma)[field]
    x, y = cell_axes(root, config)
    label, unit, definition = FIELD_DEFINITIONS[field]
    return ScientificField(run_id=run_id, snapshot_id=snapshot.snapshot_id, field_id=field, label=label,
                           time=snapshot.time, shape=list(values.shape), axes=["y", "x"], x=x.tolist(), y=y.tolist(),
                           extent_x=list(config.grid.domain.x), extent_y=list(config.grid.domain.y), unit=unit,
                           definition=definition + "; conservative snapshot; C order y then x", values=values.ravel().tolist(),
                           minimum=float(values.min()), maximum=float(values.max()), source_sha256=sha256(path))


def face_arrays(root, config, relative, start, end, quantity):
    nx, ny = config.grid.nx, config.grid.ny
    dx, dy = np.diff(config.grid.domain.x)[0] / nx, np.diff(config.grid.domain.y)[0] / ny
    xc, yc = cell_axes(root, config)
    xf = config.grid.domain.x[0] + np.arange(nx + 1) * dx
    yf = config.grid.domain.y[0] + np.arange(ny) * dy
    path = target(root, relative)
    result = []
    with np.load(path, allow_pickle=False) as data:
        for axis, shape, x, y, axes, location, measure in (
            ("x_faces", (ny, nx + 1), xf, yc, ["y_cell", "x_face"], "CARTESIAN_X_FACE", dy),
            ("y_faces", (ny, nx), xc, yf, ["y_face", "x_cell"], "CARTESIAN_Y_FACE", dx),
        ):
            for channel in ("bg", "aa", "at"):
                key = f"{axis}_pi_{channel}"
                values = data[key]
                if values.shape != shape or not np.all(np.isfinite(values)):
                    raise ValueError("Native face array shape/finite mismatch")
                result.append(NativeFaceArray(array_id=f"{quantity}.{key}", label=f"{channel} · {axis}", channel=channel,
                    location_type=location, quantity=quantity, shape=list(shape), axes=axes, x=x.tolist(), y=y.tolist(),
                    unit="model entropy / face measure" if quantity == "CUMULATIVE_SPATIAL_ALLOCATION" else "model entropy / time / face measure",
                    face_measure=float(measure), time_start=start, time_end=end, values=values.ravel().tolist(), source_sha256=sha256(path)))
    return result


def build_result(root: Path, provenance):
    validated = ValidatedExperiment.model_validate_json(target(root, "config.json").read_text(encoding="utf-8"))
    config = validated.normalized_config
    summary, effective = read(root, "result.json"), read(root, "effective_solver_config.json")
    if summary["config_hash"] != validated.config_hash or effective["normalized_config"] != config.model_dump(mode="json"):
        raise ValueError("Scientific configuration mismatch")
    run_id = summary["run_id"]
    evidence_id = f"ev.run.{run_id}"
    history_path = target(root, "diagnostics/history.jsonl")
    history = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines()]
    if len(history) != summary["accepted_steps"] or not history:
        raise ValueError("History length mismatch")
    cumulative = {f"E_{c}": 0.0 for c in ("bg", "aa", "at", "total")}
    for i, row in enumerate(history):
        if row["step"] != i or not np.isclose(row["time_end"], (i + 1) * summary["dt"], rtol=0, atol=1e-14):
            raise ValueError("History step/time mismatch")
        for key in cumulative:
            increment = row["dt"] * sum(w * row[f"dot{key}_s{s}"] for s, w in enumerate((1/6, 1/6, 2/3)))
            cumulative[key] += increment
            if not np.isclose(row[f"delta{key}"], increment, rtol=1e-12, atol=1e-13) or not np.isclose(row[key], cumulative[key], rtol=1e-12, atol=1e-13):
                raise ValueError("History RK weighting mismatch")
    if any(not np.isclose(cumulative[k], summary["channel_totals"][k], rtol=1e-12, atol=1e-13) for k in cumulative):
        raise ValueError("Entropy total mismatch")
    arrays = None
    totals = None
    allocation_error = None
    allocation_path = target(root, "derived/cumulative_faces.npz")
    recorded_paths = {row["path"] for row in provenance["outputs"]}
    if "derived/cumulative_faces.npz" in recorded_paths:
        arrays = face_arrays(root, config, "derived/cumulative_faces.npz", 0.0, summary["final_time"], "CUMULATIVE_SPATIAL_ALLOCATION")
        totals = {f"E_{c}": sum(a.face_measure * sum(a.values) for a in arrays if a.channel == c) for c in ("bg", "aa", "at")}
        allocation_error = max(abs(totals[k] - cumulative[k]) for k in totals)
        if any(not np.isclose(totals[k], cumulative[k], rtol=1e-10, atol=1e-12) for k in totals):
            raise ValueError("Spatial allocation/scalar entropy mismatch")
    metric_specs = (
        ("front_width_mean", "Shock width", "model length", "mean valid row-local p90-p10 crossing distance, p50 anchored nearest intended front", "all rows; nearest p50 to initial corrugated front, nearest p10/p90 to p50", "none"),
        ("front_rms", "Front RMS", "model length", "sqrt(mean((x50 - mean(valid x50))^2)) over valid rows", "same local p10/p50/p90 detector as Shock width", "mean-subtracted front"),
        ("front_high_k_fraction", "HF (front)", "dimensionless", "sum |rfft(front displacement)/Ny|^2 for k>4 / sum for k>=1; 0 when denominator=0", "entire periodic y; source replaces missing front rows by zero for spectrum", "rfft / Ny; energy fraction; no extra factor of two"),
    )
    with np.load(target(root, "derived/physical_fields.npz"), allow_pickle=False) as physical:
        valid_rows = int(np.count_nonzero(np.isfinite(physical["front"])))
    metrics = []
    for key, label, unit, definition, window, normalization in metric_specs:
        value = summary["physical_metrics"].get(key)
        reason = None
        if valid_rows == 0 or value is None or not np.isfinite(value):
            value, reason = None, "没有可用的局部前沿检测结果。"
        elif key == "front_high_k_fraction" and valid_rows != config.grid.ny:
            value, reason = None, "存在缺失前沿行；源谱的补零结果不作为可用 HF 结论。"
        metrics.append(dict(metric_id=key, label=label, value=value, availability="AVAILABLE" if value is not None else "UNAVAILABLE",
            reason=reason, unit=unit, definition=definition, detector="solver.diagnostics.flagship_cross_modal_case8.local_front_widths / spectral_content",
            window=window, normalization=normalization,
            applicable_conditions=f"stationary Case8 Mach6, gamma1.4, MODE4; valid front rows {valid_rows}/{config.grid.ny}; first order; no universal stability inference",
            time=summary["final_time"], resolution_limit=1.0/config.grid.nx if unit == "model length" else None, evidence_id=evidence_id))
    method = next(row for row in provenance["loaded_modules"] if row["module"] == "solver.fluxes.cross_mode_ec_unified_v1")
    software = provenance["software"]
    postprocess_hash = next((row["sha256"] for row in software if row["path"] == "backend/postprocess/case8.py"), sha256(Path(__file__)))
    limitations = ["本次新建 V2 运行，不继承历史冻结状态；配置匹配不等于论文复现通过。",
        "模型单位尚无 SI 标定；宏观指标仅适用于登记的 Case8 detector。",
        "瞬时 Pi、全轨迹累计空间分配和累计标量 E 是不同科学量；face 数组保留原生几何。",
        "快照仅含真实保存的帧；播放不插值；熵历史包含所有真实接受步。",
        "较大的 E_at 不直接代表方法更好；本结果不证明普适稳定性或最优系数。"]
    if arrays is None:
        limitations.append("旧 Run 未保存全轨迹累计 face 数据，该空间分配不可用。")
    result = dict(result_hash="", identity=dict(run_id=run_id, result_id=f"result.run.{run_id}", evidence_id=evidence_id,
        config_hash=validated.config_hash, classification=validated.classification, verification=summary["verification"]),
        config=validated, runtime=dict(started_at=summary["started_at"], finished_at=summary["finished_at"],
        accepted_steps=summary["accepted_steps"], final_time=summary["final_time"], dt=summary["dt"],
        **{k: summary["runtime"][k] for k in ("wall_seconds", "solver_seconds", "peak_rss_bytes")}),
        fields=[dict(field_id=k, label=v[0], unit=v[1], definition=v[2]) for k, v in FIELD_DEFINITIONS.items()],
        snapshots=[dict(snapshot_id=f"step_{r['step']:06d}", step=r["step"], time=r["time"], cell_shape=r["cell_shape"])
                   for r in read(root, "snapshots/index.json")],
        entropy=dict(unit="model entropy", rk_weights=[1/6, 1/6, 2/3], stage_states=["U_n", "U_1", "U_2"],
            face_measure_rule="dy*sum(Pi_x)+dx*sum(Pi_y)", spatial_scope=effective["observer"]["scope"],
            cumulative_rule="E_c(n+1)=E_c(n)+dt*sum_s w_s*dotE_c(U_s)", rows=history, totals=cumulative, source_sha256=sha256(history_path)),
        metrics=metrics, allocation=dict(availability="AVAILABLE" if arrays is not None else "UNAVAILABLE",
            reason=None if arrays is not None else "该 Run 未记录全轨迹累计 face 数据；终态 Pi 不能替代。",
            arrays=None if arrays is None else [a.model_dump(mode="json") for a in arrays], scalar_totals=totals,
            definition=ALLOCATION_RULE, max_scalar_abs_error=allocation_error), limitations=limitations,
        provenance=dict(method_id=config.method.method_id, method_sha256=method["sha256"],
            source_manifest_revision=provenance["source_manifest_revision"], source_manifest_sha256=provenance["source_manifest_sha256"],
            dependencies=[dict(path=r["path"], sha256=r["sha256"]) for r in provenance["loaded_modules"]],
            software=software, postprocess_version=VERSION, postprocess_sha256=postprocess_hash,
            solver_result_sha256=sha256(target(root, "result.json")), effective_config_sha256=sha256(target(root, "effective_solver_config.json")),
            outputs=[dict(path=r["path"], sha256=r["sha256"]) for r in provenance["outputs"]]))
    model = ScientificRunResult.model_validate(result)
    model.result_hash = content_hash(model.model_dump(mode="json"))
    return model
