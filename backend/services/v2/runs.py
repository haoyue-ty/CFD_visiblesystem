"""P3 publishes real history and density only; P4 scientific DTO remains separate."""
import json

import numpy as np

from backend.models.v2.run import RunDensity, RunHistory, RunSnapshots, RunSnapshotMeta
from backend.services.v2.experiments import ExperimentError
from backend.solver_runtime.artifacts import sha256, target
from backend.solver_runtime.case8_adapter import PreparedRun


class RunService:
    def __init__(self, store):
        self.store = store

    def history(self, query):
        record = self.store.get(query.run_id)
        path = target(self.store.directory(record.run_id), "diagnostics/history.jsonl")
        rows = []
        if path.exists():
            # A running writer may have an incomplete last line.
            for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
                if line.endswith("\n"):
                    rows.append(json.loads(line))
        return RunHistory(rows=rows[query.offset:query.offset + query.limit], total=len(rows), offset=query.offset)

    def snapshots(self, run_id):
        record = self.store.get(run_id)
        if record.status != "COMPLETED":
            return RunSnapshots(snapshots=[], availability="PENDING")
        root = self.store.directory(run_id)
        self.store.adapter.postprocess(PreparedRun(run_id, root))
        rows = json.loads(target(root, "snapshots/index.json").read_text(encoding="utf-8"))
        if len(rows) > 6:
            raise ExperimentError("RUN_OUTPUT_INVALID", "快照数量超过登记上限。", 500)
        return RunSnapshots(availability="AVAILABLE", snapshots=[
            RunSnapshotMeta(snapshot_id=f"step_{row['step']:06d}", step=row["step"],
                            time=row["time"], cell_shape=row["cell_shape"]) for row in rows])

    def density(self, run_id, snapshot_id):
        record = self.store.get(run_id)
        if record.status != "COMPLETED":
            raise ExperimentError("RUN_RESULT_NOT_READY", "运行尚未成功完成，结果不可用。", 409)
        rows = self.snapshots(run_id).snapshots
        snapshot = next((r for r in rows if r.snapshot_id == snapshot_id), None)
        if snapshot is None:
            raise ExperimentError("SNAPSHOT_NOT_FOUND", "快照不存在。", 404)
        root = self.store.directory(run_id)
        path = target(root, f"snapshots/{snapshot_id}.npz")
        config = record.experiment.normalized_config
        with np.load(path, allow_pickle=False) as data:
            rho = data["state"][..., 0]
            if rho.shape != (config.grid.ny, config.grid.nx) or not np.all(np.isfinite(rho)) or np.min(rho) <= 0:
                raise ExperimentError("RUN_OUTPUT_INVALID", "密度数组未通过校验。", 500)
            with np.load(target(root, "initial_state.npz"), allow_pickle=False) as initial:
                x, y = initial["x"], initial["y"]
        # Source x may be broadcast mesh coordinates; expose the native cell axes.
        if x.ndim == 2:
            x = x[0, :]
        if y.ndim == 2:
            y = y[:, 0]
        return RunDensity(run_id=run_id, snapshot_id=snapshot_id, time=snapshot.time,
                          shape=list(rho.shape), axes=["y", "x"], x=x.tolist(), y=y.tolist(),
                          extent_x=list(config.grid.domain.x), extent_y=list(config.grid.domain.y),
                          values=rho.ravel(order="C").tolist(), minimum=float(rho.min()), maximum=float(rho.max()),
                          source_sha256=sha256(path))
