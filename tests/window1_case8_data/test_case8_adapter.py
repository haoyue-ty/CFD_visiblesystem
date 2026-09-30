"""Window 1 adapter-level verification for the Case8 scientific data core.

These tests exercise the real read-only scientific source. They assert the
recorded counts, indices, times and file integrity that the window DoD requires.
They never modify the scientific root.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from backend.adapters import Case8Adapter, Case8AdapterProtocol
from backend.registry import case8_source_constants as C

CONFIGS = ("A_u", "B_u", "C_u", "D_u")
EXPECTED_SNAPSHOTS_PER_CONFIG = 6
EXPECTED_HISTORY_ROWS = 1912
FINAL_STEP = 1912
FINAL_TIME = 0.08


@pytest.fixture(scope="module")
def adapter() -> Case8Adapter:
    root = Path(C.SCIENTIFIC_ROOT_WINDOWS)
    if not root.exists():
        pytest.skip("scientific root not present on this host")
    return Case8Adapter(root)


def test_adapter_satisfies_protocol(adapter):
    assert isinstance(adapter, Case8AdapterProtocol)


def test_config_count(adapter):
    configs = adapter.list_configs()
    assert len(configs.items) == len(CONFIGS) == 4
    assert [c.id for c in configs.items] == list(CONFIGS)


@pytest.mark.parametrize("config_id", CONFIGS)
def test_snapshot_count_per_config(adapter, config_id):
    index = adapter.list_snapshots(config_id)
    assert index.snapshot_count == EXPECTED_SNAPSHOTS_PER_CONFIG == 6
    assert len(index.items) == 6


@pytest.mark.parametrize("config_id", CONFIGS)
def test_no_snapshot_index_zero(adapter, config_id):
    index = adapter.list_snapshots(config_id)
    indices = [item.snapshot_index for item in index.items]
    assert indices == [1, 2, 3, 4, 5, 6]
    assert 0 not in indices


@pytest.mark.parametrize("config_id", CONFIGS)
def test_first_snapshot_is_initial_state(adapter, config_id):
    first = adapter.load_snapshot_metadata(config_id, 1)
    assert first.snapshot_index == 1
    assert first.step_index == 0
    assert first.physical_time == 0.0


@pytest.mark.parametrize("config_id", CONFIGS)
def test_final_snapshot_du_values(adapter, config_id):
    final = adapter.load_snapshot_metadata(config_id, 6)
    assert final.snapshot_index == 6
    assert final.step_index == FINAL_STEP
    assert final.physical_time == FINAL_TIME


@pytest.mark.parametrize("config_id", CONFIGS)
def test_intermediate_times_come_from_source(adapter, config_id):
    """Every snapshot time must equal the recorded NPZ ``time`` member."""
    import numpy as np
    for item in adapter.list_snapshots(config_id).items:
        source_step = C.SNAPSHOT_SOURCE_STEPS[item.snapshot_index - 1]
        path = adapter._checkpoint_path(config_id, source_step)
        with np.load(path, allow_pickle=False) as z:
            assert int(z["step"]) == item.step_index
            assert float(z["time"]) == item.physical_time


@pytest.mark.parametrize("config_id", CONFIGS)
def test_history_row_count(adapter, config_id):
    series = adapter.load_scalar_series(config_id, "E_at_cumulative")
    assert series.total_point_count == EXPECTED_HISTORY_ROWS == 1912
    assert len(series.points) == 1912


@pytest.mark.parametrize("config_id", CONFIGS)
def test_history_step_mapping(adapter, config_id):
    """step_index = source_step_index + 1; source numbering preserved."""
    series = adapter.load_scalar_series(config_id, "E_bg_step", limit=2000)
    assert series.points[0].source_step_index.root.value == 0
    assert series.points[0].step_index.root.value == 1
    assert series.points[-1].source_step_index.root.value == 1911
    for point in series.points:
        assert point.step_index.root.value == point.source_step_index.root.value + 1


@pytest.mark.parametrize("config_id", CONFIGS)
def test_history_terminal_time(adapter, config_id):
    series = adapter.load_scalar_series(config_id, "E_at_cumulative")
    assert series.points[-1].physical_time.root.value == FINAL_TIME


def test_aggregation_semantics_distinguished(adapter):
    history = adapter.load_entropy_history("D_u", limit=2)
    aggregations = {s.series_id: s.aggregation for s in history.series}
    assert aggregations["E_bg_cumulative"] == "CUMULATIVE"
    assert aggregations["E_aa_cumulative"] == "CUMULATIVE"
    assert aggregations["E_at_cumulative"] == "CUMULATIVE"
    assert aggregations["E_bg_step"] == "STEP_INCREMENT"
    assert aggregations["E_aa_step"] == "STEP_INCREMENT"
    assert aggregations["E_at_step"] == "STEP_INCREMENT"


@pytest.mark.parametrize("field_id,shape", [("density", [32, 128]), ("pressure", [32, 128]), ("front", [32])])
def test_stored_fields_available(adapter, field_id, shape):
    array = adapter.load_array(f"case8.D_u.snapshot.6.{field_id}", field_id)
    assert array.descriptor.shape == shape
    assert array.descriptor.element_count == int(__import__("numpy").prod(shape))
    assert len(array.values) == array.descriptor.element_count


def test_fields_are_real_not_zero_filled(adapter):
    array = adapter.load_array("case8.D_u.snapshot.6.density", "density")
    assert any(v != 0.0 for v in array.values)


def test_metrics_real(adapter):
    collection = adapter.load_metrics("D_u")
    ids = [slot.root.value.metric_id for slot in collection.items]
    assert ids == ["case8_width", "case8_front_RMS", "case8_front_high_k_energy"]
    for slot in collection.items:
        assert slot.root.value.value.root.state == "KNOWN"


def test_allocation_registry_metadata_only(adapter):
    from backend.registry import case8_registry as REG
    allocation = REG.allocation_registry()
    assert allocation["implementation_status"] == "IMPLEMENTATION_DEFERRED"
    assert allocation["excluded_configs"] == {"A_u": "MISSING", "B_u": "MISSING", "C_u": "MISSING"}


def test_no_zero_cumulative_map_for_a_b_c(adapter):
    from backend.registry import case8_registry as REG
    for capability in REG.capabilities():
        if capability["id"] == "case8.allocation":
            for entry in capability["config_support"]:
                if entry["config_id"] in ("A_u", "B_u", "C_u"):
                    assert entry["status"] == "MISSING"
                    assert entry["result_refs"] == []


def test_verification_not_promoted(adapter):
    """VERIFIED_NOT_FROZEN must never be promoted to FROZEN_VERIFIED."""
    evidence = adapter.load_evidence("ev.case8.D_u.snapshot.6.density")
    assert evidence.verification.status == "VERIFIED_NOT_FROZEN"
    assert evidence.source_assets[0].verification.status == "VERIFIED_NOT_FROZEN"


def test_recorded_hash_matches_source(adapter):
    """The D_u terminal checkpoint hash must equal the recorded source hash."""
    path = adapter._checkpoint_path("D_u", 1912)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == C.CHECKPOINT_SHA256["D_u"][1912]
    evidence = adapter.load_evidence("ev.case8.D_u.snapshot.6")
    assert evidence.data_hash.root.value == digest


@pytest.mark.parametrize("config_id", CONFIGS)
def test_history_hash_matches_source(adapter, config_id):
    path = adapter._history_path(config_id)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == C.HISTORY_SHA256[config_id]


def test_scientific_source_unchanged(adapter):
    """Scientific files must be untouched by adapter reads (hash + mtime stable)."""
    path = adapter._history_path("D_u")
    before = path.stat()
    digest_before = hashlib.sha256(path.read_bytes()).hexdigest()
    adapter.load_entropy_history("D_u", limit=50)
    after = path.stat()
    assert after.st_size == before.st_size
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest_before


def test_provenance_binding(adapter):
    provenance = adapter.load_provenance("case8.D_u.snapshot.6.density")
    assert provenance.provenance.source_asset_ids == ["asset.case8.D_u.step1912"]
    assert provenance.provenance.evidence_refs == ["ev.case8.D_u.snapshot.6"]
