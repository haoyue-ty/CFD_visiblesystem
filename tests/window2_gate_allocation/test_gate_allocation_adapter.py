"""Window 2 adapter-level verification: gate allocation data access.

Exercises the real read-only frozen Experiment 1 package. Asserts the four
window DoD items:
  * 3 gates available (exactly Acoustic/Pressure/Ungated);
  * array shape correct (32x128 float64, C-order [y,x]);
  * metadata correct (CELL_FIELD, STATIC+TRAJECTORY_INTEGRATED, cell-centered);
  * missing asset handling (typed, distinct errors, no empty success).

These tests never modify the scientific root, never interpolate q_at, never
fabricate a fourth gate, and never convert the cell field to faces.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from backend.adapters.allocation import AllocationAdapterProtocol
from backend.adapters.gate_allocation import GateAllocationAdapter
from backend.core.errors import DomainError
from backend.registry import gate_registry as G

GATES = ("Acoustic", "Pressure", "Ungated")
CELL_SHAPE = [32, 128]


@pytest.fixture(scope="module")
def adapter() -> GateAllocationAdapter:
    root = Path(G.SCIENTIFIC_ROOT_WINDOWS)
    if not root.exists():
        pytest.skip("scientific root not present on this host")
    return GateAllocationAdapter(root)


def _pi_at_path(root: Path, config_id: str) -> Path:
    return root / G.GATE_FREEZE_REL / "results_snapshot" / config_id / "Pi_at.npy"


# =========================================================== 3 gates available
def test_exactly_three_gates(adapter):
    gates = adapter.list_gates()
    assert gates == GATES
    assert len(gates) == 3
    assert len(set(gates)) == 3


@pytest.mark.parametrize("config_id", GATES)
def test_every_gate_loads_allocation(adapter, config_id):
    metadata = adapter.load_allocation_metadata(f"gate.{config_id}.allocation")
    array = adapter.load_allocation_array(f"gate.{config_id}.allocation", "allocation_at")
    summary = adapter.load_summary_metrics(f"gate.{config_id}.allocation")
    assert metadata.root.representation_type == "CELL_FIELD"
    assert metadata.root.result.config_id == config_id
    assert len(array.values) == 4096
    assert summary.total_budget.root.availability == "AVAILABLE"


def test_no_fourth_gate_is_created(adapter):
    # Well-formed but unregistered gate ids are rejected with a typed error.
    for ghost in ("Gated", "Reference", "None", "acoustic", "Acoustic2"):
        with pytest.raises(DomainError) as excinfo:
            adapter.load_allocation_metadata(f"gate.{ghost}.allocation")
        assert excinfo.value.body.code in ("UNKNOWN_CONFIG", "UNSUPPORTED_COMBINATION")
    # Ids that violate the canonical ID grammar never become a resource identity.
    with pytest.raises(ValidationError):
        adapter.load_allocation_metadata("gate.Acoustic .allocation")


def test_matched_qat_only_the_three_frozen_values(adapter):
    observed = {}
    for config_id in GATES:
        facts = adapter._read_gate_facts(config_id)
        observed[config_id] = facts.q_at
    assert observed == G.MATCHED_QAT
    # The matched values are not interpolated from a grid.
    assert observed["Acoustic"] == 0.4
    assert observed["Pressure"] == 0.31018332312583474
    assert observed["Ungated"] == 0.03483470441226932


# ======================================================== array shape correct
@pytest.mark.parametrize("config_id", GATES)
def test_array_shape_and_dtype(adapter, config_id):
    array = adapter.load_allocation_array(f"gate.{config_id}.allocation", "allocation_at")
    assert array.descriptor.shape == CELL_SHAPE
    assert array.descriptor.dtype == "float64"
    assert array.descriptor.order == "C"
    assert array.descriptor.axes == ["y", "x"]
    assert array.descriptor.element_count == 4096
    assert len(array.values) == array.descriptor.element_count


@pytest.mark.parametrize("config_id", GATES)
def test_array_matches_saved_npy_elementwise(adapter, config_id):
    array = adapter.load_allocation_array(f"gate.{config_id}.allocation", "allocation_at")
    saved = np.load(_pi_at_path(adapter._root, config_id), allow_pickle=False)
    assert saved.shape == tuple(CELL_SHAPE)
    flat = [float(v) for v in saved.reshape(-1, order="C")]
    assert array.values == flat


@pytest.mark.parametrize("config_id", GATES)
def test_array_is_real_not_zero_filled(adapter, config_id):
    array = adapter.load_allocation_array(f"gate.{config_id}.allocation", "allocation_at")
    assert any(value != 0.0 for value in array.values)


@pytest.mark.parametrize("config_id", GATES)
def test_normalization_equals_frozen_budget(adapter, config_id):
    """sum(Pi_at) == E_at to the frozen <1e-10 threshold; no extra dx/dy/dt."""
    array = adapter.load_allocation_array(f"gate.{config_id}.allocation", "allocation_at")
    total = sum(array.values)
    assert abs(total - G.FROZEN_SUMMARY[config_id]["E_at"]) < G.INTEGRAL_ABS_THRESHOLD


@pytest.mark.parametrize("config_id", GATES)
def test_recorded_hash_matches_source(adapter, config_id):
    path = _pi_at_path(adapter._root, config_id)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == G.PI_AT_SHA256[config_id]


def test_supporting_registry_hashes_match_source(adapter):
    """Guard the transcribed constants against drift."""
    root = adapter._root
    pairs = [
        (G.matched_qat_relative_origin(), G.MATCHED_QAT_SHA256),
        (G.analysis_csv_relative_origin(), G.ANALYSIS_CSV_SHA256),
        (G.readme_relative_origin(), G.README_SHA256),
    ]
    for rel, expected in pairs:
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == expected
    for config_id in GATES:
        entropy = root / G.entropy_relative_origin(config_id)
        assert hashlib.sha256(entropy.read_bytes()).hexdigest() == G.ENTROPY_SHA256[config_id]


# ========================================================== metadata correct
@pytest.mark.parametrize("config_id", GATES)
def test_cell_field_semantics(adapter, config_id):
    metadata = adapter.load_allocation_metadata(f"gate.{config_id}.allocation")
    field = metadata.root.fields[0]
    assert field.domain.location_type == "CARTESIAN_CELL"
    assert field.domain.coordinate_system == "CARTESIAN"
    assert field.domain.shape == CELL_SHAPE
    assert [axis.name for axis in field.domain.axes] == ["y", "x"]
    assert metadata.root.result.semantic_id == G.SEMANTIC_ID


@pytest.mark.parametrize("config_id", GATES)
def test_time_semantics_static_trajectory_integrated(adapter, config_id):
    metadata = adapter.load_allocation_metadata(f"gate.{config_id}.allocation")
    time = metadata.root.result.time
    assert time.sampling == "STATIC"
    assert time.accumulation == "TRAJECTORY_INTEGRATED"
    assert time.interval.root.value.start == 0.0
    assert time.interval.root.value.end == G.FINAL_TIME


@pytest.mark.parametrize("config_id", GATES)
def test_measure_includes_spatial_and_time_weights(adapter, config_id):
    summary = adapter.load_summary_metrics(f"gate.{config_id}.allocation")
    assert summary.measure.includes_time_weights is True
    assert summary.measure.includes_spatial_measure is True
    assert summary.measure.integral_rule == "sum(values)=E_at"


@pytest.mark.parametrize("config_id", GATES)
def test_origin_is_frozen_production(adapter, config_id):
    metadata = adapter.load_allocation_metadata(f"gate.{config_id}.allocation")
    assert metadata.root.result.data_origin == "FROZEN_PRODUCTION"
    assert metadata.root.result.verification.status == "FROZEN_VERIFIED"


@pytest.mark.parametrize("config_id", GATES)
def test_shock_window_mask_is_cell_window(adapter, config_id):
    metadata = adapter.load_allocation_metadata(f"gate.{config_id}.allocation")
    assert metadata.root.fields[0].mask_refs == [G.MASK_ID]
    mask = adapter.load_mask(G.MASK_ID)
    assert mask.type == "GATE_CELL_SHOCK_WINDOW"
    assert mask.id == "mask.gate.cell-window"


@pytest.mark.parametrize("config_id", GATES)
def test_summary_fractions_from_frozen_analysis(adapter, config_id):
    summary = adapter.load_summary_metrics(f"gate.{config_id}.allocation")
    frozen = G.FROZEN_SUMMARY[config_id]
    assert summary.inside.root.value.value.root.value == pytest.approx(frozen["inside_fraction"])
    assert summary.outside.root.value.value.root.value == pytest.approx(frozen["outside_fraction"])
    total = summary.total_budget.root.value.value.root.value
    assert total == pytest.approx(frozen["E_at"])
    inside = summary.inside.root.value.value.root.value
    outside = summary.outside.root.value.value.root.value
    assert inside + outside == pytest.approx(1.0)


def test_description_is_cell_only(adapter):
    description = adapter.describe_allocation("gate", "Acoustic")
    assert description.representation_type == "CELL_FIELD"
    assert description.measure_definition == "cell integrated"
    assert "cell" in description.coordinate_convention.lower()


@pytest.mark.parametrize("config_id", GATES)
def test_metadata_carries_no_values(adapter, config_id):
    metadata = adapter.load_allocation_metadata(f"gate.{config_id}.allocation")
    assert '"values":' not in metadata.model_dump_json()


# ==================================================== cell, never face fields
@pytest.mark.parametrize("config_id", GATES)
def test_never_converted_to_faces(adapter, config_id):
    metadata = adapter.load_allocation_metadata(f"gate.{config_id}.allocation")
    locations = {field.domain.location_type for field in metadata.root.fields}
    assert locations == {"CARTESIAN_CELL"}
    assert not any("FACE" in loc for loc in locations)
    # only one 32x128 field; no x-face [32,129] / y-face [32,128] pair
    assert len(metadata.root.fields) == 1


# ==================================================== missing asset handling
def test_missing_root_raises_typed_error(tmp_path):
    adapter = GateAllocationAdapter(tmp_path)
    with pytest.raises(DomainError) as excinfo:
        adapter.load_allocation_metadata("gate.Acoustic.allocation")
    error = excinfo.value
    assert error.body.code == "MISSING_SCIENTIFIC_ASSET"
    assert error.availability == "MISSING"
    assert error.status == 404


def test_unknown_gate_is_missing_not_empty_success(adapter):
    with pytest.raises(DomainError) as excinfo:
        adapter.load_allocation_metadata("gate.Missing.allocation")
    assert excinfo.value.availability == "MISSING"
    assert excinfo.value.body.code == "UNKNOWN_CONFIG"


def test_unsupported_experiment_is_unsupported(adapter):
    with pytest.raises(DomainError) as excinfo:
        adapter.load_allocation_metadata("case8.D_u.allocation")
    assert excinfo.value.availability == "UNSUPPORTED"
    assert excinfo.value.body.code == "UNSUPPORTED_COMBINATION"


def test_unknown_array_id_is_rejected(adapter):
    with pytest.raises(DomainError) as excinfo:
        adapter.load_allocation_array("gate.Acoustic.allocation", "faces")
    assert excinfo.value.body.code == "INVALID_RESULT_ID"


def test_unknown_mask_id_is_rejected(adapter):
    with pytest.raises(DomainError) as excinfo:
        adapter.load_mask("mask.case8.native-face-shock-window")
    assert excinfo.value.body.code == "UNKNOWN_ASSET_ID"


def test_drifted_array_is_not_silently_accepted(tmp_path):
    """A mutated Pi_at must not yield a numeric success."""
    root = Path(G.SCIENTIFIC_ROOT_WINDOWS)
    if not root.exists():
        pytest.skip("scientific root not present on this host")
    freeze = tmp_path / G.GATE_FREEZE_REL / "results_snapshot" / "Acoustic"
    freeze.mkdir(parents=True)
    # Copy the real entropy row, then write a drifted allocation of wrong sum.
    source_entropy = root / G.entropy_relative_origin("Acoustic")
    (freeze / "entropy.csv").write_bytes(source_entropy.read_bytes())
    np.save(freeze / "Pi_at.npy", np.zeros(G.CELL_SHAPE, dtype=np.float64))
    adapter = GateAllocationAdapter(tmp_path)
    with pytest.raises(DomainError) as excinfo:
        adapter.load_allocation_metadata("gate.Acoustic.allocation")
    assert excinfo.value.body.code == "SOURCE_DATA_DRIFT"


# ==================================================== protocol / integration
def test_adapter_satisfies_allocation_protocol(adapter):
    assert isinstance(adapter, AllocationAdapterProtocol)
    assert hasattr(adapter, "list_gates")


def test_scientific_source_unchanged(adapter):
    path = _pi_at_path(adapter._root, "Acoustic")
    before = path.stat()
    digest_before = hashlib.sha256(path.read_bytes()).hexdigest()
    adapter.load_allocation_array("gate.Acoustic.allocation", "allocation_at")
    after = path.stat()
    assert after.st_size == before.st_size
    assert after.st_mtime_ns == before.st_mtime_ns
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest_before


def test_case8_adapter_is_not_gate_adapter():
    from backend.adapters import Case8Adapter
    case8 = Case8Adapter()
    assert not hasattr(case8, "list_gates")
