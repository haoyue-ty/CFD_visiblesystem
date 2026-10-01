"""Required Phase 8 Window 0 checks against saved scientific source bytes.

No fake science, adapter/API/UI tests, solver imports or CFD execution.
"""
import ast
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from backend.models.core import ResourceSlot, ScientificLimitation
from backend.models.evidence import EvidenceRecord
from scripts.phase8 import audit_cylinder_sources as audit


@pytest.fixture(scope="module")
def source_map():
    return json.loads(audit.OUTPUT.read_text(encoding="utf-8"))


@pytest.mark.parametrize("config", ["A_u", "B_u", "D_u"])
def test_only_three_canonical_configurations(source_map, config):
    lock = audit.read_json(audit.CANONICAL / "J2C_V2_PROTOCOL_LOCK.json")
    assert source_map["config_ids"] == ["A_u", "B_u", "D_u"] == list(lock["configurations"])
    assert audit.require_config(config) == config
    assert source_map["runs"][config]["parameters"] == lock["configurations"][config]


def test_cylinder_c_is_rejected_with_frozen_422_semantics(source_map):
    with pytest.raises(ValueError, match="422 UNSUPPORTED_COMBINATION"):
        audit.require_config("C_u")
    assert source_map["rejected_configs"]["C_u"] == {
        "availability": "UNSUPPORTED", "http_status": 422, "code": "UNSUPPORTED_COMBINATION"}
    assert not (audit.CANONICAL / "runs/cylinder_C_u").exists()


@pytest.mark.parametrize("config", ["A_u", "B_u", "D_u"])
@pytest.mark.parametrize("index,step", [(1, 0), (2, 2439), (3, 4878), (4, 7318), (5, 9757)])
def test_five_snapshot_identities_real_time_fields_and_geometry(source_map, config, index, step):
    item = source_map["runs"][config]["snapshot_source"][index-1]
    assert item["snapshot_index"] == index and item["step_index"] == step
    assert item["source_step_index"] == step and item["accumulation"] == "NONE"
    with np.load(audit.SOURCE_ROOT / item["source"], allow_pickle=False) as z:
        assert item["physical_time"] == z["time"].item()
        assert step == z["step"].item()
        if index in (2, 3, 4):
            assert item["physical_time"] != (index-1) * 0.5
        assert set(item["members"]) == set(z.files)
        assert len(item["field_members"]) == 12
        assert not {"density", "pressure", "primitive_state"} & set(z.files)
        for family, shape in (("radial_interior", (31, 128)), ("angular_interior", (32, 128))):
            assert z[f"{family}_pi_at"].shape == shape
            assert z[f"{family}_face_measure"].shape == shape
            for key in ("x_face", "y_face", "r_face", "theta_face", "unit_normal_x", "unit_normal_y"):
                assert z[f"{family}_{key}"].shape == shape
            assert np.all(z[f"{family}_face_measure"] > 0)


@pytest.mark.parametrize("config", ["A_u", "B_u", "D_u"])
def test_all_9757_history_rows_numbering_increment_cumulative_and_units(source_map, config):
    history = source_map["runs"][config]["history_source"]
    rows = audit.csv_rows(audit.SOURCE_ROOT / history["source"])
    assert len(rows) == history["record_count"] == 9757
    assert [int(row["step"]) for row in rows] == list(range(9757))
    assert history["completed_step_range"] == [1, 9757]
    assert float(rows[0]["time_start"]) == 0 and float(rows[-1]["time_end"]) == 2
    assert history["scope"] == "INTERIOR_ONLY"
    series = {s["series_id"]: s for s in history["series"]}
    assert len(series) == 35
    assert series["E_at_cumulative"]["source_column"] == "E_at_int"
    assert series["E_at_cumulative"]["accumulation"] == "CUMULATIVE"
    assert series["delta_E_at"]["accumulation"] == "PER_STEP_INCREMENT"
    assert series["dotE_at_int_s2"]["accumulation"] == "NONE"
    assert series["E_at_cumulative"]["unit"]["label"] == "model integrated entropy"
    assert series["dotE_at_int_s2"]["unit"]["label"] == "model integrated entropy rate"
    for channel in ("bg", "aa", "at", "total"):
        cumulative = 0.0
        for row in rows:
            increment = float(row[f"deltaE_{channel}_int"])
            expected = float(row["dt"]) * sum(w * float(row[f"dotE_{channel}_int_s{s}"]) for s, w in enumerate((1/6, 1/6, 2/3)))
            assert increment == pytest.approx(expected, rel=2e-15, abs=1e-17)
            cumulative += increment
            assert cumulative == float(row[f"E_{channel}_int"])
        assert cumulative == pytest.approx(source_map["runs"][config]["allocation_source"]["channel_totals"][channel], rel=1e-13)


@pytest.mark.parametrize("config", ["A_u", "B_u", "D_u"])
def test_sector_arrays_edges_additivity_and_fraction_zero_denominators(source_map, config):
    allocation = source_map["runs"][config]["allocation_source"]
    assert allocation["representations"] == ["ANGULAR_SECTORS", "REGION_SCALAR"]
    with np.load(audit.SOURCE_ROOT / allocation["source"], allow_pickle=False) as z:
        assert allocation["sector_count"] == 16 and allocation["bin_edges_count"] == 17
        np.testing.assert_array_equal(z["bins"], allocation["bin_edges"])
        for channel in ("bg", "aa", "at", "total"):
            values = z[f"channel_{channel}"]
            assert values.shape == (16,)
            assert values.sum() == allocation["channel_totals"][channel]
            semantics = allocation["sector_fractions"][channel]
            if values.sum():
                assert semantics["availability"] == "AVAILABLE"
                assert semantics["sum"] == pytest.approx(1)
            else:
                assert semantics["availability"] == "UNSUPPORTED" and semantics["sum"] is None
        np.testing.assert_allclose(z["channel_total"], z["channel_bg"] + z["channel_aa"] + z["channel_at"], atol=1e-13)
        np.testing.assert_array_equal(z["activity_Pi_at"], z["channel_at"])
        assert all(z[k].ndim <= 1 for k in z.files)


@pytest.mark.parametrize("config", ["A_u", "B_u", "D_u"])
def test_front_band_fixed_authoritative_mask_and_cumulative_semantics(source_map, config):
    allocation = source_map["runs"][config]["allocation_source"]
    band = allocation["front_band"]
    assert band["accumulation"] == "TRAJECTORY_INTEGRATED" and band["scope"] == "INTERIOR_ONLY"
    mask = band["mask"]
    assert mask["policy"] == "FIXED_A_U_AUTHORITATIVE_RADIAL_ANCHORS" and mask["radial_half_width"] == .16
    assert "only between" in mask["angular_scope"] and "NaN outside" in mask["angular_scope"]
    assert mask["source"].endswith("07_cylinder_A_u/checkpoint_final.npz")
    assert audit.digest(audit.SOURCE_ROOT / mask["source"]) == mask["source_sha256"]
    with np.load(audit.SOURCE_ROOT / mask["source"], allow_pickle=False) as anchors:
        np.testing.assert_array_equal(anchors["front_angles"], mask["front_angles"])
        np.testing.assert_array_equal(anchors["front_radii"], mask["front_radii"])
    with np.load(audit.SOURCE_ROOT / allocation["source"], allow_pickle=False) as z:
        assert band["scalar"] == z["shock_at"].item()
        if config == "D_u":
            assert band["fraction"] == pytest.approx(0.00777687219301986, rel=1e-13)
        else:
            assert band["scalar"] == 0 and band["fraction"] is None and band["fraction_availability"] == "UNSUPPORTED"


def test_missing_2d_evidence_limitation_and_typed_slot_without_value(source_map):
    missing = source_map["missing_assets"]["cumulative_2d"]
    evidence = EvidenceRecord.model_validate(missing["Evidence"])
    limitation = ScientificLimitation.model_validate(missing["ScientificLimitation"])
    slot = ResourceSlot[dict].model_validate(missing["ResourceSlot"])
    assert evidence.evidence_id == slot.root.error.evidence_refs[0]
    assert evidence.result_ids == [] and evidence.source_assets[0].role == "MISSING_REFERENCE"
    assert slot.root.availability == "MISSING" and "value" not in slot.model_dump()
    assert limitation.code == "NO_FULL_CUMULATIVE_2D"
    with pytest.raises(ValidationError):
        ResourceSlot[dict].model_validate({**missing["ResourceSlot"], "value": {"invented": True}})
    for config in source_map["config_ids"]:
        assert source_map["runs"][config]["allocation_source"]["cumulative_2d"] == "MISSING"


def test_existing_off_contract_rerun_is_disclosed_and_not_registered(source_map):
    candidate = source_map["source_discrepancies"][0]
    assert candidate["id"] == "OFF_CONTRACT_CUMULATIVE_2D_EXISTS"
    assert candidate["availability_in_source_root"] == "AVAILABLE"
    assert candidate["availability_in_frozen_phase8_contract"] == "MISSING"
    assert candidate["selected_for_phase8"] is False
    manifest = audit.read_json(audit.EXCLUDED / "FREEZE_MANIFEST.json")
    assert candidate["manifest_sha256"] == audit.digest(audit.EXCLUDED / "FREEZE_MANIFEST.json")
    assert candidate["manifest_files_verified"] == len(manifest["files"]) == 77
    for item in manifest["files"]:
        assert audit.digest(audit.EXCLUDED / item["relative_path"]) == item["sha256"]
    assert candidate["native_face_field_integral"] == pytest.approx(0.09142394966318078, rel=1e-12)


def test_cross_flow_frozen_descriptive_policy(source_map):
    comparison = source_map["cross_flow"]
    assert comparison["schema"] == "CrossFlowComparison"
    assert (comparison["left"], comparison["right"]) == ("case8", "cylinder")
    assert comparison["ranking_policy"] == "NO_UNIFIED_RANKING"
    assert comparison["default_comparability"] == "DESCRIPTIVE_ONLY"
    assert all(r["status"] == "DESCRIPTIVE_ONLY" and r["mapping_ref"]["state"] == "NOT_APPLICABLE" for r in comparison["rules"])
    assert {r["left_definition_id"] for r in comparison["rules"]} == {
        "case8.native_face_localization", "case8.high_k_energy", "case8.cartesian_width", "case8.entropy_budget"}


def test_frozen_documents_and_shared_git_base(source_map):
    for item in source_map["frozen_prerequisites"]["phase4_documents"]:
        assert audit.digest(audit.WORKTREE / item["path"]) == item["sha256"]
    for phase in ("phase5", "phase6", "phase7"):
        assert source_map["frozen_prerequisites"][phase] == "FROZEN_ACCEPTED"
    for item in source_map["frozen_prerequisites"]["prerequisite_freeze_hashes"]:
        # Final integration restores the accepted CRLF bytes; the historical
        # bootstrap map retains its LF checkout observation without rewriting it.
        assert audit.digest(audit.WORKTREE / item["path"]) == item["frozen_windows_sha256"]
    base = source_map["phase8_base_commit"]
    assert subprocess.check_output(["git", "rev-parse", "phase7/spectral-integration"], cwd=audit.WORKTREE, text=True).strip() == base
    assert subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=audit.WORKTREE, check=False).returncode == 0


def test_all_audited_source_hashes_and_preservation(source_map):
    preservation = source_map["source_preservation"]
    assert preservation["status"] == "PASS"
    assert preservation["before_inventory"] == preservation["after_inventory"]
    assert preservation["file_count"] == len(source_map["source_files"]) == 189
    assert audit.inventory([audit.SOURCE_ROOT / f["path"] for f in source_map["source_files"]]) == preservation["after_inventory"]
    assert not [f for f in source_map["source_files"] if f["verification_state"] == "RECORDED_HASH_DRIFT"]
    assert source_map["scientific_files_modified"] is False and source_map["cfd_runs_started"] == 0


def test_reproduce_audit_with_scientific_write_guard(source_map, monkeypatch):
    original_open = io.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if isinstance(file, (str, Path)) and Path(file).resolve().is_relative_to(audit.SOURCE_ROOT.resolve()):
            assert not any(flag in mode for flag in ("w", "a", "x", "+")), "Scientific write attempted"
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(io, "open", guarded_open)
    rebuilt = audit.audit()
    # Worktree identity and checkout observations change at integration. Every
    # scientific observation, source hash, missing slot and policy stays exact.
    observation_keys = {"worktree", "frozen_prerequisites"}
    assert {k: v for k, v in rebuilt.items() if k not in observation_keys} == {
        k: v for k, v in source_map.items() if k not in observation_keys}
    assert rebuilt["frozen_prerequisites"]["phase7_accepted_files_verified"] == 161
    assert all(item["checkout_sha256"] == item["frozen_windows_sha256"]
               for item in rebuilt["frozen_prerequisites"]["prerequisite_freeze_hashes"])
    tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(name and (name.startswith("solver") or name.startswith("diagnostics")) for name in imports)
    assert audit.OUTPUT.is_relative_to(audit.WORKTREE) and not audit.OUTPUT.is_relative_to(audit.SOURCE_ROOT)
