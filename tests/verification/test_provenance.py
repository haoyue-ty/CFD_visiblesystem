"""Provenance and public-DTO hygiene assertions (Window 4 QA).

Two independent obligations are checked:

1. Every scientific result must be traceable: it carries a result/experiment/config
   identity, evidence references, source asset identities, a verification block and
   hash fields.
2. No public DTO may leak an absolute file path, a ``file://`` URL or a raw source
   locator. Public location information is limited to a controlled relative origin
   and a human-readable source display string.

Part 1 asserts the canonical models; part 2 asserts the wire contract, pending merge.
"""

from __future__ import annotations

import json
import re

import pytest

from backend.models import (ArrayDescriptor, ScientificResult, SourceAsset,
                            unresolved)

WAITING = ("WAITING_FOR_IMPLEMENTATION: Case8 blueprint (C801-C808 / ARRAY01 / EVI) "
           "is not registered on PHASE5_BOOTSTRAP_BASE. Test is merge-ready and must "
           "be re-enabled, not rewritten, when the routes land.")

WINDOWS_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")
UNC_PATH = re.compile(r"\\\\[^\\/\s]+[\\/]")
FILE_URL = re.compile(r"file://", re.IGNORECASE)
READONLY_ROOT = re.compile(r"^[A-Za-z]:[\\/]Paper[\\/]passage6", re.IGNORECASE)


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)


def find_locator_leaks(payload_text: str) -> list[str]:
    """Return every string in a public payload that exposes a raw source locator."""
    leaks: list[str] = []
    for candidate in _walk_strings(json.loads(payload_text)):
        if FILE_URL.search(candidate) or WINDOWS_ABSOLUTE.search(candidate) or UNC_PATH.search(candidate):
            leaks.append(candidate)
    return leaks


# ---------------------------------------------------------------------------
# 1. Canonical model layer
# ---------------------------------------------------------------------------

def _result_payload(**overrides):
    payload = {
        "schema_version": "1.0.0",
        "result_id": "case8.D_u.snapshot.6.density",
        "experiment_id": "case8",
        "config_id": "D_u",
        "semantic_id": "density",
        "data_origin": "VERIFIED_PRODUCTION",
        "availability": "AVAILABLE",
        "time": {"sampling": "MULTI_SNAPSHOT", "accumulation": "NONE",
                 "physical_time": {"state": "KNOWN", "value": 0.08},
                 "interval": unresolved("Instantaneous state", "NOT_APPLICABLE"),
                 "step_index": {"state": "KNOWN", "value": 1912},
                 "stage_index": unresolved("Endpoint snapshot", "NOT_APPLICABLE"),
                 "snapshot_index": {"state": "KNOWN", "value": 6},
                 "index_convention": "snapshot_index 1-based"},
        "scope": {"id": "case8.cells", "description": "endpoint density",
                  "boundary_scope": unresolved("Bind at adapter"),
                  "spatial_domain_ref": {"state": "KNOWN", "value": "case8.cells"},
                  "mask_refs": [], "definition_refs": ["density"]},
        "unit": {"id": "model_density", "system": "MODEL", "quantity": "density",
                 "label": "model density", "si_mapping": unresolved("No SI mapping")},
        "verification": {"status": "VERIFIED_NOT_FROZEN",
                         "basis": ["Recorded finite fields and bitwise terminal comparison"],
                         "verified_at": unresolved("No bound event"),
                         "observation_at": unresolved("Not observed"),
                         "evidence_refs": ["ev.case8.D_u.snapshot.6.density"]},
        "provenance": {"evidence_refs": ["ev.case8.D_u.snapshot.6.density"],
                       "source_asset_ids": ["asset_f4323c28384b"],
                       "registry_revision": "rev.phase5b", "data_revision": "data.phase1",
                       "release_id": unresolved("No release bundle", "NOT_APPLICABLE"),
                       "source_drift": unresolved("Not observed")},
        "limitations": [],
    }
    payload.update(overrides)
    return payload


def test_scientific_result_carries_full_provenance_identity():
    result = ScientificResult.model_validate(_result_payload())
    assert result.result_id and result.experiment_id and result.config_id
    assert result.provenance.evidence_refs
    assert result.provenance.source_asset_ids
    assert result.verification.evidence_refs
    assert result.provenance.registry_revision and result.provenance.data_revision


def test_scientific_result_requires_source_asset_identity():
    payload = _result_payload()
    payload["provenance"]["source_asset_ids"] = []
    with pytest.raises(Exception):
        ScientificResult.model_validate(payload)


def test_source_asset_hash_fields_are_separate_and_not_interchangeable():
    asset = SourceAsset.model_validate({
        "asset_id": "asset_f4323c28384b", "source_id": "scientific-root-v1",
        "source_display": "Case8 D_u corrected checkpoint step_001912.npz",
        "relative_origin": {"state": "KNOWN",
                            "value": "corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_001912.npz"},
        "role": "DATA", "format": "NPZ",
        "recorded_data_hash": {"state": "KNOWN", "value": "3ab44eb9febe7fbe5d8f76e00ef0b31afd4b01bceb2676ed609f4f9860d62093"},
        "current_data_hash": unresolved("Runtime observation not performed"),
        "data_drift": unresolved("Not observed"),
        "verification": {"status": "VERIFIED_NOT_FROZEN",
                         "basis": ["Finite fields and terminal comparison"],
                         "verified_at": unresolved("No event"),
                         "observation_at": unresolved("Not observed"),
                         "evidence_refs": ["ev.case8"]},
        "canonical_selected": True, "limitations": [],
    })
    assert "recorded_data_hash" in asset.model_fields_set
    assert find_locator_leaks(asset.model_dump_json()) == []


def test_array_descriptor_rejects_hidden_absolute_member_path():
    with pytest.raises(Exception):
        ArrayDescriptor.model_validate({
            "array_id": "density", "dtype": "float64", "shape": [32, 128], "order": "C",
            "axes": ["y", "x"], "encoding": "FLAT_JSON", "element_count": 4096,
            "absolute_source_path": "D:/secret.npz"})


@pytest.mark.xfail(
    strict=False,
    reason=("FOUND_FAILURE: no public-DTO locator scrubber exists on the bootstrap base. "
            "ScientificResult.scope.description is unrestricted free text, so an absolute "
            "source path can be serialized into a public payload. Reported, not repaired: "
            "QA does not modify production code."))
def test_scientific_result_does_not_serialize_absolute_path_in_public_fields():
    """The canonical serializer must not let an absolute locator out on the wire."""
    payload = _result_payload()
    payload["scope"]["description"] = r"read from D:\Paper\passage6\secret.npz"
    result = ScientificResult.model_validate(payload)
    assert find_locator_leaks(result.model_dump_json()) == []


# ---------------------------------------------------------------------------
# 2. Contract layer — merge-ready, pending the Case8 blueprint
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason=WAITING)
def test_contract_snapshot_payload_exposes_no_absolute_path(app):
    response = app.test_client().get("/api/v1/experiments/case8/configs/D_u/snapshots/6")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    assert find_locator_leaks(response.get_data(as_text=True)) == []


@pytest.mark.xfail(strict=True, reason=WAITING)
def test_contract_evidence_payload_carries_hashes_and_relative_origin(app):
    response = app.test_client().get("/api/v1/evidence/ev.case8.D_u.snapshot.6.density")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    body = response.json["data"]
    assert body["method_hash"]["value"]
    assert body["recorded_source_hash"]
    assert find_locator_leaks(response.get_data(as_text=True)) == []
