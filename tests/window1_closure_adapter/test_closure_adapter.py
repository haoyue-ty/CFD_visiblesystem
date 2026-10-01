"""Real frozen Closure sources; no solver imports, reruns or source writes."""
import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.adapters.entropy_closure import EntropyClosureAdapter, EntropyClosureAdapterProtocol
from backend.core.errors import DomainError
from backend.models.closure import ClosureRunRegistry, ClosureHistory, EntropyClosureRun, RefinementSummary
from backend.models.core import fact_value
from backend.registry import closure_registry as R
from backend.services.closure import ClosureService


@pytest.fixture(scope="module")
def adapter():
    return EntropyClosureAdapter()


@pytest.fixture(scope="module")
def service(adapter):
    return ClosureService(adapter)


def value(fact):
    return fact_value(fact)


def assert_error(code, callable_, *args, **kwargs):
    with pytest.raises(DomainError) as caught:
        callable_(*args, **kwargs)
    assert caught.value.body.code == code
    assert "D:/" not in caught.value.body.model_dump_json()
    return caught.value


def raw_csv(run_id, filename):
    with (Path(R.SCIENTIFIC_ROOT) / R.run_path(run_id, filename)).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_exact_five_run_registry(service):
    registry = service.list_runs()
    assert isinstance(registry, ClosureRunRegistry)
    assert tuple(run.run_id for run in registry.runs) == R.RUN_IDS
    assert [run.step_point_count for run in registry.runs] == [3451, 6901, 13802, 27603, 13802]
    assert [run.stage_point_count for run in registry.runs] == [10353, 20703, 41406, 82809, 41406]
    assert sum(run.stage_point_count for run in registry.runs) == 196677
    assert sum(run.step_point_count for run in registry.runs) == 65559
    for run in registry.runs:
        assert isinstance(run, EntropyClosureRun)
        assert run.config.id == run.run_id
        assert {p.name: value(p.value) for p in run.config.parameters} == {
            key: R.RUNS[run.run_id][key] for key in ("CFL", "q_aa", "q_at")}
        assert value(run.config.protocol.integrator) == "SSP-RK3"
        assert run.stage_series_refs == [R.result_id(run.run_id, "stage", field) for field in R.STAGE_SERIES]
        assert run.step_series_refs == [R.result_id(run.run_id, "step", field) for field in R.STEP_SERIES]
        assert run.evidence_refs and run.config.evidence_refs


@pytest.mark.parametrize("run_id", ["B_u-cfl-0.1", "D_u-cfl-0.03", "B_u-cfl-0.2", "D_u-cfl-0.005", "D_u-cfl-0.10", "D_u-cfl-1e-2"])
@pytest.mark.parametrize("method", ["load_run", "load_stage_history", "load_step_history"])
def test_recognizable_unsupported_combinations(service, run_id, method):
    error = assert_error("UNSUPPORTED_COMBINATION", getattr(service, method), run_id)
    assert error.status == 422 and error.availability == "UNSUPPORTED"
    assert error.body.details[0].allowed_values == list(R.RUN_IDS)


@pytest.mark.parametrize("run_id", ["random-result", "Du_cfl_02", "../outputs/Du_cfl_02", "D_u-cfl-nonsense", "C_u-cfl-0.05", ""])
def test_random_run_ids(service, run_id):
    assert_error("INVALID_RESULT_ID", service.load_run, run_id)


@pytest.mark.parametrize("run_id", R.RUN_IDS)
def test_all_rows_audited_and_history_semantics(adapter, service, run_id):
    # _load audits every stage/step row, not just the requested page.
    stage, step, summary = adapter._load(run_id)
    assert len(stage) == 3 * len(step) == 3 * R.RUNS[run_id]["steps"]
    expected_stage = {"G", "D_bg", "D_aa", "D_at", "D_total", "R_SD", "eps_SD", "R_decomp"}
    expected_step = {"S_n", "S_np1", "DeltaS", "E_bg_step", "E_aa_step", "E_at_step", "E_obs_step", "R_time_step", "R_time_cumulative", "E_total_independent_step"}
    for offset in (0, 2, len(stage) - 3, len(stage), len(stage) + 10):
        history = service.load_stage_history(run_id, offset=offset, limit=4)
        assert isinstance(history, ClosureHistory)
        assert history.run_id == run_id and history.granularity == "PER_STAGE"
        assert expected_stage <= {series.series_id for series in history.series}
        for series in history.series:
            assert series.result.config_id == run_id
            assert series.result.time.sampling == "PER_STAGE" and series.result.time.accumulation == "NONE"
            assert series.aggregation == "NONE"
            assert "containing accepted step time_n" in series.result.time.index_convention
            assert "NOT_ESTABLISHED" in series.result.time.index_convention
            assert series.source_column == series.series_id
            assert series.result.unit.model_dump() == R.UNITS[R.definition(series.series_id)["unit_ref"]]
            for point in series.points:
                source = stage[point.point_index]
                interval = step[source["step"] - 1]
                assert value(point.step_index) == value(point.source_step_index) == source["step"]
                assert value(point.stage_index) == source["stage"] - 1
                assert value(point.source_stage_index) == source["stage"]
                assert value(point.physical_time) == source["t_stage_or_step_time"] == interval["time_n"]
                assert value(point.interval).model_dump() == {"start": interval["time_n"], "end": interval["time_np1"]}
                assert value(point.value) == source[series.source_column]
    for offset in (0, len(step) - 1, len(step)):
        history = service.load_step_history(run_id, offset=offset, limit=2)
        assert history.granularity == "PER_STEP"
        assert expected_step <= {series.series_id for series in history.series}
        assert set(R.STEP_SERIES) == {series.series_id for series in history.series}
        for series in history.series:
            assert series.result.time.sampling == "PER_STEP"
            assert "S_n refers to time_n" in series.result.time.index_convention
            if series.series_id.startswith("E_"):
                assert series.aggregation == "STEP_INCREMENT"
                assert series.result.time.accumulation == "STAGE_WEIGHTED_INCREMENT"
            if series.series_id == "R_time_cumulative":
                assert series.aggregation == "CUMULATIVE" and series.result.time.accumulation == "TRAJECTORY_INTEGRATED"
            if series.series_id == "R_time_step":
                assert series.aggregation == "STEP_INCREMENT" and series.result.time.accumulation == "STEP_INCREMENT"
            for point in series.points:
                source = step[point.point_index]
                assert value(point.step_index) == value(point.source_step_index) == source["step"]
                assert value(point.physical_time) == source["time_np1"]
                assert value(point.interval).start == source["time_n"]
                assert value(point.interval).end == source["time_np1"]
                assert value(point.value) == source[series.source_column]
                embedded_stage = R.definition(series.series_id).get("source_stage_index")
                assert value(point.source_stage_index) == embedded_stage
                assert value(point.stage_index) == (embedded_stage - 1 if embedded_stage else None)
    assert step[-1]["R_time_cumulative"] == summary["R_total"]
    # Independent loops check the entire audit coverage and retained independent total.
    assert all(row["R_SD"] == row["G"] + row["D_total"] for row in stage)
    # Frozen driver uses Python sum in bg/aa/at order; reassociation to chained
    # addition changes floating-point rounding (notably compensated sum in 3.12).
    assert all(row["R_decomp"] == row["D_total"] - sum(row[f"D_{c}"] for c in ("bg", "aa", "at")) for row in stage)
    assert any(row["D_total"] != row["D_bg"] + row["D_aa"] + row["D_at"] for row in stage)


def test_complete_canonical_stage_and_step_values(adapter):
    # A complete scalar page of both histories binds every raw row, with no sampled gaps.
    for run_id in R.RUN_IDS:
        raw_stage = raw_csv(run_id, "stage_closure.csv")
        history = adapter.load_stage_history(run_id, series=("R_SD",), limit=len(raw_stage))
        series = history.series[0]
        assert len(series.points) == len(raw_stage) and not series.page.has_more
        assert all(value(point.value) == float(raw["R_SD"]) and point.point_index == i for i, (point, raw) in enumerate(zip(series.points, raw_stage)))
        del raw_stage, history, series
        raw_step = raw_csv(run_id, "step_closure.csv")
        history = adapter.load_step_history(run_id, series=("R_time_cumulative",), limit=len(raw_step))
        assert all(value(point.value) == float(raw["R_time_cumulative"]) for point, raw in zip(history.series[0].points, raw_step))
        assert history.series[0].page.returned_count == len(raw_step)


def test_bu_all_recorded_zero_channels(adapter):
    run_id = "B_u-cfl-0.05"
    stage, step, summary = adapter._load(run_id)
    assert all(row["D_at"] == 0.0 for row in stage)
    assert all(row["D_at_stage1"] == row["D_at_stage2"] == row["D_at_stage3"] == row["E_at_step"] == 0.0 for row in step)
    assert summary["E_at_total"] == 0.0
    history = adapter.load_stage_history(run_id, series=("D_at",), limit=3)
    assert all(point.value.root.state == "KNOWN" and value(point.value) == 0.0 for point in history.series[0].points)


def test_refinement_is_existing_frozen_diagnostic(service):
    summary = service.load_refinement()
    assert isinstance(summary, RefinementSummary)
    assert summary.run_ids == list(R.RUN_IDS[:4])
    assert value(summary.refinement_slope.root.value.value) == 2.9999942283876795
    assert summary.refinement_slope.root.value.result.verification.status == "FROZEN_VERIFIED"
    for i, run in enumerate(summary.metrics_by_run):
        metrics = {slot.root.value.metric_id: slot.root.value for slot in run.metrics}
        assert value(metrics["R_total"].value) == R.RUNS[run.run_id]["terminal_summary"]["R_total"]
        assert value(metrics["dt_eff"].value) == R.RUNS[run.run_id]["dt"]
        if i < 3:
            assert value(metrics[f"pairwise_slope_to_{R.RUN_IDS[i + 1]}"].value) == R.SOURCE_MAP["refinement"]["pairwise_slopes"][i]["slope"]
    assert any(lim.code == "FULLY_DISCRETE_DIAGNOSTIC" and "not an exact" in lim.description for lim in summary.limitations)
    assert summary.evidence_refs == [R.REFINEMENT_EVIDENCE]


@pytest.mark.parametrize("run_id", R.RUN_IDS)
@pytest.mark.parametrize("group", ["run", "stage", "step"])
def test_all_evidence_binding(service, run_id, group):
    evidence = service.load_evidence(R.evidence_id(run_id, group))
    assert evidence.evidence_id == R.evidence_id(run_id, group)
    assert value(evidence.config_id) == run_id and value(evidence.config).id == run_id
    assert evidence.result_ids and len(evidence.result_ids) == len(evidence.result_contexts)
    assert evidence.definitions and evidence.source_assets and evidence.processing and evidence.limitations
    assert value(evidence.method_hash) == value(evidence.recorded_source_hash) == R.METHOD_HASH
    assert value(evidence.current_source_hash) == R.METHOD_HASH
    assert value(evidence.source_drift) is False
    assert value(evidence.freeze_reference).manifest_asset_id == R.ASSETS[f"{R.BASE}/FREEZE/FREEZE_MANIFEST.json"]["asset_id"]
    assert len(value(evidence.data_hash)) == 64
    assets = {asset.asset_id: asset for asset in evidence.source_assets}
    assert len(assets) == len(evidence.source_assets)
    for asset in assets.values():
        assert value(asset.recorded_data_hash) == value(asset.current_data_hash)
        assert value(asset.data_drift) is False
    assert assets[R.ASSETS[f"{R.BASE}/FREEZE/FREEZE_HASHES.sha256"]["asset_id"]].verification.status == "VERIFIED_NOT_FROZEN"
    assert {record.kind for record in evidence.processing} == {"FORMAT_MAPPING", "METADATA_CORRECTION"}
    assert all(value(record.processing_hash) and record.verification.status == "VERIFIED_NOT_FROZEN" for record in evidence.processing)
    definitions = {definition.id for definition in evidence.definitions}
    for header in evidence.result_contexts:
        assert header.config_id == run_id and header.provenance.evidence_refs == [evidence.evidence_id]
        assert set(header.scope.definition_refs) <= definitions
        assert set(header.provenance.source_asset_ids) <= set(assets)
    # Point units/definition/run remain in the canonical enclosing header and match Evidence.
    if group != "run":
        loader = service.load_stage_history if group == "stage" else service.load_step_history
        history = loader(run_id, limit=1)
        contexts = {header.result_id: header for header in evidence.result_contexts}
        for series in history.series:
            assert series.result == contexts[series.result.result_id]


def test_refinement_evidence_and_provenance(service):
    evidence = service.load_evidence(R.REFINEMENT_EVIDENCE)
    assert {header.config_id for header in evidence.result_contexts} == set(R.RUN_IDS[:4])
    asset_ids = {asset.asset_id for asset in evidence.source_assets}
    assert {R.ASSETS[R.SLOPES_PATH]["asset_id"], R.ASSETS[R.AUDIT_PATH]["asset_id"]} <= asset_ids
    assert any(record.id == "closure.frozen-slope-binding-v1" for record in evidence.processing)
    for run_id in R.RUN_IDS[:4]:
        assert R.ASSETS[R.run_path(run_id, "step_closure.csv")]["asset_id"] in asset_ids
    result_id = R.result_id(R.RUN_IDS[0], "refinement", "refinement_slope")
    provenance = service.load_provenance(result_id)
    assert provenance.evidence_records[0].evidence_id == R.REFINEMENT_EVIDENCE
    assert provenance.provenance.evidence_refs == [R.REFINEMENT_EVIDENCE]


def test_cold_provenance_and_unknown_evidence():
    service = ClosureService(EntropyClosureAdapter())
    result_id = R.result_id(R.RUN_IDS[0], "stage", "D_total")
    provenance = service.load_provenance(result_id)
    assert provenance.result_id == result_id
    assert provenance.evidence_records[0].evidence_id == R.evidence_id(R.RUN_IDS[0], "stage")
    assert_error("INVALID_RESULT_ID", service.load_provenance, "random-result")
    assert_error("UNKNOWN_EVIDENCE_ID", service.load_evidence, "ev.random")


@pytest.mark.parametrize("kwargs", [{"offset": -1}, {"offset": True}, {"limit": 0}, {"limit": "2"}])
def test_invalid_pagination(service, kwargs):
    assert_error("INVALID_REQUEST", service.load_stage_history, R.RUN_IDS[0], **kwargs)


@pytest.mark.parametrize("series", [("E_bg_cumulative",), ("R_SD", "R_SD"), (), ("S_n",)])
def test_no_unrecorded_or_wrong_granularity_series(service, series):
    assert_error("INVALID_RESULT_ID", service.load_stage_history, R.RUN_IDS[0], series=series)


def test_missing_column_never_becomes_zero():
    assert_error("MISSING_SCIENTIFIC_ASSET", EntropyClosureAdapter._csv,
        b"step,G\n1,0\n", R.STAGE_COLUMNS, integers=("step", "stage"))
    assert_error("CANONICAL_SCHEMA_MISMATCH", EntropyClosureAdapter._csv,
        b"step,G\n1,nan\n", ("step", "G"), integers=("step",))


@pytest.fixture
def relocated(tmp_path):
    adapter = EntropyClosureAdapter(tmp_path)
    for relative in adapter._deps(R.RUN_IDS[0]):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(R.SCIENTIFIC_ROOT) / relative, destination)
    return adapter


def test_missing_source_even_after_cache(relocated):
    relocated.load_run(R.RUN_IDS[0])
    (relocated._root / R.run_path(R.RUN_IDS[0], "stage_closure.csv")).unlink()
    assert_error("MISSING_SCIENTIFIC_ASSET", relocated.load_stage_history, R.RUN_IDS[0], limit=1)


def test_raw_data_drift_even_after_cache(relocated):
    relocated.load_run(R.RUN_IDS[0])
    path = relocated._root / R.run_path(R.RUN_IDS[0], "step_closure.csv")
    path.write_bytes(path.read_bytes() + b"\n")
    assert_error("SOURCE_DATA_DRIFT", relocated.load_step_history, R.RUN_IDS[0], limit=1)


def test_source_code_drift_is_separate_from_frozen_data(relocated):
    relocated.load_run(R.RUN_IDS[0])
    path = relocated._root / R.METHOD_PATH
    path.write_bytes(path.read_bytes() + b"\n# relocated test source drift\n")
    history = relocated.load_stage_history(R.RUN_IDS[0], series=("G",), limit=1)
    assert value(history.series[0].result.provenance.source_drift) is True
    evidence = relocated.load_evidence(R.evidence_id(R.RUN_IDS[0], "stage"))
    assert value(evidence.source_drift) is True
    assert value(evidence.recorded_source_hash) != value(evidence.current_source_hash)
    assert any(value(obs.drift) is True for obs in evidence.source_observations)
    assert all(value(asset.data_drift) is False for asset in evidence.source_assets if asset.role == "DATA")


def test_adapter_protocol_and_service_validation(service):
    assert isinstance(service.adapter, EntropyClosureAdapterProtocol)
    assert_error("FEATURE_NOT_ENABLED", ClosureService(None).list_runs)
    class Broken:
        def load_run(self, _):
            return {"run_id": "wrong"}
    assert_error("CANONICAL_SCHEMA_MISMATCH", ClosureService(Broken()).load_run, R.RUN_IDS[0])
    class Missing:
        def load_run(self, _):
            raise FileNotFoundError()
    assert_error("MISSING_SCIENTIFIC_ASSET", ClosureService(Missing()).load_run, R.RUN_IDS[0])


@pytest.mark.parametrize("field,group", [("R_SD", "stage"), ("R_decomp", "stage"), ("eps_SD", "stage"),
    ("D_at", "stage"), ("t_stage_or_step_time", "stage"), ("R_time_step", "step"), ("R_time_cumulative", "step"),
    ("E_obs_step", "step"), ("E_total_independent_step", "step"), ("D_bg_stage2", "step")])
def test_scientific_invariant_audit_rejects_corrupt_rows(adapter, field, group):
    stage, step, summary = adapter._load(R.RUN_IDS[0])
    stages = list(stage)
    steps = list(step)
    if group == "stage":
        stages[0] = {**stages[0], field: stages[0][field] + 1.0}
    else:
        steps[0] = {**steps[0], field: steps[0][field] + 1.0}
    assert_error("CANONICAL_SCHEMA_MISMATCH", adapter._verify, R.RUNS[R.RUN_IDS[0]], stages, steps, summary)


def test_frozen_contracts_and_sources_preserved():
    before = json.loads((R.ROOT / "docs/handoffs/phase9/WINDOW1_SOURCE_BEFORE.json").read_text(encoding="utf-8"))
    current_closure_files = {p.as_posix() for p in (Path(R.SCIENTIFIC_ROOT) / R.BASE).rglob("*") if p.is_file()}
    assert current_closure_files == {path for path in before if path.startswith(f"{R.SCIENTIFIC_ROOT}/{R.BASE}/")}
    for path, recorded in before.items():
        asset = Path(path)
        assert asset.stat().st_size == recorded["size_bytes"]
        assert hashlib.sha256(asset.read_bytes()).hexdigest() == recorded["sha256"]
    for contract in R.SOURCE_MAP["frozen_contracts"]:
        assert hashlib.sha256((R.ROOT / contract["path"]).read_bytes()).hexdigest() == contract["sha256"]


def test_phase1_asset_identity_preserved():
    inventory = json.loads((R.ROOT / "data/data_asset_inventory.json").read_text(encoding="utf-8"))
    assets = {asset["relative_source_path"]: asset for asset in inventory["assets"]}
    for path, binding in R.ASSETS.items():
        if path in assets:
            assert binding["asset_id"] == assets[path]["asset_id"]


def test_canonical_entities_forbid_extra_fields(service):
    payload = service.load_run(R.RUN_IDS[0]).model_dump(mode="python")
    payload["raw_csv"] = []
    with pytest.raises(ValidationError):
        EntropyClosureRun.model_validate(payload)
    history = service.load_stage_history(R.RUN_IDS[0], limit=1).model_dump(mode="python")
    history["series"][0]["points"][0]["stage_index"] = {"state": "KNOWN", "value": 3}
    with pytest.raises(ValidationError):
        ClosureHistory.model_validate(history)
