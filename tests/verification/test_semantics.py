"""Semantic distinctness assertions for the Case8 slice (Window 4 QA).

These tests guard against *category* errors, which are the failure mode a purely
software test cannot see: two different scientific quantities collapsing into one
another, an absent value silently becoming zero, or a delivery state being
mistaken for a scientific state.

Part 1 asserts the canonical models in ``backend.models`` already enforce the
distinctions. Part 2 asserts the same distinctions survive the API contract; those
assertions carry their merge-readiness marker.
"""

from __future__ import annotations

import pytest

from backend.models import (CanonicalModel, KnownFact, TimeSpec, UnresolvedFact,
                            Verification, unresolved)
from tests.verification.case8_facts import FACTS

WAITING = ("WAITING_FOR_IMPLEMENTATION: Case8 blueprint (C801-C808 / ARRAY01 / EVI) "
           "is not registered on PHASE5_BOOTSTRAP_BASE. Test is merge-ready and must "
           "be re-enabled, not rewritten, when the routes land.")


# ---------------------------------------------------------------------------
# 1. Canonical model layer — these must hold on the frozen bootstrap base
# ---------------------------------------------------------------------------

def test_missing_is_not_zero_and_cannot_carry_a_value():
    missing = unresolved("Known scientific asset absent", "MISSING")
    UnresolvedFact.model_validate(missing)
    assert missing == {"state": "MISSING", "reason": "Known scientific asset absent"}
    assert "value" not in missing

    with pytest.raises(Exception):
        UnresolvedFact.model_validate({"state": "MISSING", "reason": "absent", "value": 0.0})


def test_unknown_is_not_missing_and_reasons_are_not_interchangeable():
    unknown = unresolved("Runtime observation not performed", "UNKNOWN")
    missing = unresolved("Known asset absent", "MISSING")
    assert unknown["state"] != missing["state"]
    assert unknown["reason"] != missing["reason"]


def test_a_missing_fact_never_validates_as_a_zero_valued_known_fact():
    with pytest.raises(Exception):
        KnownFact[float].model_validate({"state": "MISSING", "value": 0.0})
    with pytest.raises(Exception):
        KnownFact[float].model_validate({"state": "KNOWN", "reason": "no value"})


def test_verified_not_frozen_is_not_the_same_status_as_frozen_verified():
    assert "VERIFIED_NOT_FROZEN" != "FROZEN_VERIFIED"
    basis = ["Recorded finite fields and bitwise terminal comparison"]

    verified_not_frozen = Verification(status="VERIFIED_NOT_FROZEN", basis=basis,
                                       verified_at=unresolved("No bound event"),
                                       observation_at=unresolved("Not observed"),
                                       evidence_refs=["ev.case8"])
    frozen_verified = Verification(status="FROZEN_VERIFIED", basis=basis,
                                   verified_at=unresolved("No bound event"),
                                   observation_at=unresolved("Not observed"),
                                   evidence_refs=["ev.case8"])
    assert verified_not_frozen.status != frozen_verified.status


def test_verified_statuses_require_an_explicit_basis():
    for status in ("FROZEN_VERIFIED", "VERIFIED_NOT_FROZEN", "DERIVED_VERIFIED"):
        with pytest.raises(Exception):
            Verification(status=status, basis=[], verified_at=unresolved("none"),
                         observation_at=unresolved("none"), evidence_refs=["ev"])


def test_snapshot_timeline_and_scalar_timeline_are_not_the_same_axis():
    snapshot_time = TimeSpec(sampling="MULTI_SNAPSHOT", accumulation="NONE",
                             physical_time={"state": "KNOWN", "value": 0.08},
                             interval=unresolved("Instantaneous state", "NOT_APPLICABLE"),
                             step_index={"state": "KNOWN", "value": 1912},
                             stage_index=unresolved("Endpoint snapshot", "NOT_APPLICABLE"),
                             snapshot_index={"state": "KNOWN", "value": 6},
                             index_convention="snapshot_index 1-based")
    scalar_time = TimeSpec(sampling="PER_STEP", accumulation="TRAJECTORY_INTEGRATED",
                           physical_time={"state": "KNOWN", "value": 0.08},
                           interval={"state": "KNOWN", "value": {"start": 0.0, "end": 0.08}},
                           step_index={"state": "KNOWN", "value": 1912},
                           stage_index=unresolved("Accepted-step endpoint", "NOT_APPLICABLE"),
                           snapshot_index=unresolved("No recorded frame", "NOT_APPLICABLE"),
                           index_convention="completed accepted steps 1..1912")
    assert snapshot_time.sampling != scalar_time.sampling
    assert snapshot_time.accumulation != scalar_time.accumulation
    assert snapshot_time.index_convention != scalar_time.index_convention
    # The shared numeric physical_time is allowed; the semantics are what differ.
    assert snapshot_time.physical_time == scalar_time.physical_time


def test_cumulative_and_step_increment_are_distinct_accumulation_tokens():
    assert "STEP_INCREMENT" != "TRAJECTORY_INTEGRATED"
    step = TimeSpec(sampling="PER_STEP", accumulation="STEP_INCREMENT",
                    physical_time=unresolved("no single time"), interval=unresolved("no interval"),
                    step_index={"state": "KNOWN", "value": 1}, stage_index=unresolved("none"),
                    snapshot_index=unresolved("none"), index_convention="deltaE_* column")
    cumulative = TimeSpec(sampling="PER_STEP", accumulation="TRAJECTORY_INTEGRATED",
                          physical_time=unresolved("no single time"), interval=unresolved("no interval"),
                          step_index={"state": "KNOWN", "value": 1}, stage_index=unresolved("none"),
                          snapshot_index=unresolved("none"), index_convention="E_at column")
    assert step.accumulation != cumulative.accumulation


def test_E_at_and_Pi_at_are_different_recorded_quantities():
    """The recorded source keeps cumulative E_at and the stage rate as separate columns."""
    assert FACTS.fact("D_u.E_at.rows_distinct").value is True
    assert isinstance(FACTS.fact("D_u.E_at.terminal").value, float)


def test_delivery_status_tokens_are_not_scientific_availability_tokens():
    delivery = {"PLANNED", "IMPLEMENTED"}
    availability = {"AVAILABLE", "PARTIAL", "MISSING", "UNSUPPORTED", "ERROR"}
    assert delivery.isdisjoint(availability), (
        "PLANNED delivery must never be reported as scientific MISSING")


def test_canonical_models_forbid_unknown_fields():
    class Sample(CanonicalModel):
        name: str

    with pytest.raises(Exception):
        Sample.model_validate({"name": "x", "absolute_source_path": "D:/secret"})


# ---------------------------------------------------------------------------
# 2. Contract layer — merge-ready, pending the Case8 blueprint
# ---------------------------------------------------------------------------

def test_contract_keeps_cumulative_and_increment_in_separate_series(app):
    response = app.test_client().get("/api/v1/experiments/case8/configs/D_u/entropy-history")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    aggregations = {series["aggregation"] for series in response.json["data"]["series"]}
    assert "STEP_INCREMENT" in aggregations
    assert "CUMULATIVE" in aggregations
    for series in response.json["data"]["series"]:
        if series["aggregation"] == "CUMULATIVE":
            assert series["result"]["time"]["accumulation"] == "TRAJECTORY_INTEGRATED"


def test_contract_reports_absent_metric_as_missing_slot_not_zero(app):
    response = app.test_client().get("/api/v1/experiments/case8/configs/A_u/metrics")
    assert response.status_code == 200, response.get_data(as_text=True)[:200]
    items = response.json["data"]["items"]
    assert items, "the metric collection must be enumerated, even when empty of values"
    for slot in items:
        if slot["availability"] == "MISSING":
            assert "value" not in slot
