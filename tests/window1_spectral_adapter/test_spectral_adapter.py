"""Offline fault tests plus exact comparisons with read-only frozen assets.

Fault injection uses synthetic immutable in-memory bytes, never source edits
or copied scientific files. Real-source tests skip explicitly if not installed.
"""
import csv
import hashlib
import json
from copy import deepcopy
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest

from backend.adapters.spectral import SpectralAdapterProtocol
from backend.adapters.spectral_data import COMMON, SPECTRUM, SpectralAdapter
from backend.models.core import fact_value
from backend.models.results import ScientificArray
from backend.registry import spectral_registry as R


def npz_bytes(**arrays):
    out = BytesIO()
    np.savez_compressed(out, **arrays)
    return out.getvalue()


def csv_bytes(columns, rows):
    from io import StringIO
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


@pytest.fixture
def memory_source(monkeypatch):
    """SYNTHETIC ONLY: independent of any local scientific installation."""
    q = np.array(list(R.DATASETS.values()))
    modes = np.arange(17, dtype=np.int64)
    values = np.full((4, 17, 512), -10.0 + 2j, dtype=np.complex128)
    for qi in range(4):
        for m in range(17):
            values[qi, m, 0] = float(m) - 8 + qi / 10 + (m + 1) * 1j
    base = np.zeros((128, 4))
    config = {"method_id": R.METHOD_NAME, "method_sha256": R.METHOD_HASH, "physics": {"mach": 6.0},
              "q_at": q.tolist(), "q_aa": 3.96, "modes": modes.tolist(),
              "mesh": {"nx": 128, "ny": 32, "xlim": [0.0, 1.0], "ylim": [0.0, 1.0]},
              "numerics": {"integrator": "SSP-RK3", "reconstruction": "none"}}
    vectors = np.zeros((4, 17, 512, 32), dtype=np.complex128)
    vectors[:, :, :, 0] = np.arange(512) + (np.arange(512) + 0.25) * 1j
    blobs = {name: b"synthetic frozen method evidence" for name in COMMON}
    for name, value in {
        "config.json": config,
        "method_identity.json": {"expected_sha256": R.METHOD_HASH, "actual_sha256": R.METHOD_HASH, "method_hash": "MATCH"},
        "validity_gates.json": {"checks": {"synthetic": "PASS"}},
        "base_state/base_state_audit.json": {"converged": True, "shared_B_D": True},
        "spectrum/shock_mask.json": {"indices": list(range(58, 67)), "rule": "SYNTHETIC fixed mask"},
    }.items():
        blobs[name] = json.dumps(value).encode()
    blobs["base_state/base_state.npz"] = npz_bytes(Ubar=base, Ubar_2d=np.broadcast_to(base, (32, 128, 4)), x=np.zeros(128), y=np.zeros(32))
    blobs["spectrum/eigenvalues.npz"] = npz_bytes(eigenvalues=values, q_at=q, m=modes)
    for side in ("right", "left"):
        blobs[f"spectrum/{side}_eigenvectors.npz"] = npz_bytes(vectors=vectors, q_at=q, m=modes, ranks=np.arange(32, dtype=np.int64))
    rows = [{"m": m, "q_at": float(q[qi]), "kappa": float(m), "alpha": float(values[qi, m, 0].real),
             "leading_imag": float(values[qi, m, 0].imag)} for m in range(17) for qi in range(4)]
    blobs["spectrum/spectral_summary.csv"] = csv_bytes(list(rows[0]), rows)
    adapter = SpectralAdapter()
    assets = deepcopy(R.ASSETS)
    def pin():
        for name, raw in blobs.items():
            if name != "SHA256_MANIFEST.json":
                asset = assets[name]
                assets[name] = (asset[0], hashlib.sha256(raw).hexdigest(), *asset[2:])
        entries = [{"path": name, "sha256": assets[name][1]} for name in blobs if name != "SHA256_MANIFEST.json"]
        blobs["SHA256_MANIFEST.json"] = json.dumps({"artifacts": entries}).encode()
        asset = assets["SHA256_MANIFEST.json"]
        assets["SHA256_MANIFEST.json"] = (asset[0], hashlib.sha256(blobs["SHA256_MANIFEST.json"]).hexdigest(), *asset[2:])
        monkeypatch.setattr(R, "ASSETS", assets)
    pin()
    def read(name):
        if name not in blobs:
            from backend.core.errors import missing_asset
            from backend.models.core import known
            raise missing_asset("Synthetic missing dependency", resource_type="asset", identity=known(assets[name][0]))
        return blobs[name], (len(blobs[name]), 1, 1)
    monkeypatch.setattr(adapter, "_read_bytes", read)
    return adapter, blobs, pin


def assert_failure(slot, availability, code):
    assert slot.root.availability == availability
    assert slot.root.error.code == code
    assert "value" not in slot.model_dump()


@pytest.fixture
def memory_growth(memory_source):
    adapter, blobs, pin = memory_source
    eigenvalues = adapter._npz(blobs["spectrum/eigenvalues.npz"])["eigenvalues"]
    choices = [{"m": m, "q_at": q, "rank": 1 if q == .396 and m in (1, 4) else 0, "branch_id": 0}
               for m in (1, 4, 8, 12) for q in (0.0, .396)]
    rows = []
    for mode, q, eps, name in R.RUNS.values():
        rank = next(c["rank"] for c in choices if c["m"] == mode and c["q_at"] == q)
        lam = eigenvalues[list(R.DATASETS.values()).index(q), mode, rank]
        rk3, cfd = float(lam.real) - .125, float(lam.real) + .125
        absolute = abs(cfd - rk3)
        rows.append({"m": mode, "q_at": q, "epsilon": eps, "branch_id": 0, "rank": rank,
                     "lambda_real": float(lam.real), "lambda_imag": float(lam.imag),
                     "sigma_LIN": float(lam.real), "sigma_RK3": rk3, "sigma_CFD": cfd,
                     "fit_start_step": 0, "fit_end_step": 32, "fit_points": 33,
                     "absolute_discrepancy_CFD_RK3": absolute,
                     "relative_discrepancy_CFD_RK3": absolute / max(abs(rk3), 1.0),
                     "history_path": name.removeprefix("cfd_validation/")})
        history = [{"accepted_step": step, "physical_time": step / 100.0, "modal_amplitude": eps + step / 100000.0}
                   for step in range(33)]
        blobs[name] = csv_bytes(list(history[0]), history)
    blobs["cfd_validation/validation_summary.csv"] = csv_bytes(list(rows[0]), rows)
    blobs["cfd_validation/mode_selection.json"] = json.dumps({"choices": choices}).encode()
    blobs["scripts/cfd_validation.py"] = b"synthetic validation evidence"
    pin()
    return adapter, blobs, pin


def assert_provenance(result):
    assert result.verification.status == "FROZEN_VERIFIED"
    assert result.verification.evidence_refs
    assert result.provenance.source_drift.root.value is False
    assets = {a.asset_id: a for a in result.evidence.source_assets}
    for ref in result.provenance.source_asset_ids:
        asset = assets[ref]
        assert asset.source_display and fact_value(asset.relative_origin)
        assert fact_value(asset.recorded_data_hash) == fact_value(asset.current_data_hash)
        assert len(fact_value(asset.current_data_hash)) == 64


def test_offline_modes_parameters_complex_and_provenance(memory_source):
    adapter, _, _ = memory_source
    assert isinstance(adapter, SpectralAdapterProtocol)
    datasets = adapter.list_spectral_datasets()
    assert [d.parameter_value for d in datasets] == [0.0, 0.132, 0.264, 0.396]
    for dataset in datasets:
        assert_provenance(dataset)
        curve = adapter.load_spectral_points(dataset.dataset_id).root.value
        assert len(curve.points) == 17
        assert [p.mode_index for p in curve.points] == list(range(17))
        assert len({p.spectrum_record_id for p in curve.points}) == 17
        for point in curve.points:
            assert_provenance(point)
            assert fact_value(point.imag_lambda) != 0
    model = adapter.load_eigenmode(datasets[0].dataset_id, 8).root.value
    array = adapter.load_array(model.values_ref.result_id, "eigenvector").root.value
    restored = ScientificArray.model_validate_json(array.model_dump_json())
    assert restored.values[7].real == 7.0 and restored.values[7].imag == 7.25
    assert restored.descriptor.shape == [128, 4]
    assert restored.descriptor.dtype == "complex128"


@pytest.mark.parametrize("name", [*COMMON, *SPECTRUM])
def test_missing_dependencies_are_typed(memory_source, name):
    adapter, blobs, _ = memory_source
    del blobs[name]
    assert_failure(adapter.load_spectral_points("spectrum.q-0.000"), "MISSING", "MISSING_ASSET")


@pytest.mark.parametrize("name", [*COMMON, *SPECTRUM, "spectrum/right_eigenvectors.npz"])
def test_hash_drift_prevents_numeric_results(memory_source, name):
    adapter, blobs, _ = memory_source
    blobs[name] += b"tampered"
    slot = adapter.load_eigenmode("spectrum.q-0.000", 8) if "right_eigenvectors" in name else adapter.load_spectral_points("spectrum.q-0.000")
    assert_failure(slot, "ERROR", "SOURCE_DATA_DRIFT")


def test_missing_vector_and_validation_do_not_disable_spectrum(memory_source):
    adapter, blobs, _ = memory_source
    del blobs["spectrum/right_eigenvectors.npz"]
    assert_failure(adapter.load_eigenmode("spectrum.q-0.000", 0), "MISSING", "MISSING_ASSET")
    assert adapter.load_spectral_points("spectrum.q-0.000").root.availability == "AVAILABLE"
    capabilities = adapter.describe_capabilities()
    assert capabilities["eigenmode"]["RIGHT"]["status"] == "MISSING"
    assert capabilities["eigenmode"]["LEFT"]["status"] == "SUPPORTED"
    assert all(v["status"] == "MISSING" for v in capabilities["growth_validation"].values())
    assert capabilities["linear_amplitude"]["status"] == "MISSING"


@pytest.mark.parametrize("run", list(R.RUNS))
def test_offline_growth_24_run_mapping_and_missing_predictions(memory_growth, run):
    adapter, _, _ = memory_growth
    slot = adapter.load_growth_validation(run)
    assert slot.root.availability == "PARTIAL"
    value = slot.root.value
    assert_provenance(value)
    mode, q, eps, _ = R.RUNS[run]
    assert (value.mode_index, value.parameter_value, value.epsilon) == (mode, q, eps)
    assert value.step_indices == list(range(33))
    assert all(a.root.state == "MISSING" for a in value.linear_amplitude)
    rank = 1 if q == .396 and mode in (1, 4) else 0
    assert value.eigenmode_id == R.eigenmode_id(R.dataset_id(q), mode, "RIGHT", rank)


@pytest.mark.parametrize("name", ["cfd_validation/validation_summary.csv", "cfd_validation/mode_selection.json",
    "scripts/cfd_validation.py", R.RUNS[next(iter(R.RUNS))][3]])
@pytest.mark.parametrize("failure", ["missing", "drift"])
def test_growth_dependency_failure_is_unavailable(memory_growth, name, failure):
    adapter, blobs, _ = memory_growth
    if failure == "missing": del blobs[name]
    else: blobs[name] += b"changed"
    slot = adapter.load_growth_validation(next(iter(R.RUNS)))
    assert_failure(slot, "MISSING" if failure == "missing" else "ERROR",
                   "MISSING_ASSET" if failure == "missing" else "SOURCE_DATA_DRIFT")
    assert adapter.load_spectral_points("spectrum.q-0.000").root.availability == "AVAILABLE"


@pytest.mark.parametrize("kind", ["time_order", "step_count", "negative_amplitude", "branch_rank", "history_path", "rates", "discrepancy"])
def test_growth_rehashed_schema_or_identity_failure(memory_growth, kind):
    adapter, blobs, pin = memory_growth
    run = next(iter(R.RUNS))
    name = R.RUNS[run][3] if kind in ("time_order", "step_count", "negative_amplitude") else "cfd_validation/validation_summary.csv"
    rows = adapter._csv(blobs[name])
    if kind == "time_order": rows[1]["physical_time"] = 0.0
    if kind == "step_count": rows.pop()
    if kind == "negative_amplitude": rows[0]["modal_amplitude"] = -1.0
    if kind == "branch_rank": rows[0]["rank"] = 31
    if kind == "history_path": rows[0]["history_path"] = "../../arbitrary.csv"
    if kind == "rates": rows[0]["sigma_LIN"] = 123.0
    if kind == "discrepancy": rows[0]["relative_discrepancy_CFD_RK3"] = 100.0
    blobs[name] = csv_bytes(list(rows[0]), rows)
    pin()
    assert_failure(adapter.load_growth_validation(run), "ERROR", "CANONICAL_SCHEMA_MISMATCH")


@pytest.mark.parametrize("kind", ["q_order", "mode_order", "mode_count", "dtype", "summary_count", "summary_order", "duplicate", "alpha"])
def test_rehashed_malformed_spectrum_rejected_without_reordering(memory_source, kind):
    adapter, blobs, pin = memory_source
    if kind in ("summary_count", "summary_order", "duplicate", "alpha"):
        rows = adapter._csv(blobs["spectrum/spectral_summary.csv"])
        if kind == "summary_count": rows.pop()
        if kind == "summary_order": rows.reverse()
        if kind == "duplicate": rows[1] = rows[0]
        if kind == "alpha": rows[0]["alpha"] = 0.125
        blobs["spectrum/spectral_summary.csv"] = csv_bytes(list(rows[0]), rows)
    else:
        arrays = adapter._npz(blobs["spectrum/eigenvalues.npz"])
        if kind == "q_order": arrays["q_at"] = arrays["q_at"][::-1]
        if kind == "mode_order": arrays["m"] = arrays["m"][::-1]
        if kind == "mode_count": arrays["m"] = arrays["m"][:-1]
        if kind == "dtype": arrays["eigenvalues"] = arrays["eigenvalues"].real
        blobs["spectrum/eigenvalues.npz"] = npz_bytes(**arrays)
    pin()
    assert_failure(adapter.load_spectral_points("spectrum.q-0.000"), "ERROR", "CANONICAL_SCHEMA_MISMATCH")


@pytest.mark.parametrize("kind", ["ranks", "real_vector", "flat_vector", "nan", "corrupt_npz"])
def test_rehashed_malformed_complex_vector_rejected(memory_source, kind):
    adapter, blobs, pin = memory_source
    name = "spectrum/right_eigenvectors.npz"
    data = adapter._npz(blobs[name])
    if kind == "ranks": data["ranks"] = data["ranks"][::-1]
    if kind == "real_vector": data["vectors"] = data["vectors"].real
    if kind == "flat_vector": data["vectors"] = data["vectors"].ravel()
    if kind == "nan": data["vectors"][0, 0, 0, 0] = complex(float("nan"), 1)
    blobs[name] = b"invalid archive" if kind == "corrupt_npz" else npz_bytes(**data)
    pin()
    assert_failure(adapter.load_eigenmode("spectrum.q-0.000", 0), "ERROR", "CANONICAL_SCHEMA_MISMATCH")


@pytest.mark.parametrize("kind", ["bytes", "stamp", "disappeared"])
def test_changed_dependency_between_reads(memory_source, monkeypatch, kind):
    adapter, blobs, _ = memory_source
    original = adapter._read_bytes
    counts = {}
    def read(name):
        counts[name] = counts.get(name, 0) + 1
        raw, stamp = original(name)
        if name == "config.json" and counts[name] == 2:
            if kind == "disappeared":
                del blobs[name]
                return original(name)
            return (raw + b"changed", stamp) if kind == "bytes" else (raw, (stamp[0], 2, 1))
        return raw, stamp
    monkeypatch.setattr(adapter, "_read_bytes", read)
    assert_failure(adapter.load_spectral_points("spectrum.q-0.000"), "ERROR", "SOURCE_CHANGED_DURING_READ")


@pytest.mark.parametrize("selector", [0.132, "spectrum.q-0.200", "../../config.json", "D:/Paper/passage6", True])
def test_dataset_selector_is_registered_identity_only(memory_source, selector):
    adapter, _, _ = memory_source
    assert_failure(adapter.load_spectral_points(selector), "UNSUPPORTED", "UNSUPPORTED_COMBINATION")


@pytest.mark.parametrize("kwargs", [{"mode_index": True}, {"mode_index": "8"}, {"mode_index": 17},
    {"rank": True}, {"rank": -1}, {"rank": 32}, {"side": "right"}, {"projection": "MAGNITUDE"},
    {"field_component": "density"}, {"representation": "SCALAR_HEATMAP"},
    {"representation": "PRIMITIVE_PROFILE", "side": "LEFT", "projection": "AMPLITUDE", "field_component": "density"}])
def test_invalid_eigenmode_selection(memory_source, kwargs):
    adapter, _, _ = memory_source
    assert_failure(adapter.load_eigenmode("spectrum.q-0.000", **({"mode_index": 8} | kwargs)), "UNSUPPORTED", "UNSUPPORTED_COMBINATION")


def test_revision_and_array_reference_pair(memory_source):
    adapter, _, _ = memory_source
    assert_failure(adapter.describe_spectrum("spectrum.q-0.000", registry_revision="old"), "ERROR", "REVISION_UNAVAILABLE")
    assert_failure(adapter.load_eigenmode("spectrum.q-0.000", 1, registry_revision="old"), "ERROR", "REVISION_UNAVAILABLE")
    assert_failure(adapter.load_growth_validation(next(iter(R.RUNS)), registry_revision="old"), "ERROR", "REVISION_UNAVAILABLE")
    assert_failure(adapter.load_array(R.record_id("spectrum.q-0.000", 1), "vectors"), "UNSUPPORTED", "UNSUPPORTED_COMBINATION")
    assert_failure(adapter.load_array(R.record_id("spectrum.q-0.000", 1), "eigenvector"), "UNSUPPORTED", "UNSUPPORTED_COMBINATION")
    assert_failure(adapter.load_growth_validation("../../history.csv"), "UNSUPPORTED", "UNSUPPORTED_COMBINATION")


@pytest.fixture(scope="module")
def real():
    root = Path(R.SCIENTIFIC_ROOT) / R.FREEZE_DIR
    if not root.is_dir():
        pytest.skip("Read-only common Mach6 freeze not installed")
    return SpectralAdapter(), root


@pytest.mark.parametrize("dataset,q", list(R.DATASETS.items()))
def test_real_complete_spectrum_exact_source_order(real, dataset, q):
    adapter, root = real
    rows = [r for r in csv.DictReader((root / "spectrum/spectral_summary.csv").read_text().splitlines()) if float(r["q_at"]) == q]
    value = adapter.load_spectral_points(dataset).root.value
    assert [p.mode_index for p in value.points] == [int(r["m"]) for r in rows] == list(range(17))
    assert [fact_value(p.spectral_abscissa) for p in value.points] == [float(r["alpha"]) for r in rows]
    assert [fact_value(p.imag_lambda) for p in value.points] == [float(r["leading_imag"]) for r in rows]
    assert [fact_value(p.wave_number) for p in value.points] == [float(r["kappa"]) for r in rows]
    for point in value.points:
        assert_provenance(point)
    desc = adapter.describe_spectrum(dataset).root.value
    assert desc.record_count == 17 and desc.matrix_source.root.state == "MISSING"
    assert fact_value(desc.wave_number_range.wave_numbers) == [float(r["kappa"]) for r in rows]
    array = adapter.load_array(value.points[8].eigenvalues_ref.result_id, "eigenvalues").root.value
    with np.load(root / "spectrum/eigenvalues.npz", allow_pickle=False) as z:
        block = z["eigenvalues"][list(R.DATASETS).index(dataset), 8]
        assert np.array_equal(np.array([complex(v.real, v.imag) for v in array.values]), block)


@pytest.mark.parametrize("side", ["RIGHT", "LEFT"])
@pytest.mark.parametrize("rank", [0, 1, 31])
@pytest.mark.parametrize("projection", ["COMPLEX", "REAL", "IMAGINARY", "AMPLITUDE"])
def test_real_complex_vectors_exact_without_projection_conversion(real, side, rank, projection):
    adapter, root = real
    model = adapter.load_eigenmode("spectrum.q-0.396", 4, side=side, rank=rank, projection=projection).root.value
    assert model.mode_index == 4 and model.rank == rank
    assert model.projection == projection and model.shape == [128, 4]
    assert_provenance(model)
    array = adapter.load_array(model.values_ref.result_id, "eigenvector").root.value
    with np.load(root / f"spectrum/{side.lower()}_eigenvectors.npz", allow_pickle=False) as z:
        original = z["vectors"][3, 4, :, rank]
    reconstructed = np.array([complex(v.real, v.imag) for v in array.values])
    assert np.array_equal(reconstructed, original)
    if side == "LEFT":
        assert model.localization_fraction.root.state == "MISSING"
    else:
        rows = list(csv.DictReader((root / "spectrum/eigenvector_metrics.csv").read_text().splitlines()))
        metric = next(r for r in rows if int(r["m"]) == 4 and float(r["q_at"]) == .396 and int(r["rank"]) == rank)
        assert fact_value(model.localization_fraction) == float(metric["shock_localization_fraction"])


@pytest.mark.parametrize("component,index", [("density", 0), ("u", 1), ("v", 2), ("pressure", 3)])
def test_real_saved_primitive_amplitude_only(real, component, index):
    adapter, root = real
    model = adapter.load_eigenmode("spectrum.q-0.264", 8, rank=31, representation="PRIMITIVE_PROFILE",
                                  projection="AMPLITUDE", field_component=component).root.value
    array = adapter.load_array(model.values_ref.result_id, "primitive_amplitude").root.value
    with np.load(root / "spectrum/leading_primitive_amplitude_profiles.npz", allow_pickle=False) as z:
        assert np.array_equal(np.array(array.values), z["amplitude"][2, 8, 31, :, index])


@pytest.mark.parametrize("run", list(R.RUNS))
def test_real_growth_rates_and_history_no_fitting_or_synthesis(real, run):
    adapter, root = real
    mode, q, eps, name = R.RUNS[run]
    rows = list(csv.DictReader((root / "cfd_validation/validation_summary.csv").read_text().splitlines()))
    row = next(r for r in rows if (int(r["m"]), float(r["q_at"]), float(r["epsilon"])) == (mode, q, eps))
    history = list(csv.DictReader((root / name).read_text().splitlines()))
    slot = adapter.load_growth_validation(run)
    assert slot.root.availability == "PARTIAL" and slot.root.issues[0].code == "MISSING_ASSET"
    value = slot.root.value
    assert_provenance(value)
    assert value.time == [float(r["physical_time"]) for r in history]
    assert value.step_indices == list(range(33))
    assert [fact_value(a) for a in value.cfd_amplitude] == [float(r["modal_amplitude"]) for r in history]
    assert all(a.root.state == "MISSING" for a in value.linear_amplitude)
    assert "value" not in value.linear_amplitude[0].model_dump()
    assert (fact_value(value.growth_rate.linear), fact_value(value.growth_rate.rk3), fact_value(value.growth_rate.cfd)) == tuple(float(row[k]) for k in ("sigma_LIN", "sigma_RK3", "sigma_CFD"))
    assert fact_value(value.error.relative_discrepancy) == float(row["relative_discrepancy_CFD_RK3"])
    assert value.eigenmode_id == R.eigenmode_id(R.dataset_id(q), mode, "RIGHT", int(row["rank"]))


def test_real_pinned_inventory_and_manifest_baselines(real):
    _, root = real
    project = Path(__file__).resolve().parents[2]
    inventory = json.loads((project / "data/data_asset_inventory.json").read_bytes())
    entries = {a["relative_source_path"]: a for a in inventory["assets"]}
    manifest = {a["path"]: a["sha256"] for a in json.loads((root / "SHA256_MANIFEST.json").read_bytes())["artifacts"]}
    for name, (aid, expected, *_) in R.ASSETS.items():
        asset = entries[f"{R.FREEZE_DIR}/{name}"]
        assert asset["asset_id"] == aid and asset["sha256"] == expected
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
        if name != "SHA256_MANIFEST.json":
            assert manifest[name] == expected
