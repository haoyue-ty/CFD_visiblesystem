"""Real-source Window 1 checks; no solver import or scientific execution."""
import ast
import csv
import hashlib
import io
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from backend.adapters.cylinder import COMMON, CylinderAdapter, CylinderAdapterProtocol
from backend.core.errors import DomainError
from backend.models.core import fact_value
from backend.models.cylinder import AllocationResult, CylinderAllocationOverview
from backend.models.evidence import EvidenceRecord
from backend.registry import cylinder_registry as R
from backend.services.cylinder import CylinderService

ROOT = Path(R.SCIENTIFIC_ROOT)
WORKTREE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def adapter():
    return CylinderAdapter()


@pytest.fixture(scope="module")
def service(adapter):
    return CylinderService(adapter)


def raw_json(config, filename):
    return json.loads((ROOT / R.run_path(config, filename)).read_text(encoding="utf-8"))


def csv_rows(config):
    with (ROOT / R.run_path(config, "stage_weighted_history.csv")).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_three_real_configs_registry_and_protocol(service, adapter):
    assert isinstance(adapter, CylinderAdapterProtocol)
    configs = service.list_configs()
    assert [c.id for c in configs.items] == ["A_u", "B_u", "D_u"]
    for config in configs.items:
        assert {p.name: fact_value(p.value) for p in config.parameters} == R.MANIFEST["runs"][config.id]["parameters"]
        assert fact_value(config.protocol.final_time) == 2
        grid = fact_value(config.protocol.grid)
        assert grid.coordinate_system == "CURVILINEAR_POLAR"
        assert [d.size for d in grid.dimensions] == [32, 128]
        assert config.evidence_refs
        assert config.verification.status == "VERIFIED_NOT_FROZEN"
    experiment = service.describe_experiment()
    assert experiment.status == "PARTIAL"
    gap = next(c for c in experiment.capabilities if c.task == "cumulative-2d")
    assert gap.status == "MISSING" and gap.available_for_configs == []


@pytest.mark.parametrize("method,args", [
    ("list_snapshots", ()), ("load_snapshot_metadata", (1,)), ("load_field", (1, "radial_interior_pi_at")),
    ("load_entropy_history", ()), ("load_scalar_series", ("E_at_cumulative",)),
    ("load_allocation_overview", ()), ("load_sectors", ()), ("load_front_band", ()), ("load_metrics", ())])
def test_c_u_rejected_before_source_access(service, method, args):
    with pytest.raises(DomainError) as caught:
        getattr(service, method)("C_u", *args)
    error = caught.value
    assert (error.status, error.availability, error.body.code) == (422, "UNSUPPORTED", "UNSUPPORTED_COMBINATION")


@pytest.mark.parametrize("config", R.CONFIGS)
def test_five_snapshot_indices_native_source_step_and_time(service, config):
    snapshots = service.list_snapshots(config)
    assert snapshots.snapshot_count == 5
    assert [s.snapshot_index for s in snapshots.items] == list(range(1, 6))
    assert [s.step_index for s in snapshots.items] == list(R.STEPS)
    for snapshot in snapshots.items:
        relative = R.run_path(config, f"snapshots/native_faces_step_{snapshot.step_index:05d}.npz")
        with np.load(ROOT / relative, allow_pickle=False) as z:
            assert snapshot.physical_time == float(z["time"].item())
            assert snapshot.step_index == int(z["step"].item())
            assert fact_value(snapshot.result.time.snapshot_index) == snapshot.snapshot_index
            assert snapshot.result.time.accumulation == "NONE"
            assert len(snapshot.fields) == 12
            assert not {"pressure", "density", "velocity"} & {f.field_id for f in snapshot.fields}
            for field in snapshot.fields:
                assert field.result.time == snapshot.result.time
                assert field.domain.coordinate_system == "CURVILINEAR_POLAR"
                assert field.domain.location_type in ("CYLINDER_RADIAL_FACE", "CYLINDER_ANGULAR_FACE")
                assert field.array_ref.descriptor.shape == list(z[field.field_id].shape)
                assert field.array_ref.descriptor.dtype == "float64"
                assert field.result.provenance.evidence_refs
    assert snapshots.items[1].physical_time != .5
    assert snapshots.items[2].physical_time != 1.0
    assert snapshots.items[3].physical_time != 1.5


@pytest.mark.parametrize("index", [0, -1, 6, True, 1.0])
def test_snapshot_zero_and_unrecorded_indices_rejected(service, index):
    with pytest.raises(DomainError) as caught:
        service.load_snapshot_metadata("D_u", index)
    assert caught.value.body.code == "SNAPSHOT_NOT_FOUND"


@pytest.mark.parametrize("config", R.CONFIGS)
@pytest.mark.parametrize("index", [1, 2, 3, 4, 5])
def test_array01_native_values_and_all_saved_geometry(adapter, service, config, index):
    snapshot = service.load_snapshot_metadata(config, index)
    with np.load(ROOT / R.run_path(config, f"snapshots/native_faces_step_{snapshot.step_index:05d}.npz"), allow_pickle=False) as z:
        for field in snapshot.fields:
            response = service.load_field(config, index, field.field_id)
            assert response.field == field
            array = service.load_array(field.array_ref.result_id, field.array_ref.descriptor.array_id)
            assert array.result == field.result
            assert array.descriptor == field.array_ref.descriptor
            np.testing.assert_array_equal(array.values, z[field.field_id].ravel(order="C"))
        for family, shape in R.FAMILIES.items():
            for key in R.GEOMETRY:
                member = f"{family}_{key}"
                rid = f"{snapshot.snapshot_id}.geometry.{member}"
                ref = adapter.list_array_refs(rid)[0]
                assert ref["descriptor"]["shape"] == list(shape)
                a = service.load_array(rid, member)
                np.testing.assert_array_equal(a.values, z[member].ravel(order="C"))
                if key == "theta_face":
                    assert a.result.unit.label == "radian"
                if key.startswith("unit_normal"):
                    assert a.result.unit.system == "DIMENSIONLESS"


def test_missing_field_is_missing_not_numeric_zero(service):
    with pytest.raises(DomainError) as caught:
        service.load_field("A_u", 1, "density")
    assert caught.value.availability == "MISSING"
    assert caught.value.body.code == "MISSING_SCIENTIFIC_ASSET"


def test_partial_snapshot_missing_saved_member_is_not_synthesized(adapter, monkeypatch):
    original = adapter._npz
    def absent(relative):
        values = original(relative)
        if "snapshots/" in relative:
            del values["radial_interior_pi_at"]
        return values
    monkeypatch.setattr(adapter, "_npz", absent)
    fields = adapter.load_snapshot_metadata("D_u", 1).fields
    assert "radial_interior_pi_at" not in {f.field_id for f in fields}
    with pytest.raises(DomainError) as caught:
        adapter.load_field("D_u", 1, "radial_interior_pi_at")
    assert caught.value.availability == "MISSING"


@pytest.mark.parametrize("config", R.CONFIGS)
def test_all_9757_scalar_rows_channels_interval_units_and_numbering(service, config):
    rows = csv_rows(config)
    assert len(rows) == 9757
    history = service.load_entropy_history(config, limit=1)
    assert history.evidence_refs and len(history.series) == 4
    for channel in ("bg", "aa", "at", "total"):
        first = service.load_scalar_series(config, f"E_{channel}_cumulative", limit=5000)
        second = service.load_scalar_series(config, f"E_{channel}_cumulative", offset=5000, limit=5000)
        points = first.points + second.points
        assert first.total_point_count == second.total_point_count == len(points) == 9757
        assert first.page.has_more and not second.page.has_more
        assert first.result.time.accumulation == "TRAJECTORY_INTEGRATED"
        assert first.result.unit.label == "model integrated entropy"
        assert "INTERIOR_ONLY" in fact_value(first.result.scope.boundary_scope)
        assert first.definition_id == f"def.Cylinder_E_{channel}_cumulative"
        for i, (point, source) in enumerate(zip(points, rows)):
            assert point.point_index == i
            assert fact_value(point.source_step_index) == int(source["step"]) == i
            assert fact_value(point.step_index) == i+1
            assert fact_value(point.physical_time) == float(source["time_end"])
            interval = fact_value(point.interval)
            assert (interval.start, interval.end) == (float(source["time_start"]), float(source["time_end"]))
            assert fact_value(point.value) == float(source[f"E_{channel}_int"])
        assert fact_value(points[-1].value) == raw_json(config, "run_result.json")["channel_totals"][channel]
    assert fact_value(points[0].interval).start == 0
    assert fact_value(points[-1].physical_time) == 2


@pytest.mark.parametrize("config", R.CONFIGS)
def test_all_35_series_definitions_stage_and_increment_semantics(service, config):
    specs = R.MANIFEST["runs"][config]["history_source"]["series"]
    rows = csv_rows(config)
    assert len(specs) == 35
    for spec in specs:
        s = service.load_scalar_series(config, spec["series_id"], offset=9756, limit=1)
        p = s.points[0]
        assert s.source_column == spec["source_column"]
        assert fact_value(p.value) == float(rows[-1][s.source_column])
        assert fact_value(p.source_step_index) == 9756 and fact_value(p.step_index) == 9757
        if "stage_index" in spec:
            assert s.result.time.sampling == "PER_STAGE" and s.result.time.accumulation == "NONE"
            assert fact_value(p.stage_index) == fact_value(p.source_stage_index) == spec["stage_index"]
            assert p.physical_time.root.state == "UNKNOWN"
            if s.source_column.startswith("dotE_"):
                assert s.result.unit.label == "model integrated entropy rate"
        elif spec["accumulation"] == "PER_STEP_INCREMENT":
            assert s.aggregation == "STEP_INCREMENT"
            assert s.result.time.accumulation == "STAGE_WEIGHTED_INCREMENT"


@pytest.mark.parametrize("offset,limit", [(-1, 1), (0, 0), (0, 5001), (True, 1)])
def test_history_invalid_pages(service, offset, limit):
    with pytest.raises(DomainError) as caught:
        service.load_scalar_series("D_u", "E_at_cumulative", offset=offset, limit=limit)
    assert caught.value.body.code == "INVALID_REQUEST"


def test_history_empty_page_and_unknown_series(service):
    page = service.load_scalar_series("D_u", "E_at_cumulative", offset=10000, limit=1)
    assert page.points == [] and not page.page.has_more
    with pytest.raises(DomainError) as caught:
        service.load_scalar_series("D_u", "made_up")
    assert caught.value.body.code == "INVALID_RESULT_ID"


@pytest.mark.parametrize("config", R.CONFIGS)
def test_sectors_native_16_17_channels_canonical_sum_and_separate_units(service, config):
    sectors = service.load_sectors(config).root
    assert sectors.representation_type == "ANGULAR_SECTORS"
    assert sectors.sector_count == 16 and sectors.bin_edges.descriptor.shape == [17]
    assert sectors.result.time.sampling == "STATIC"
    assert sectors.result.time.accumulation == "TRAJECTORY_INTEGRATED"
    assert fact_value(sectors.result.scope.boundary_scope).startswith("INTERIOR_ONLY")
    assert sectors.summary.measure.includes_time_weights and sectors.summary.measure.includes_spatial_measure
    canonical = raw_json(config, "run_result.json")["channel_totals"]
    with np.load(ROOT / R.run_path(config, "spatial_cumulative.npz"), allow_pickle=False) as z:
        edges = service.load_array(sectors.bin_edges.result_id, "bin_edges")
        assert edges.result.unit.label == "radian"
        assert edges.result.time.sampling == "STATIC" and edges.result.time.accumulation == "NONE"
        assert edges.result.unit != sectors.result.unit
        np.testing.assert_array_equal(edges.values, z["bins"])
        for c in sectors.channel_arrays:
            assert c.array_ref.descriptor.shape == [16]
            array = service.load_array(c.array_ref.result_id, c.array_ref.descriptor.array_id)
            assert array.result.unit.label == "model integrated entropy"
            np.testing.assert_array_equal(array.values, z[f"channel_{c.channel}"])
            np.testing.assert_allclose(sum(array.values), canonical[c.channel], rtol=1e-13, atol=1e-14)
        if canonical["at"]:
            np.testing.assert_array_equal([fact_value(f) for f in sectors.sector_fractions], z["channel_at"]/canonical["at"])
        else:
            assert all(f.root.state == "NOT_APPLICABLE" and "value" not in f.model_dump() for f in sectors.sector_fractions)
    with pytest.raises(DomainError) as caught:
        service.load_array(sectors.result.result_id, "cumulative_2d")
    assert caught.value.availability == "MISSING"


@pytest.mark.parametrize("config", R.CONFIGS)
def test_region_scalar_fixed_a_u_mask_saved_cumulative_and_missing2d(service, config):
    overview = service.load_allocation_overview(config)
    assert isinstance(overview, CylinderAllocationOverview)
    assert overview.cumulative_2d.root.availability == "MISSING"
    assert "value" not in overview.cumulative_2d.model_dump()
    band = overview.front_band.root.value.root
    assert band.representation_type == "REGION_SCALAR"
    assert band.result.time.sampling == "STATIC" and band.result.time.accumulation == "TRAJECTORY_INTEGRATED"
    interval = fact_value(band.result.time.interval)
    assert (interval.start, interval.end) == (0, 2)
    assert band.region_mask.type == "CYLINDER_FIXED_FRONT_BAND"
    params = {p.name: fact_value(p.value) for p in band.region_mask.parameters}
    assert params["radial_half_width"] == .16 and params["reference_config"] == "A_u"
    assert "NaN outside" in band.region_mask.definition
    with np.load(ROOT / R.run_path(config, "spatial_cumulative.npz"), allow_pickle=False) as z:
        assert fact_value(band.integrated_value) == float(z["shock_at"].item())
    if config == "D_u":
        assert fact_value(band.fraction) == pytest.approx(.00777687219301986, rel=1e-13)
    else:
        assert band.fraction.root.state == "NOT_APPLICABLE"
        assert "value" not in band.fraction.model_dump()
        assert fact_value(band.integrated_value) == 0  # real stored zero remains a real zero
    for name in ("inside", "outside"):
        metric = getattr(band.summary, name).root.value
        assert metric.time_scope.accumulation == "TRAJECTORY_INTEGRATED"
        if config != "D_u":
            assert metric.value.root.state == "NOT_APPLICABLE"
    assert overview.cumulative_2d.root.error.evidence_refs == ["ev.missing.cylinder-cumulative2d"]
    missing = service.load_evidence("ev.missing.cylinder-cumulative2d")
    assert missing.verification.status == "MISSING"
    assert missing.source_assets[0].role == "MISSING_REFERENCE"
    assert missing.data_hash.root.state == "MISSING"
    assert missing.result_ids == []


@pytest.mark.parametrize("config", R.CONFIGS)
def test_metrics_exact_saved_values_definitions_detectors_units_and_floor(service, config):
    collection = service.load_metrics(config)
    saved = raw_json(config, "physical_metrics.json")
    assert len(collection.items) == len(R.METRICS) == 15
    for slot in collection.items:
        metric = slot.root.value
        key, definition, unit = R.METRICS[metric.metric_id]
        assert fact_value(metric.value) == saved[key]
        assert metric.definition_id == f"def.{metric.metric_id}"
        assert metric.result.unit.model_dump() == unit
        assert fact_value(metric.detector).evidence_refs
        assert metric.time_scope == metric.result.time
        assert metric.time_scope.sampling == "TERMINAL" and metric.time_scope.accumulation == "NONE"
        assert fact_value(metric.time_scope.physical_time) == 2
        assert metric.resolution_limit.root.state == "UNKNOWN"  # nominal dr is not an error bar
        if "width" in key and config != "A_u":
            assert any(l.code == "DETECTOR_LIMITED_SHARPNESS_READING" for l in metric.result.limitations)
            assert "not an error bar" in metric.result.limitations[0].description
    evidence = service.load_evidence(f"ev.cylinder.{config}.metrics")
    definitions = {d.id: d for d in evidence.definitions}
    assert "local_radial_spacing" in definitions["def.cylinder_front_HF_RMS"].definition
    assert definitions["def.cylinder_front_HF_RMS"].unit.system == "DIMENSIONLESS"
    assert "rfft" in definitions["def.cylinder_high_angular_energy"].definition
    assert "standard deviation" in definitions["def.cylinder_front_RMS"].definition


def test_metrics_filter_and_nonterminal_movie_rejected(service):
    assert len(service.load_metrics("D_u", metric_id="cylinder_centerline_width", snapshot_index=5).items) == 1
    with pytest.raises(DomainError) as caught:
        service.load_metrics("D_u", snapshot_index=1)
    assert caught.value.body.code == "UNSUPPORTED_COMBINATION"


@pytest.mark.parametrize("config", R.CONFIGS)
@pytest.mark.parametrize("group", ["protocol", "snapshots", "history", "sectors", "front-band", "metrics"])
def test_evidence_closure_protocol_definitions_masks_hash_and_processing(service, config, group):
    ev = f"ev.cylinder.{config}.{group}"
    record = service.load_evidence(ev)
    EvidenceRecord.model_validate_json(record.model_dump_json())
    assert record.result_ids and len(record.result_ids) == len(record.result_contexts)
    assert fact_value(record.config_id) == config
    assert fact_value(record.config).id == config
    assert fact_value(record.method_hash) == R.ASSETS[COMMON[5]]["sha256"]
    assert fact_value(record.source_drift) is False
    assets = {a.asset_id: a for a in record.source_assets}
    definitions = {d.id: d for d in record.definitions}
    for header in record.result_contexts:
        assert header.provenance.evidence_refs == [ev]
        assert set(header.provenance.source_asset_ids) <= set(assets)
        assert set(header.scope.definition_refs) <= set(definitions)
        assert header.verification.status == "VERIFIED_NOT_FROZEN"
    for asset in assets.values():
        relative = fact_value(asset.relative_origin)
        assert not relative.startswith(("D:", "C:"))
        assert fact_value(asset.current_data_hash) == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert fact_value(asset.recorded_data_hash) == fact_value(asset.current_data_hash)
        assert fact_value(asset.data_drift) is False
    assert record.processing
    assert all(p.processing_hash.root.state == "KNOWN" for p in record.processing)
    assert record.verified_at.root.state == "UNKNOWN"
    if group in ("sectors", "front-band"):
        assert record.masks and record.masks[0].id == R.MASK_ID
        assert record.masks[0].scope.definition_refs == ["def.cylinder_front_band_fraction"]
        assert any(p.kind == "VERIFIED_DERIVATION" for p in record.processing)
        assert "ev.missing.cylinder-cumulative2d" in record.related_evidence_refs
        counterpart = f"ev.cylinder.{config}.front-band" if group == "sectors" else f"ev.cylinder.{config}.sectors"
        assert counterpart in record.related_evidence_refs


def test_result_provenance_and_fresh_array_resolution():
    service = CylinderService(CylinderAdapter())
    rid = "cylinder.D_u.sectors.geometry"
    array = service.load_array(rid, "bin_edges")
    provenance = service.load_provenance(rid)
    assert provenance.provenance == array.result.provenance
    assert provenance.evidence_records[0].evidence_id == "ev.cylinder.D_u.sectors"
    assert rid in provenance.evidence_records[0].result_ids


def copied_adapter(tmp_path, filename):
    paths = set(COMMON) | {R.run_path("D_u", "run_result.json"), R.run_path("D_u", filename)}
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return CylinderService(CylinderAdapter(tmp_path))


def test_saved_source_missing_and_hash_drift_are_blocked(tmp_path):
    filename = "snapshots/native_faces_step_00000.npz"
    service = copied_adapter(tmp_path, filename)
    path = tmp_path / R.run_path("D_u", filename)
    service.load_snapshot_metadata("D_u", 1)
    path.write_bytes(path.read_bytes() + b"corruption")
    with pytest.raises(DomainError) as caught:
        service.load_snapshot_metadata("D_u", 1)
    assert caught.value.body.code == "SOURCE_DATA_DRIFT"
    path.unlink()
    with pytest.raises(DomainError) as caught:
        service.load_snapshot_metadata("D_u", 1)
    assert caught.value.availability == "MISSING"


def test_cached_history_still_checks_current_hash(tmp_path):
    service = copied_adapter(tmp_path, "stage_weighted_history.csv")
    service.load_scalar_series("D_u", "E_at_cumulative", limit=1)
    path = tmp_path / R.run_path("D_u", "stage_weighted_history.csv")
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(DomainError) as caught:
        service.load_scalar_series("D_u", "E_at_cumulative", limit=1)
    assert caught.value.body.code == "SOURCE_DATA_DRIFT"


def test_metrics_terminal_state_dependency_drift_blocks_delivery(tmp_path):
    service = copied_adapter(tmp_path, "physical_metrics.json")
    relative = R.run_path("D_u", "final_state.npz")
    state = tmp_path / relative
    shutil.copyfile(ROOT / relative, state)
    service.load_metrics("D_u")
    state.write_bytes(state.read_bytes() + b"changed-state")
    with pytest.raises(DomainError) as caught:
        service.load_metrics("D_u")
    assert caught.value.body.code == "SOURCE_DATA_DRIFT"


def test_cached_array_descriptor_does_not_bypass_source_observation(tmp_path):
    filename = "snapshots/native_faces_step_00000.npz"
    service = copied_adapter(tmp_path, filename)
    service.load_snapshot_metadata("D_u", 1)
    path = tmp_path / R.run_path("D_u", filename)
    path.write_bytes(path.read_bytes() + b"changed-checkpoint")
    with pytest.raises(DomainError) as caught:
        service.adapter.list_array_refs("cylinder.D_u.snapshot.1.radial_interior_pi_at")
    assert caught.value.body.code == "SOURCE_DATA_DRIFT"


def test_unavailable_adapter_and_source_schema_validation(service, monkeypatch):
    with pytest.raises(DomainError) as caught:
        CylinderService(None).load_metrics("D_u")
    assert caught.value.body.code == "FEATURE_NOT_ENABLED"
    with pytest.raises(ValidationError):
        AllocationResult.model_validate({**service.load_sectors("D_u").model_dump(), "sector_count": 15})
    with pytest.raises(ValidationError):
        CylinderAllocationOverview.model_validate({**service.load_allocation_overview("D_u").model_dump(),
            "cumulative_2d": {**R.MANIFEST["missing_cumulative_2d"]["ResourceSlot"], "value": {}}})


def test_independent_worktree_base_and_frozen_contracts_preserved():
    base = R.MANIFEST["phase8_base_commit"]
    assert base == "69a318b65b9378066b9a55e429dfca162cef32af"
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=WORKTREE, text=True).strip() == "phase8/cylinder-adapter"
    assert subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=WORKTREE).returncode == 0
    for relative in ("docs/03_USER_FLOW_AND_IA.md", "docs/04_SYSTEM_ARCHITECTURE.md", "docs/05_DATA_SCHEMA.md", "docs/06_API_CONTRACT.md", "config/openapi.json"):
        path = WORKTREE / relative
        expected = subprocess.check_output(["git", "show", f"{base}:{relative}"], cwd=WORKTREE)
        assert path.read_bytes().replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n")


def test_all_source_assets_hash_size_mtime_and_names_preserved():
    manifest = json.loads((WORKTREE / "docs/handoffs/phase8/WINDOW1_SOURCE_PRESERVATION.json").read_text(encoding="utf-8"))
    before = manifest["before_inventory"]
    assert len(before) == 189
    after = [{"path": item["path"], "sha256": hashlib.sha256((ROOT/item["path"]).read_bytes()).hexdigest(),
              "size_bytes": (ROOT/item["path"]).stat().st_size, "mtime_ns": (ROOT/item["path"]).stat().st_mtime_ns} for item in before]
    assert after == before
    trees = (R.BASE, "jcp_extension_v1/J2_entropy_diagnostics/J2C_S0_localization_semantics", "Paper/fig/fig_15/FREEZE")
    for relative in trees:
        observed = {p.relative_to(ROOT).as_posix() for p in (ROOT/relative).rglob("*") if p.is_file()}
        expected = {p["path"] for p in before if p["path"].startswith(relative+"/")}
        assert observed == expected
    assert not any(a["selection"] == "OFF_CONTRACT_CANDIDATE" for a in R.ASSETS.values())


def test_no_scientific_writes_or_solver_execution(service, monkeypatch):
    original_open = io.open
    def guarded(file, mode="r", *args, **kwargs):
        if isinstance(file, (str, Path)) and Path(file).resolve().is_relative_to(ROOT.resolve()):
            assert not any(flag in mode for flag in ("w", "a", "x", "+"))
        return original_open(file, mode, *args, **kwargs)
    monkeypatch.setattr(io, "open", guarded)
    service.load_allocation_overview("D_u")
    service.load_metrics("D_u")
    for module in ("backend/adapters/cylinder.py", "backend/services/cylinder.py", "backend/registry/cylinder_registry.py"):
        tree = ast.parse((WORKTREE/module).read_text(encoding="utf-8"))
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any(n and n.startswith(("solver", "diagnostics")) for n in imports)
