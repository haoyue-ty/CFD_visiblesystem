"""Verified run-scoped results, evidence, fields and deterministic view context."""
import numpy as np

from backend.models.v2.result import ScientificRunResult, RunEvidence, RunViewContext
from backend.postprocess.case8 import build_result, content_hash, field_from_snapshot, face_arrays, read
from backend.services.v2.experiments import ExperimentError
from backend.services.v2.runs import RunService
from backend.solver_runtime.artifacts import target
from backend.solver_runtime.case8_adapter import PreparedRun


class ScientificResultService:
    def __init__(self, store):
        self.store = store
        self.runs = RunService(store)

    def verified(self, run_id):
        record = self.store.get(run_id)
        if record.status != "COMPLETED":
            raise ExperimentError("RUN_RESULT_NOT_READY", "运行尚未成功完成，科学结果不可用。", 409)
        root = self.store.directory(run_id)
        try:
            self.store.adapter.postprocess(PreparedRun(run_id, root))
        except (ValueError, RuntimeError, OSError) as error:
            raise ExperimentError("RUN_OUTPUT_INVALID", "本次运行的输出或来源校验失败。", 500) from error
        return record, root

    def result(self, run_id):
        record, root = self.verified(run_id)
        try:
            path = target(root, "scientific_result.json")
            result = ScientificRunResult.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else build_result(root, read(root, "provenance.json"))
            if (result.identity.run_id != run_id or result.identity.config_hash != record.experiment.config_hash
                    or result.config != record.experiment or result.result_hash != content_hash(result.model_dump(mode="json"))):
                raise ValueError("Result identity mismatch")
            return result
        except (ValueError, KeyError, OSError) as error:
            raise ExperimentError("RUN_OUTPUT_INVALID", "科学结果未通过定义与身份校验。", 500) from error

    def evidence(self, run_id):
        result = self.result(run_id)
        root = self.store.directory(run_id)
        return RunEvidence(evidence_id=result.identity.evidence_id, result_hash=result.result_hash,
            identity=result.identity, config=result.config, effective_config=read(root, "effective_solver_config.json"),
            provenance=result.provenance, outputs=[{ "path": r["path"], "sha256": r["sha256"] } for r in read(root, "provenance.json")["outputs"]],
            supports=["本次配置与有效 Solver 参数", "本 Run 的真实数组、接受步、时间与熵积分", "已登记 detector 的宏观指标与来源哈希"],
            does_not_support=["自动继承历史 FROZEN_PRODUCTION", "仅凭论文模板宣称复现成功", "普适稳定性、最优系数或跨协议性能排名"],
            limitations=result.limitations)

    def snapshot(self, query):
        record, root = self.verified(query.run_id)
        rows = self.runs.snapshots(query.run_id).snapshots
        snapshot = next((row for row in rows if row.snapshot_id == query.snapshot_id), None)
        if snapshot is None:
            raise ExperimentError("SNAPSHOT_NOT_FOUND", "快照不存在。", 404)
        return record, root, snapshot

    def field(self, query):
        record, root, snapshot = self.snapshot(query)
        try:
            return field_from_snapshot(root, record.experiment.normalized_config, query.run_id, snapshot, query.field)
        except (ValueError, KeyError, OSError) as error:
            raise ExperimentError("RUN_OUTPUT_INVALID", "科学字段未通过校验。", 500) from error

    def faces(self, query):
        record, root, snapshot = self.snapshot(query)
        try:
            return face_arrays(root, record.experiment.normalized_config, f"snapshots/{snapshot.snapshot_id}.npz",
                               snapshot.time, snapshot.time, "INSTANTANEOUS_PI")
        except (ValueError, KeyError, OSError) as error:
            raise ExperimentError("RUN_OUTPUT_INVALID", "原生 face 字段未通过校验。", 500) from error

    def context(self, query):
        result, field = self.result(query.run_id), self.field(query)
        region = None
        values = np.asarray(field.values).reshape(field.shape)
        if query.x_min is not None:
            region = {k: getattr(query, k) for k in ("x_min", "x_max", "y_min", "y_max")}
            if not (field.extent_x[0] <= query.x_min < query.x_max <= field.extent_x[1]
                    and field.extent_y[0] <= query.y_min < query.y_max <= field.extent_y[1]):
                raise ExperimentError("INVALID_REQUEST", "区域必须位于本次计算域内。", 400)
            x, y = np.asarray(field.x), np.asarray(field.y)
            values = values[np.ix_((y >= query.y_min) & (y <= query.y_max), (x >= query.x_min) & (x <= query.x_max))]
        count = int(values.size)
        return RunViewContext(run_id=query.run_id, result_hash=result.result_hash, evidence_id=result.identity.evidence_id,
            snapshot_id=query.snapshot_id, snapshot_sha256=field.source_sha256, field=query.field, time=field.time, unit=field.unit,
            region=region, selected_count=count, availability="AVAILABLE" if count else "UNAVAILABLE",
            reason=None if count else "该区域不包含真实 cell center。", minimum=float(values.min()) if count else None,
            maximum=float(values.max()) if count else None, mean=float(values.mean()) if count else None)
