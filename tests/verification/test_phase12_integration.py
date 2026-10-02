"""Final integration seams over accepted metadata; no CFD execution."""
import pytest
from pydantic import ValidationError
from backend.models import Experiment, ExperimentConfig, ConfigList, CapabilityList, Verification, unresolved
from backend.models.core import VERIFICATION_CANONICAL


@pytest.mark.parametrize("identity,count", [("gate", 3), ("spectrum", 4), ("modal-validation", 24)])
def test_delivered_workspaces_share_registry_and_real_evidence(app, identity, count):
    client = app.test_client()
    body = client.get(f"/api/v1/experiments/{identity}")
    assert body.status_code == 200
    experiment = Experiment.model_validate(body.json["data"])
    assert experiment.delivery_status == "IMPLEMENTED"
    configs = ConfigList.model_validate(client.get(f"/api/v1/experiments/{identity}/configs").json["data"])
    capabilities = CapabilityList.model_validate(client.get(f"/api/v1/experiments/{identity}/capabilities").json["data"])
    assert len(configs.items) == count
    assert configs.items == experiment.available_configs
    assert capabilities.items == experiment.capabilities
    assert all(c.tab_policy.visible_for_family for c in capabilities.items)
    assert not {"flow", "entropy"} & {c.tab_policy.tab_id for c in capabilities.items}
    registry = app.extensions["evidence_service"].registry
    for ref in experiment.evidence_refs:
        assert ref in registry.entries
        record = registry.record(ref)
        assert record["experiment_id"]["value"] == identity
        assert ExperimentConfig.model_validate(record["config"]["value"]) in configs.items


@pytest.mark.parametrize("source,canonical", VERIFICATION_CANONICAL.items())
def test_canonical_verification_preserves_basis_and_roundtrip(source, canonical):
    raw = {"status": source, "basis": ["Existing source verification; no promotion"],
           "verified_at": unresolved("No event timestamp"), "observation_at": unresolved("No event timestamp"), "evidence_refs": []}
    model = Verification.model_validate(raw)
    assert model.canonical_status == canonical
    assert model.status == source and model.basis == raw["basis"]
    assert Verification.model_validate_json(model.model_dump_json()) == model
    with pytest.raises(ValidationError):
        Verification.model_validate({**raw, "canonical_status": "MISSING" if canonical != "MISSING" else "VERIFIED"})


def test_canonical_mapping_preserves_strict_json_datetime_semantics():
    model = Verification.model_validate_json('{"status":"FROZEN_VERIFIED","basis":["Recorded source audit"],"verified_at":{"state":"UNKNOWN","reason":"No event timestamp"},"observation_at":{"state":"KNOWN","value":"2026-10-02T09:00:00Z"},"evidence_refs":[]}')
    assert model.observation_at.root.value.tzinfo is not None
    assert Verification.model_validate_json(model.model_dump_json()) == model
