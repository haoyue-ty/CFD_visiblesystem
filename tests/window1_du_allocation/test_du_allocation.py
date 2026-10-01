"""Real frozen assets, read only. Fault injection uses memory, never source writes."""
import hashlib
import json
from pathlib import Path
from io import BytesIO

import numpy as np
import pytest

from backend.adapters import Case8AllocationAdapter
from backend.adapters.allocation import AllocationAdapterProtocol
from backend.core.errors import DomainError
from backend.models import fact_value
from backend.registry import case8_allocation as R
from backend.registry import case8_evidence as EV


ROOT = Path(r"D:\Paper\passage6")
FREEZE = ROOT / R.FREEZE_DIR


def observation():
    return {name: (hashlib.sha256((FREEZE/name).read_bytes()).hexdigest(),
                   (FREEZE/name).stat().st_size, (FREEZE/name).stat().st_mtime_ns) for name in R.ASSETS}


@pytest.fixture(scope="module", autouse=True)
def selected_scientific_sources_unchanged():
    before = observation()
    yield
    assert observation() == before


@pytest.fixture
def adapter():
    return Case8AllocationAdapter(ROOT)


def test_real_hashes_equal_formal_inventory_and_freeze_manifest(adapter):
    inventory = json.loads(Path("data/data_asset_inventory.json").read_text(encoding="utf-8"))
    rows = {row["relative_source_path"]: row for row in inventory["assets"]}
    manifest = json.loads((FREEZE/"FREEZE_MANIFEST.json").read_bytes())
    entries = {item["relative_path"]: item for item in manifest["files"]}
    evidence = adapter.load_evidence(R.EVIDENCE_ID)
    for asset in evidence.source_assets:
        row = rows[fact_value(asset.relative_origin)]
        name = asset.source_display
        assert asset.asset_id == row["asset_id"]
        assert fact_value(asset.recorded_data_hash) == row["sha256"]
        assert fact_value(asset.current_data_hash) == row["sha256"]
        assert asset.verification.status == row["status"]  # manifest is not promoted
        if name != "FREEZE_MANIFEST.json":
            assert row["sha256"] == entries[name]["sha256"]


def test_face_description_metadata_and_corrected_legacy_source(adapter, monkeypatch):
    assert isinstance(adapter, AllocationAdapterProtocol)
    description = adapter.describe_allocation("case8", "D_u")
    assert description.representation_type == "FACE_FIELD"
    assert description.measure_definition == "face integrated"
    assert "[y,x]" in description.coordinate_convention
    assert "1912" in description.definition.time_rule
    monkeypatch.setattr(np, "load", lambda *_a, **_k: pytest.fail("metadata must not decode allocation arrays"))
    result = adapter.load_allocation_metadata(R.RESULT_ID).root
    assert result.representation_type == "FACE_FIELD"
    assert [f.domain.location_type for f in result.fields] == ["CARTESIAN_X_FACE", "CARTESIAN_Y_FACE"]
    assert [f.domain.shape for f in result.fields] == [[32,129], [32,128]]
    assert [f.array_ref.descriptor.dtype for f in result.fields] == ["float64", "float64"]
    assert result.result.data_origin == "DIAGNOSTIC_RERUN"
    assert result.result.verification.status == "FROZEN_VERIFIED"
    assert result.result.time.accumulation == "TRAJECTORY_INTEGRATED"
    assert fact_value(result.result.time.interval).end == 0.08
    assert result.summary.measure.includes_time_weights is True
    assert result.summary.measure.includes_spatial_measure is False
    assert '"values":' not in result.model_dump_json()
    legacy = EV.allocation_registry_metadata()
    assert legacy["face_members"] == ["pi_at_x_faces", "pi_at_y_faces"]
    assert legacy["relative_origin"]["value"].endswith("Pi_at_trajectory_integrated.npz")
    assert legacy["allocation_adapter_status"] == "IMPLEMENTED"


@pytest.mark.parametrize("name", list(R.ARRAYS))
def test_load_verbatim_saved_array_with_shape_dtype_units_and_provenance(adapter, name):
    item = adapter.load_allocation_array(R.array_result_id(name), name)
    source_name, shape, dtype, _ = R.ARRAYS[name]
    with np.load(FREEZE/source_name, allow_pickle=False) as source:
        original = source[name]
        actual = np.array(item.values, dtype=dtype).reshape(shape)
        assert actual.tobytes() == original.tobytes()
    assert item.descriptor.shape == list(shape)
    assert item.descriptor.dtype == dtype
    assert item.result.result_id == R.array_result_id(name)
    assert item.result.provenance.registry_revision == R.REGISTRY_REVISION
    assert item.result.provenance.data_revision == R.DATA_REVISION
    assert fact_value(item.result.provenance.source_drift) is False
    assert item.result.unit.si_mapping.root.state in ("UNKNOWN", "NOT_APPLICABLE")
    if name.startswith("pi_at_"):
        field = next(f for f in adapter.load_allocation_metadata(R.RESULT_ID).root.fields if f.field_id == name)
        assert item.descriptor == field.array_ref.descriptor
        assert item.result.time == field.result.time
        assert item.result.unit == field.result.unit
        assert item.result.provenance == field.result.provenance
        assert item.result.unit.quantity == "time-integrated native-face entropy density"
    elif name.endswith("_window_mask"):
        assert item.result.unit.system == "DIMENSIONLESS"
        assert item.result.provenance.source_asset_ids == [R.MASK_ASSET_ID]
        assert item.result.time.sampling == "STATIC"
        assert item.result.time.accumulation == "NONE"
    else:
        assert item.result.unit.quantity == "length"
        assert item.result.time.sampling == "STATIC"
        assert item.result.time.accumulation == "NONE"


def test_native_face_sum_mask_fractions_and_missing_spatial_curve(adapter):
    x = np.array(adapter.load_allocation_array(R.RESULT_ID, "pi_at_x_faces").values).reshape(32,129)
    y = np.array(adapter.load_allocation_array(R.RESULT_ID, "pi_at_y_faces").values).reshape(32,128)
    mask = adapter.load_mask(R.MASK_ID)
    assert mask.domain_refs == ["case8.native-x-faces", "case8.native-y-faces"]
    xm, ym = [np.array(adapter.load_allocation_array(ref.result_id, ref.descriptor.array_id).values, dtype=bool)
              .reshape(ref.descriptor.shape) for ref in mask.mask_array_refs]
    assert [xm.sum(), ym.sum()] == [640,648]
    total = x.sum()/32 + y.sum()/128
    inside = x[xm].sum()/32 + y[ym].sum()/128
    with (FREEZE/"rerun_metrics.json").open() as stream:
        metrics = json.load(stream)
    assert abs(total-metrics["e_at_total_accum"]) <= metrics["e_at_internal_closure_abs_error"] + 1e-17
    summary = adapter.load_summary_metrics(R.RESULT_ID)
    assert fact_value(summary.total_budget.root.value.value) == metrics["e_at_total_accum"]
    assert abs(inside/total-fact_value(summary.inside.root.value.value)) < 1e-12
    assert abs(1-inside/total-fact_value(summary.outside.root.value.value)) < 1e-12
    assert summary.inside.root.value.result.unit.system == "DIMENSIONLESS"
    assert summary.total_budget.root.value.result.unit.quantity == "integrated entropy"
    assert summary.spatial_cumulative_curve.root.availability == "MISSING"
    assert not hasattr(summary.spatial_cumulative_curve.root, "value")


def test_provenance_hash_roles_freeze_processing_and_locator_privacy(adapter):
    provenance = adapter.load_provenance(R.RESULT_ID)
    evidence = provenance.evidence_records[0]
    assert fact_value(evidence.data_hash) == R.ASSETS["Pi_at_trajectory_integrated.npz"][1]
    assert fact_value(evidence.method_hash) == R.METHOD_HASH
    assert fact_value(evidence.freeze_reference).manifest_asset_id == R.ASSETS["FREEZE_MANIFEST.json"][0]
    assert len(evidence.source_observations) == len(R.ASSETS)
    assert {a.role for a in evidence.source_assets} == {"DATA", "CONFIG", "MASK", "METHOD", "ANALYSIS", "FREEZE"}
    assert evidence.processing[0].kind == "FORMAT_MAPPING"
    assert fact_value(evidence.source_drift) is False
    assert 'D:\\' not in evidence.model_dump_json()
    for name in R.ARRAYS:
        assert adapter.load_provenance(R.array_result_id(name)).result_id == R.array_result_id(name)


@pytest.mark.parametrize("config", ["A_u", "B_u", "C_u"])
def test_known_missing_configs_do_not_load_or_fabricate_maps(adapter, monkeypatch, config):
    monkeypatch.setattr(adapter, "_bundle", lambda: pytest.fail("known missing config must not read source"))
    for call in (lambda: adapter.describe_allocation("case8", config),
                 lambda: adapter.load_allocation_metadata(f"case8.{config}.allocation"),
                 lambda: adapter.load_allocation_array(f"case8.{config}.allocation", "pi_at_x_faces"),
                 lambda: adapter.load_summary_metrics(f"case8.{config}.allocation")):
        with pytest.raises(DomainError) as error:
            call()
        assert error.value.availability == "MISSING"
        assert error.value.body.code == "MISSING_SCIENTIFIC_ASSET"


@pytest.mark.parametrize("args,code", [(("gate", "Acoustic"), "UNKNOWN_EXPERIMENT"),
                                     (("case8", "invented"), "UNKNOWN_CONFIG")])
def test_unknown_identity_is_distinct_from_known_missing(adapter, args, code):
    with pytest.raises(DomainError) as error:
        adapter.describe_allocation(*args)
    assert error.value.body.code == code


@pytest.mark.parametrize("result,array", [(R.RESULT_ID, "cell"), (R.RESULT_ID, "y_cell"),
                                         (R.RESULT_ID, "x_pi_at"), ("arbitrary.path", "pi_at_x_faces"),
                                         (R.array_result_id("pi_at_x_faces"), "pi_at_y_faces")])
def test_no_cell_projection_instantaneous_member_free_path_or_mixed_identity(adapter, result, array):
    with pytest.raises(DomainError) as error:
        adapter.load_allocation_array(result, array)
    assert error.value.body.code == "INVALID_RESULT_ID"


def test_missing_source_is_typed_and_never_empty_success(tmp_path):
    with pytest.raises(DomainError) as error:
        Case8AllocationAdapter(tmp_path).load_allocation_array(R.RESULT_ID, "pi_at_x_faces")
    assert error.value.availability == "MISSING"
    assert error.value.body.code == "MISSING_SCIENTIFIC_ASSET"


@pytest.mark.parametrize("name", list(R.ASSETS))
def test_data_or_dependency_drift_blocks_numeric_load_without_source_writes(adapter, monkeypatch, name):
    original = adapter._read_bytes
    def drift(key):
        raw, stamp = original(key)
        return (raw+b"in-memory fault", stamp) if key == name else (raw, stamp)
    monkeypatch.setattr(adapter, "_read_bytes", drift)
    with pytest.raises(DomainError) as error:
        adapter.load_allocation_array(R.RESULT_ID, "pi_at_x_faces")
    assert error.value.body.code == "SOURCE_DATA_DRIFT"
    assert error.value.body.domain == "SCIENTIFIC"


def test_change_between_dependency_observations_is_rejected(adapter, monkeypatch):
    original = adapter._read_bytes
    calls = 0
    def changed(name):
        nonlocal calls
        calls += 1
        raw, stamp = original(name)
        return (raw+b"in-memory race", stamp) if calls == len(R.ASSETS)+1 else (raw, stamp)
    monkeypatch.setattr(adapter, "_read_bytes", changed)
    with pytest.raises(DomainError) as error:
        adapter.load_allocation_metadata(R.RESULT_ID)
    assert error.value.body.code == "SOURCE_CHANGED_DURING_READ"


@pytest.mark.parametrize("fault", ["shape", "dtype", "nan", "budget", "mask", "trajectory", "corrupt"])
def test_native_array_schema_and_closure_fail_closed_in_memory(adapter, fault):
    blobs, metadata, _ = adapter._bundle()
    if fault == "corrupt":
        blobs["Pi_at_trajectory_integrated.npz"] = b"invalid archive"
    else:
        with np.load(BytesIO(blobs["Pi_at_trajectory_integrated.npz"]), allow_pickle=False) as source:
            arrays = {key: source[key] for key in source.files}
        if fault == "shape":
            arrays["pi_at_x_faces"] = arrays["pi_at_x_faces"][:, :-1]
        elif fault == "dtype":
            arrays["pi_at_x_faces"] = arrays["pi_at_x_faces"].astype("float32")
        elif fault == "nan":
            arrays["pi_at_x_faces"][0,0] = np.nan
        elif fault == "budget":
            arrays["pi_at_x_faces"][0,0] += 1.0
        elif fault == "mask":
            arrays["x_window_mask"][0,0] = ~arrays["x_window_mask"][0,0]
        else:
            arrays["final_time"] = np.array(0.04)
        buffer = BytesIO()
        np.savez(buffer, **arrays)
        blobs["Pi_at_trajectory_integrated.npz"] = buffer.getvalue()
    with pytest.raises(DomainError) as error:
        adapter._decode_faces(blobs, metadata)
    assert error.value.body.code == "CANONICAL_SCHEMA_MISMATCH"


@pytest.mark.parametrize("method,args", [("describe_allocation", ("case8", "D_u")),
    ("load_allocation_metadata", (R.RESULT_ID,)), ("load_allocation_array", (R.RESULT_ID,"pi_at_x_faces")),
    ("load_mask", (R.MASK_ID,)), ("load_summary_metrics", (R.RESULT_ID,)),
    ("load_evidence", (R.EVIDENCE_ID,)), ("load_provenance", (R.RESULT_ID,))])
def test_all_methods_reject_unavailable_revision_before_reading(adapter, monkeypatch, method, args):
    monkeypatch.setattr(adapter, "_bundle", lambda: pytest.fail("unavailable revision must not read source"))
    with pytest.raises(DomainError) as error:
        getattr(adapter, method)(*args, registry_revision="other-revision")
    assert error.value.body.code == "REVISION_UNAVAILABLE"
