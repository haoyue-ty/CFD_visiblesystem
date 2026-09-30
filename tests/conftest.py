import pytest

from backend import create_app
from backend.models import unresolved, known


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def result_payload():
    unknown = unresolved("Test fixture has no scientific source")
    na = unresolved("Mock fixture", "NOT_APPLICABLE")
    return {
        "schema_version": "1.0.0", "result_id": "mock.case8.field", "experiment_id": "case8",
        "config_id": "D_u", "semantic_id": "density", "data_origin": "MOCK", "availability": "AVAILABLE",
        "time": {"sampling": "MULTI_SNAPSHOT", "accumulation": "NONE", "physical_time": known(0.0),
                 "interval": na, "step_index": known(0), "stage_index": na, "snapshot_index": known(1),
                 "index_convention": "USER_VISIBLE_1_BASED_RECORDED_INDEX"},
        "scope": {"id": "mock.scope", "description": "Fixture only", "boundary_scope": unknown,
                  "spatial_domain_ref": unknown, "mask_refs": [], "definition_refs": []},
        "unit": {"id": "mock.unit", "system": "MODEL", "quantity": "density", "label": "model density", "si_mapping": unknown},
        "verification": {"status": "NOT_APPLICABLE", "basis": ["Test fixture"], "verified_at": na,
                         "observation_at": na, "evidence_refs": ["mock.evidence"]},
        "provenance": {"evidence_refs": ["mock.evidence"], "source_asset_ids": [], "registry_revision": "mock.registry",
                       "data_revision": "mock.data", "release_id": na, "source_drift": na},
        "limitations": [],
    }
