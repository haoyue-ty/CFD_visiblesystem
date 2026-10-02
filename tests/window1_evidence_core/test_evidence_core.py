"""Phase11 acceptance of frozen EVI01–04 and reproducibility semantics.

Negative observations mutate only temporary relocated files. Expected section
boundaries and representative IDs are asserted independently of catalog output.
"""
import json
import re
import shutil
from pathlib import Path

import pytest
from openapi_spec_validator import validate
from pydantic import ValidationError

from backend import create_app
from backend.adapters.evidence_sources import aggregate_drift
from backend.adapters.case8 import Case8Adapter
from backend.adapters.allocation_integration import IntegratedAllocationAdapter
from backend.adapters.cylinder import CylinderAdapter
from backend.adapters.entropy_closure import EntropyClosureAdapter
from backend.adapters.spectral_data import SpectralAdapter
from backend.models import EvidenceRecord, SourceAsset, known, unresolved
from backend.registry import case8_source_constants as C, spectral_registry as S
from backend.registry import closure_registry as L
from backend.registry.content_registry import load_foundation
from backend.schemas.openapi import export_openapi
from backend.schemas.requests import EvidenceQuery
from backend.services.evidence import EvidenceService
from backend.services.spectral_resources import PREFIX, SELECTORS

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path("D:/Paper/passage6")


@pytest.fixture(scope="module")
def app():
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def read(client, url):
    response = client.get(url)
    assert response.status_code == 200, response.json
    assert response.json["availability"] == "AVAILABLE"
    return response.json["data"]


def test_current_default_page_excludes_history_and_missing(client, app):
    data = read(client, "/api/v1/evidence")
    assert data["page"]["limit"] == 50 and data["page"]["returned_count"] == 50
    assert data["page"]["has_more"] and data["page"]["total_count"] > 50
    registry = app.extensions["evidence_service"].registry
    for item in data["items"]:
        assert registry.sections[item["evidence_id"]] == "CURRENT"
        assert item["verification"]["status"] not in ("MISSING", "LEGACY", "SUPERSEDED", "AVAILABLE_UNVERIFIED")
    assert not any(i.startswith("ev.inventory.") for i in registry.sections if registry.sections[i] == "CURRENT")


def test_server_filters_and_stable_offset_pages(client):
    query = "/api/v1/evidence?experiment_id=entropy-closure&limit=3"
    first = read(client, query)
    second = read(client, query + "&offset=3")
    assert first["page"]["total_count"] == second["page"]["total_count"] == 16
    assert not ({i["evidence_id"] for i in first["items"]} & {i["evidence_id"] for i in second["items"]})
    assert all(i["experiment_id"] == known("entropy-closure") for i in first["items"] + second["items"])
    last = read(client, query + "&offset=15")
    assert last["page"]["returned_count"] == 1 and last["page"]["has_more"] is False
    assert read(client, query + "&offset=100")["items"] == []
    assert read(client, "/api/v1/evidence?experiment_id=unknown")["page"]["total_count"] == 0
    frozen = read(client, "/api/v1/evidence?experiment_id=spectrum&status=FROZEN_VERIFIED&limit=2")
    assert all(i["verification"]["status"] == "FROZEN_VERIFIED" for i in frozen["items"])


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1", "offset=1.2", "limit=x",
    "section=unknown", "status=UNSUPPORTED", "limit=1&limit=2", "section=CURRENT&section=GAPS", "path=D:/Paper/passage6", "source_drift=false"])
def test_only_frozen_evidence_query_fields_are_accepted(client, query):
    response = client.get("/api/v1/evidence?" + query)
    assert response.status_code == 400 and response.json["error"]["code"] == "INVALID_REQUEST"
    assert EvidenceQuery().limit == 50


def test_gaps_are_explicit_missing_unsupported_and_never_numeric_zero(client):
    gaps = read(client, "/api/v1/evidence?section=GAPS&limit=200")
    ids = {item["evidence_id"] for item in gaps["items"]}
    assert {"ev.missing.cylinder-cumulative2d", "ev.inventory.missing_near1d_raw_epsilon_scan",
            "ev.inventory.missing_persisted_jacobian_fourier_blocks", "ev.gap.case8-cylinder-front-band",
            "ev.gap.closure-spatial-trajectory"} <= ids
    for identity in ids:
        record = read(client, "/api/v1/evidence/" + identity)
        assert record["result_ids"] == record["result_contexts"] == []
        assert record["data_hash"]["state"] in ("MISSING", "UNKNOWN", "NOT_APPLICABLE")
        assert "value" not in record["data_hash"]
    unsupported = read(client, "/api/v1/evidence/ev.gap.case8-cylinder-front-band")
    assert unsupported["verification"]["status"] == "NOT_APPLICABLE"
    assert "UNSUPPORTED" in {l["code"] for l in unsupported["limitations"]}


def test_history_is_separate_and_keeps_original_status(client, app):
    data = read(client, "/api/v1/evidence?section=HISTORY&status=SUPERSEDED&limit=2")
    assert data["page"]["total_count"] > 2
    for item in data["items"]:
        assert item["verification"]["status"] == "SUPERSEDED"
        record = read(client, "/api/v1/evidence/" + item["evidence_id"])
        assert record["result_ids"] == []
        assert all(a["canonical_selected"] is False for a in record["source_assets"])
    registry = app.extensions["evidence_service"].registry
    all_data = read(client, "/api/v1/evidence?section=ALL&limit=1")
    assert all_data["page"]["total_count"] == len(registry.entries)


@pytest.mark.parametrize("url,code", [("/api/v1/evidence/unknown", "UNKNOWN_EVIDENCE_ID"),
    ("/api/v1/results/not-registered/provenance", "INVALID_RESULT_ID"), ("/api/v1/assets/unknown", "UNKNOWN_ASSET_ID")])
def test_unknown_id_is_typed_404(client, url, code):
    response = client.get(url)
    assert response.status_code == 404 and response.json["error"]["code"] == code
    assert "data" not in response.json


REPRESENTATIVES = ["case8.D_u.allocation", "case8.D_u.E_at_cumulative", "gate.Acoustic.allocation", "gate.comparison.min",
    S.record_id("spectrum.q-0.396", 8),
    S.eigenmode_id("spectrum.q-0.396", 16, "LEFT", 31),
    S.eigenmode_id("spectrum.q-0.132", 7, "RIGHT", 3, "PRIMITIVE_PROFILE", "pressure"),
    next(iter(S.RUNS)) + ".history", "cylinder.D_u.sectors", "case8-cylinder.D_u.D_u",
    L.result_id("D_u-cfl-0.05", "run", "R_total"), "mechanism.acoustic-pathways.v1"]


@pytest.mark.parametrize("identity", REPRESENTATIVES)
def test_representative_result_provenance_has_every_direct_record(client, identity):
    provenance = read(client, "/api/v1/results/" + identity + "/provenance")
    records = provenance["evidence_records"]
    assert provenance["result_id"] == identity and records
    assert {r["evidence_id"] for r in records} == set(provenance["provenance"]["evidence_refs"])
    assert all(read(client, "/api/v1/evidence/" + r["evidence_id"])["evidence_id"] == r["evidence_id"] for r in records)
    if identity.startswith("case8-cylinder."):
        assert {"case8", "cylinder"} <= {r["experiment_id"].get("value") for r in records}
    elif identity.startswith("mechanism."):
        assert all(r["result_ids"] == [] for r in records)
    else:
        assert any(identity in r["result_ids"] for r in records) or identity.startswith("gate.comparison.")


def test_mechanism_is_nonnumerical_and_explore_reuses_existing_ids(client, app):
    mechanism, scenes = load_foundation()
    registry = app.extensions["evidence_service"].registry
    references = set(mechanism.evidence_refs) | {r for scene in scenes.items for r in scene.evidence_refs}
    assert references <= set(registry.entries)
    assert not any("explore" in identity for identity in registry.entries)
    evidence = read(client, "/api/v1/evidence/ev.mechanism.theory-implementation")
    assert evidence["result_ids"] == evidence["result_contexts"] == []
    assert "SCHEMATIC" in {l["code"] for l in evidence["limitations"]}


@pytest.mark.parametrize("identity", ["ev.case8.D_u.entropy", "ev.case8.D_u.allocation", "ev.gate.Acoustic.allocation",
    "evidence.spectral.spectrum.q-0.396", "ev.cylinder.D_u.sectors", "ev.entropy-closure.D_u-cfl-0.05.run",
    "ev.mechanism.theory-implementation"])
def test_schema_hash_separation_unknown_dates_and_asset_details(client, identity):
    record = read(client, "/api/v1/evidence/" + identity)
    assert set(record) == set(EvidenceRecord.model_fields)
    assert record["created_at"]["state"] == record["verified_at"]["state"] == "UNKNOWN"
    assert {a["asset_id"] for a in record["source_assets"]} == {o["asset_id"] for o in record["source_observations"]}
    assert record["method_hash"]["state"] == "KNOWN"
    assert record["recorded_source_hash"] == record["method_hash"]
    if identity.startswith(("ev.cylinder.", "ev.entropy-closure.")):
        assert record["data_hash"]["state"] == "UNKNOWN"
    elif record["data_hash"]["state"] == "KNOWN":
        assert record["data_hash"] != record["method_hash"]
    for asset in record["source_assets"]:
        public = read(client, "/api/v1/assets/" + asset["asset_id"])
        assert set(public) == set(SourceAsset.model_fields)
        assert public["recorded_data_hash"] == asset["recorded_data_hash"]
    response = client.get("/api/v1/evidence/" + identity)
    assert "ETag" not in response.headers  # Transport hash is not a scientific hash.


@pytest.mark.parametrize("facts,expected", [([], "UNKNOWN"), ([known(False), unresolved("Not observed")], "UNKNOWN"),
    ([known(False), known(False)], False), ([known(True), unresolved("Missing"), known(False)], True)])
def test_drift_aggregates_all_dependencies_with_true_priority(facts, expected):
    result = aggregate_drift(facts)
    assert result == known(expected) if isinstance(expected, bool) else result["state"] == expected


def test_case8_data_drift_remains_inspectable_and_blocks_numeric_delivery(tmp_path):
    relative = C.J2B_RUN_ROOT_REL + "/" + C.HISTORY_REL_TEMPLATE.format(config="D_u")
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(SOURCE / relative, target)
    app = create_app(case8_adapter=Case8Adapter(tmp_path), allocation_adapter=None, spectral_adapter=None,
                     cylinder_adapter=None, closure_adapter=None)
    client = app.test_client()
    numeric = "/api/v1/experiments/case8/configs/D_u/scalar-series/E_at_cumulative?limit=1"
    assert client.get(numeric).status_code == 200
    target.write_bytes(target.read_bytes() + b"\n")
    record = read(client, "/api/v1/evidence/ev.case8.D_u.entropy")
    assert record["source_drift"] == known(True)
    assert record["verification"]["status"] == "PARTIAL"
    assert read(client, "/api/v1/results/case8.D_u.E_at_cumulative/provenance")["provenance"]["source_drift"] == known(True)
    response = client.get(numeric)
    assert response.status_code == 409 and response.json["error"]["code"] == "SOURCE_DATA_DRIFT"
    assert "data" not in response.json
    assert read(client, "/api/v1/evidence?experiment_id=case8")["items"] == []
    filtered = read(client, "/api/v1/evidence?section=GAPS&experiment_id=case8&status=PARTIAL&limit=200")
    assert "ev.case8.D_u.entropy" in {i["evidence_id"] for i in filtered["items"]}
    assert all(i["verification"]["status"] == "PARTIAL" for i in filtered["items"])


@pytest.mark.parametrize("family", ["gate", "cylinder", "closure", "spectral"])
def test_all_source_families_keep_evidence_readable_on_data_drift(tmp_path, family):
    choices = {"gate": "ev.gate.Acoustic.allocation", "cylinder": "ev.cylinder.D_u.sectors",
        "closure": "ev.entropy-closure.D_u-cfl-0.05.run", "spectral": "evidence.spectral.spectrum.q-0.396"}
    identity = choices[family]
    service = EvidenceService(tmp_path)
    raw = service.registry.record(identity)
    asset = next(a for a in raw["source_assets"] if a["role"] == "DATA" and a["recorded_data_hash"]["state"] == "KNOWN")
    target = tmp_path / asset["relative_origin"]["value"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / asset["relative_origin"]["value"], target)
    target.write_bytes(target.read_bytes() + b"tampered")
    record = service.load_evidence(identity).model_dump(mode="json")
    assert record["source_drift"] == known(True)
    assert record["verification"]["status"] == "PARTIAL"
    assert record["result_ids"]  # Recorded contexts survive drift/missing other inputs.
    observed = service.load_asset(asset["asset_id"]).model_dump(mode="json")
    assert observed["data_drift"] == known(True)
    assert observed["current_data_hash"] != observed["recorded_data_hash"]


@pytest.mark.parametrize("family", ["gate", "cylinder", "closure", "spectral"])
def test_numeric_apis_preserve_source_data_drift_409_across_families(tmp_path, family):
    from backend.adapters.cylinder import COMMON as CYL_COMMON
    from backend.adapters.spectral_data import COMMON as SPEC_COMMON, SPECTRUM
    if family == "gate":
        adapter = IntegratedAllocationAdapter(gate_root=tmp_path)
        relatives = [a["relative_origin"]["value"] for a in adapter._gate_assets("Acoustic")]
        kwargs = {"allocation_adapter": adapter}
        evidence, numeric = "ev.gate.Acoustic.allocation", "/api/v1/allocations/gate.Acoustic.allocation/metadata"
    elif family == "cylinder":
        relatives, kwargs = list(CYL_COMMON), {"cylinder_adapter": CylinderAdapter(tmp_path)}
        evidence, numeric = "ev.cylinder.D_u.sectors", "/api/v1/experiments/cylinder/configs/D_u/allocation/sectors"
    elif family == "closure":
        relatives, kwargs = list(L.COMMON), {"closure_adapter": EntropyClosureAdapter(tmp_path)}
        evidence, numeric = "ev.entropy-closure.D_u-cfl-0.05.run", "/api/v1/experiments/entropy-closure/runs/D_u-cfl-0.05"
    else:
        relatives, kwargs = [S.FREEZE_DIR + "/" + n for n in (*SPEC_COMMON, *SPECTRUM)], {"spectral_adapter": SpectralAdapter(tmp_path)}
        evidence, numeric = "evidence.spectral.spectrum.q-0.396", "/api/v1/spectra/spectrum.q-0.396/points"
    for relative in relatives:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, target)
    target = tmp_path / relatives[0]
    target.write_bytes(target.read_bytes() + b"drift")
    client = create_app(**kwargs).test_client()
    record = read(client, "/api/v1/evidence/" + evidence)
    assert record["source_drift"] == known(True)
    response = client.get(numeric)
    assert response.status_code == 409 and response.json["error"]["code"] == "SOURCE_DATA_DRIFT"
    assert "data" not in response.json


def test_missing_source_is_unknown_drift_and_not_false(tmp_path):
    service = EvidenceService(tmp_path)
    record = service.load_evidence("ev.entropy-closure.D_u-cfl-0.05.run").model_dump(mode="json")
    assert record["source_drift"]["state"] == "UNKNOWN"
    assert record["result_ids"]
    assert all(a["current_data_hash"]["state"] == "MISSING" for a in record["source_assets"])


def test_recorded_bu_zero_is_preserved_separately_from_missing(client):
    history = read(client, "/api/v1/experiments/entropy-closure/runs/B_u-cfl-0.05/stage-history?limit=1")
    at = next(s for s in history["series"] if s["series_id"].endswith("D_at"))
    assert at["points"][0]["value"] == known(0.0)
    gap = read(client, "/api/v1/evidence/ev.gap.closure-spatial-trajectory")
    assert gap["verification"]["status"] == "MISSING" and gap["result_ids"] == []


def test_evidence_readers_never_invoke_numeric_adapters(client, monkeypatch):
    for adapter in (Case8Adapter, CylinderAdapter, EntropyClosureAdapter, SpectralAdapter):
        for method in ("load_evidence", "load_provenance", "load_scalar_series", "load_run", "load_sectors", "load_spectral_points"):
            if hasattr(adapter, method):
                monkeypatch.setattr(adapter, method, lambda *a, **k: pytest.fail("Evidence request invoked numerical reader"))
    assert read(client, "/api/v1/evidence/ev.cylinder.D_u.sectors")["evidence_id"] == "ev.cylinder.D_u.sectors"
    assert read(client, "/api/v1/results/case8-cylinder.D_u.D_u/provenance")["evidence_records"]


def test_public_dtos_and_routes_have_no_locator_or_download(client, app):
    regex = re.compile(r"[A-Za-z]:[\\/]|file://|absolute_source_path", re.IGNORECASE)
    for url in ("/api/v1/evidence?section=HISTORY&limit=3", "/api/v1/evidence/ev.cylinder.D_u.sectors",
                "/api/v1/results/case8-cylinder.D_u.D_u/provenance", "/api/v1/assets/asset_8d15c3f16f95"):
        response = client.get(url)
        assert response.status_code == 200 and not regex.search(response.get_data(as_text=True))
        assert "Content-Disposition" not in response.headers
    assert not any("download" in rule.rule or "file" in rule.rule for rule in app.url_map.iter_rules())
    for url in ("/api/v1/assets/asset_8d15c3f16f95?path=D:/Paper/passage6", "/api/v1/assets/asset_8d15c3f16f95?download=true"):
        assert client.get(url).status_code == 400
    assert client.get("/api/v1/assets/asset_8d15c3f16f95/download").status_code == 404


@pytest.mark.parametrize("origin", ["D:/Paper/passage6/file", "file:///D:/Paper/file", "../secret", "\\\\host\\share\\file", "/tmp/file"])
def test_source_asset_model_rejects_absolute_or_escaping_origin(app, origin):
    raw = app.extensions["evidence_service"].load_asset("asset_8d15c3f16f95").model_dump(mode="python")
    raw["relative_origin"] = known(origin)
    with pytest.raises(ValidationError):
        SourceAsset.model_validate(raw)


def test_all_formal_registries_have_evidence_and_accepted_metadata_is_canonical(app):
    service = app.extensions["evidence_service"]
    from backend.services.cylinder_resources import RESULT_IDS as cylinder
    from backend.services.closure_resources import RESULT_IDS as closure
    assert set(SELECTORS) | set(cylinder) | set(closure) <= set(service.registry.result_evidence)
    for identity in service.registry.catalog["records"]:
        raw = service.registry.record(identity)
        EvidenceRecord.model_validate(raw)
        assert set(raw["result_ids"]) == {r["result_id"] for r in raw["result_contexts"]}
        assert all(ref in service.registry.entries for ref in raw["related_evidence_refs"])
    assert {service.registry.index_metadata(i)[0]["experiment_id"].get("value") for i in service.registry.entries} >= {
        "case8", "gate", "spectrum", "modal-validation", "cylinder", "entropy-closure", "mechanism"}


def test_openapi_runtime_saved_document_and_four_frozen_operations(app, client):
    document = export_openapi(app.extensions["operation_catalog"])
    validate(document)
    assert document == client.get("/api/v1/openapi.json").json
    assert document == json.loads((ROOT / "config/openapi.json").read_text(encoding="utf-8"))
    paths = {"/api/v1/evidence": "EVI01", "/api/v1/evidence/{evidence_id}": "EVI02",
             "/api/v1/results/{result_id}/provenance": "EVI03", "/api/v1/assets/{asset_id}": "EVI04"}
    for path, identity in paths.items():
        assert document["paths"][path]["get"]["operationId"] == identity
    parameters = {p["name"]: p["schema"] for p in document["paths"]["/api/v1/evidence"]["get"]["parameters"]}
    assert set(parameters) == set(EvidenceQuery.model_fields)
    assert parameters["limit"]["default"] == 50 and parameters["limit"]["maximum"] == 200
