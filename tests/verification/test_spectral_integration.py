"""Phase 7C: mandatory real-source integration, no scientific execution.

Missing source installations fail acceptance rather than silently skipping it.
Fault injection replaces only an adapter's in-memory read seam.
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from backend import create_app
from backend.adapters.spectral_data import SpectralAdapter
from backend.core.errors import missing_asset
from backend.models import EvidenceRecord, ResultProvenance, ScientificArray, known
from backend.models.spectral_api import (SpectrumCurveView, SpectrumDatasetView,
                                         SpectralPointView, EigenmodeView, GrowthValidationView)
from backend.registry import spectral_registry as R

ROOT = Path(R.SCIENTIFIC_ROOT) / R.FREEZE_DIR
BASE = "/api/v1"


@pytest.fixture(scope="module")
def client():
    assert ROOT.is_dir(), "Real frozen source is required for Phase 7C acceptance"
    app = create_app()
    app.testing = True
    return app.test_client()


def read(client, path, model):
    response = client.get(BASE + path)
    assert response.status_code == 200, response.json
    model.model_validate_json(json.dumps(response.json["data"]))
    return response.json["data"]


def evidence_chain(client, value):
    rid = value["result"]["result_id"]
    for ref in value["provenance"]["evidence_refs"]:
        record = read(client, "/evidence/" + ref, EvidenceRecord)
        assert record["result_ids"] == [rid]
        assert record["config_id"]["value"] == value["result"]["config_id"]
        assert record["verification"]["status"] == "FROZEN_VERIFIED"
        assert record["source_drift"]["value"] is False
        assert {a["asset_id"] for a in record["source_assets"]} == set(value["provenance"]["source_asset_ids"])
        for asset in record["source_assets"]:
            digest = hashlib.sha256((Path(R.SCIENTIFIC_ROOT) / asset["relative_origin"]["value"]).read_bytes()).hexdigest()
            assert asset["current_data_hash"]["value"] == asset["recorded_data_hash"]["value"] == digest
    provenance = read(client, f"/results/{rid}/provenance", ResultProvenance)
    assert provenance["provenance"] == value["provenance"]


@pytest.mark.parametrize("dataset,q", list(R.DATASETS.items()))
def test_real_spectrum_all_17_modes_exact_csv_npz_api_and_evidence(client, dataset, q):
    summary = read(client, f"/spectra/{dataset}", SpectrumDatasetView)
    assert summary["q_at"] == q and summary["mode_indices"] == list(range(17))
    assert summary["matrix_source"]["state"] == "MISSING"
    evidence_chain(client, summary)
    curve = read(client, f"/spectra/{dataset}/points", SpectrumCurveView)
    assert [p["mode_index"] for p in curve["points"]] == list(range(17))
    with (ROOT / "spectrum/spectral_summary.csv").open() as stream:
        rows = [row for row in csv.DictReader(stream) if float(row["q_at"]) == q]
    with np.load(ROOT / "spectrum/eigenvalues.npz", allow_pickle=False) as data:
        values = data["eigenvalues"][list(R.DATASETS.values()).index(q)]
    for point, row, block in zip(curve["points"], rows, values, strict=True):
        mode = point["mode_index"]
        assert point["real_lambda"]["value"] == float(row["alpha"]) == block[0].real
        assert point["imag_lambda"]["value"] == float(row["leading_imag"]) == block[0].imag
        assert point["wave_number"]["value"] == float(row["kappa"])
        single = read(client, f"/spectra/{dataset}/points/{mode}", SpectralPointView)
        # Observation times are fresh; recorded numbers and references are exact.
        assert single["real_lambda"] == point["real_lambda"]
        assert single["spectrum_record_id"] == point["spectrum_record_id"]
    evidence_chain(client, curve)


@pytest.mark.parametrize("dataset", list(R.DATASETS))
def test_real_eigenmode_every_block_complex_array_and_evidence(client, dataset):
    qi = list(R.DATASETS).index(dataset)
    with np.load(ROOT / "spectrum/right_eigenvectors.npz", allow_pickle=False) as data:
        recorded = data["vectors"][qi, :, :, 0]
    for mode in range(17):
        view = read(client, f"/spectra/{dataset}/eigenmodes/{mode}", EigenmodeView)
        ref = view["values_ref"]
        array = read(client, f'/results/{ref["result_id"]}/arrays/eigenvector', ScientificArray)
        assert array["descriptor"]["shape"] == [128, 4]
        actual = np.array([v["real"] + 1j * v["imag"] for v in array["values"]])
        assert np.array_equal(actual, recorded[mode])
        assert array["result"]["provenance"] == view["provenance"]
    evidence_chain(client, view)
    revision = client.get(BASE + f'/results/{ref["result_id"]}/arrays/eigenvector',
                          query_string={"registry_revision": R.REGISTRY_REVISION})
    assert revision.status_code == 200
    bad = client.get(BASE + f'/results/{ref["result_id"]}/arrays/eigenvector',
                     query_string={"registry_revision": "wrong"})
    assert bad.status_code == 409


@pytest.mark.parametrize("run", list(R.RUNS))
def test_real_all_24_validation_runs_preserve_rates_branch_and_missing_history(client, run):
    view = read(client, f"/spectra/validation/{run}", GrowthValidationView)
    with (ROOT / "cfd_validation/validation_summary.csv").open() as stream:
        row = next(r for r in csv.DictReader(stream) if (int(r["m"]), float(r["q_at"]), float(r["epsilon"])) == R.RUNS[run][:3])
    with (ROOT / R.RUNS[run][3]).open() as stream:
        history = list(csv.DictReader(stream))
    assert view["result"]["availability"] == "PARTIAL"
    assert all(v["state"] == "MISSING" for v in view["linear_amplitude"])
    assert view["step_indices"] == list(range(33))
    assert [v["value"] for v in view["cfd_amplitude"]] == [float(r["modal_amplitude"]) for r in history]
    assert view["time"] == [float(r["physical_time"]) for r in history]
    for key, column in (("linear", "sigma_LIN"), ("rk3", "sigma_RK3"), ("cfd", "sigma_CFD")):
        assert view["growth_rate"][key]["value"] == float(row[column])
    assert view["error"]["relative_discrepancy"]["value"] == float(row["relative_discrepancy_CFD_RK3"])
    assert f'.rank-{int(row["rank"]):02d}.' in view["eigenmode_id"]
    evidence_chain(client, view)


def test_missing_saved_vectors_and_arrays_never_return_values(monkeypatch):
    adapter = SpectralAdapter()
    original = adapter._read_bytes
    def read_bytes(name):
        if name == "spectrum/right_eigenvectors.npz":
            raise missing_asset("Injected absent saved asset", resource_type="asset", identity=known(R.ASSETS[name][0]))
        return original(name)
    monkeypatch.setattr(adapter, "_read_bytes", read_bytes)
    client = create_app(spectral_adapter=adapter).test_client()
    for path, code in (("/spectra/spectrum.q-0.000/eigenmodes/1", "MISSING_EIGENMODE"),
                       (f'/results/{R.eigenmode_id("spectrum.q-0.000",1,"RIGHT",0)}/arrays/eigenvector', "MISSING_ASSET")):
        response = client.get(BASE + path)
        assert response.status_code == 404 and response.json["error"]["code"] == code
        assert "data" not in response.json


def test_positive_entropy_does_not_imply_uniform_modal_damping(client):
    # Positive Case8 production budget is separately sourced; it is not the
    # zero-output spectral base state, nor a matched spectrum/entropy sample.
    path = Path(R.SCIENTIFIC_ROOT) / "jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs/case8_D_u/stage_weighted_history.csv"
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    assert float(rows[-1]["E_at"]) > 0
    curves = [read(client, f"/spectra/{dataset}/points", SpectrumCurveView) for dataset in ("spectrum.q-0.000", "spectrum.q-0.396")]
    delta = [b["real_lambda"]["value"] - a["real_lambda"]["value"] for a,b in zip(curves[0]["points"], curves[1]["points"], strict=True)]
    assert delta[3] < 0 and delta[4] < 0
    assert delta[1] > 0 and delta[8] > 0 and delta[12] > 0
    assert curves[1]["points"][16]["real_lambda"]["value"] > 0
    assert abs(delta[16]) < 1e-10
