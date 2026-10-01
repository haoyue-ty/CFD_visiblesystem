"""TEST-ONLY spectral adapter standing in for the Window 1 scientific loader.

Confined to the test tree and never imported by ``backend``. Every payload is MOCK and
uses the ``mock.`` result namespace so its numbers can never be mistaken for reproduced
science. It exists to prove the five SPEC operations carry ``representation``, ``q_at``,
``mode_index`` (where applicable), ``verification`` and ``provenance`` on every response
and map failures onto UNKNOWN_SPECTRUM / UNKNOWN_MODE / MISSING_EIGENMODE /
UNSUPPORTED_PARAMETER / SOURCE_ERROR without ever fabricating or interpolating a value.
"""
from backend.core.errors import DomainError, missing_asset, source_error, system_error, unsupported_combination
from backend.models.core import ResourceSlot, known, unresolved
from backend.models.spectral import (Eigenmode, GrowthValidation, SpectrumDataset,
                                     SpectralPoint, SpectralPoints)

Q_VALUES = (0.0, 0.132, 0.264, 0.396)
DATASET_IDS = {f"mock.spectrum.q-{q}": q for q in Q_VALUES}
RUN_IDS = {
    f"mock.modal-validation.m{m}_q{q}_eps1e-05": (m, q)
    for m in (1, 4, 8, 12) for q in (0.0, 0.396)
}
MASK_ID = "mock.mask.spectrum.fixed-shock-cells"
EVIDENCE = "mock.evidence.spectrum"


def _unknown(reason: str) -> dict:
    return unresolved(reason)


def _na(reason: str) -> dict:
    return unresolved(reason, "NOT_APPLICABLE")


def _unit(quantity: str) -> dict:
    return {"id": f"mock.unit.{quantity.replace(' ', '-')}", "system": "MODEL", "quantity": quantity,
            "label": f"model {quantity}", "si_mapping": _unknown("No SI mapping in mock data")}


def _verification() -> dict:
    return {"status": "NOT_APPLICABLE", "basis": ["Test-only fake spectral adapter"],
            "verified_at": _na("Mock"), "observation_at": _na("Mock"), "evidence_refs": [EVIDENCE]}


def _provenance() -> dict:
    return {"evidence_refs": [EVIDENCE], "source_asset_ids": ["mock.asset.spectrum"],
            "registry_revision": "mock.registry", "data_revision": "mock.data",
            "release_id": _na("Mock release"), "source_drift": _na("No drift check")}


def _scope(sampling: str) -> dict:
    return {"id": "mock.scope.spectrum", "description": "Test-only spectral scope",
            "boundary_scope": _unknown("Mock boundary"), "spatial_domain_ref": _unknown("Mock domain"),
            "mask_refs": [MASK_ID], "definition_refs": []}


def _result(result_id: str, *, experiment_id: str, config_id: str, semantic_id: str, sampling: str,
            unit_quantity: str) -> dict:
    return {
        "schema_version": "1.0.0", "result_id": result_id, "experiment_id": experiment_id,
        "config_id": config_id, "semantic_id": semantic_id, "data_origin": "MOCK", "availability": "AVAILABLE",
        "time": {"sampling": sampling, "accumulation": "NONE", "physical_time": _na("Mock static"),
                 "interval": _na("Mock"), "step_index": _na("No step"), "stage_index": _na("No stage"),
                 "snapshot_index": _na("No snapshot"), "index_convention": "Recorded Fourier mode 0..16"},
        "scope": _scope(sampling), "unit": _unit(unit_quantity), "verification": _verification(),
        "provenance": _provenance(), "limitations": [],
    }


def _mask() -> dict:
    return {"id": MASK_ID, "type": "SPECTRUM_FIXED_SHOCK_CELLS", "domain_refs": ["mock.scope.spectrum"],
            "definition": "Test-only fixed shock cells 58..66", "parameters": [],
            "index_sets": [{"axis": "x", "indices": list(range(58, 67)), "index_base": 0}],
            "mask_array_refs": [], "scope": _scope("STATIC"), "verification": _verification(),
            "evidence_refs": [EVIDENCE]}


def _dim() -> dict:
    return {"id": "mock.unit.coefficient", "system": "DIMENSIONLESS", "quantity": "coefficient",
            "label": "dimensionless", "si_mapping": _na("Dimensionless")}


def _config(dataset_id: str, q: float, *, config_id: str | None = None,
            experiment_id: str = "spectrum", run: tuple | None = None) -> dict:
    parameters = [{"name": "q_at", "value": known(q), "unit": _dim()},
                  {"name": "q_aa", "value": known(3.96), "unit": _dim()}]
    if run is not None:
        mode, epsilon = run
        parameters += [{"name": "mode", "value": known(float(mode)), "unit": _dim()},
                       {"name": "epsilon", "value": known(epsilon), "unit": _dim()}]
    return {
        "id": config_id or dataset_id, "experiment_id": experiment_id, "name": "Test-only spectral configuration",
        "parameters": parameters,
        "protocol": {"method_name": known("mock.method"), "method_hash": known("0" * 64),
                     "grid": _unknown("Mock grid"), "integrator": _unknown("Mock integrator"),
                     "reconstruction": _unknown("Mock reconstruction"), "final_time": _na("Mock static"),
                     "boundary_scope": _unknown("Mock boundary"), "protocol_asset_refs": ["mock.asset.spectrum"]},
        "verification": _verification(), "limitations": [], "evidence_refs": [EVIDENCE],
    }


def _context(result_id: str, dataset_id: str, q: float, *, experiment_id: str, config_id: str,
             semantic_id: str, unit_quantity: str, sampling: str = "STATIC",
             run: tuple | None = None) -> dict:
    """MOCK-only scientific context mirroring the frozen spectral model shape."""
    header = _result(result_id, experiment_id=experiment_id, config_id=config_id,
                     semantic_id=semantic_id, sampling=sampling, unit_quantity=unit_quantity)
    return {"result": header, "experiment_id": experiment_id, "configuration_id": config_id,
            "parameter_value": q, "verification": header["verification"], "provenance": header["provenance"],
            "evidence": {"configuration": _config(dataset_id, q, config_id=config_id,
                                                  experiment_id=experiment_id, run=run),
                         "source_assets": [{"asset_id": "mock.asset.spectrum",
                                            "source_id": "mock.spectrum.source", "source_display": "mock",
                                            "relative_origin": known("mock/spectrum"), "role": "DATA",
                                            "format": "NPZ", "recorded_data_hash": known("0" * 64),
                                            "current_data_hash": known("0" * 64), "data_drift": known(False),
                                            "verification": _verification(), "canonical_selected": True,
                                            "limitations": []}]}}


def _array_ref(result_id: str, array_id: str, shape: list[int], dtype: str, axes: list[str]) -> dict:
    return {"result_id": result_id, "descriptor": {"array_id": array_id, "dtype": dtype, "shape": shape,
            "axes": axes, "order": "C", "encoding": "FLAT_JSON",
            "element_count": shape[0] * shape[1] if len(shape) == 2 else shape[0]}}


def _dataset(dataset_id: str, q: float) -> SpectrumDataset:
    context = _context(dataset_id, dataset_id, q, experiment_id="spectrum", config_id=dataset_id,
                       semantic_id="spectral_abscissa", unit_quantity="inverse model time")
    return SpectrumDataset.model_validate({**context,
        "experiment_id": "spectrum", "dataset_id": dataset_id, "collection_id": "mock.collection",
        "base_result_id": "mock.base", "configuration_id": dataset_id, "parameter_value": q,
        "matrix_source": unresolved("No serialized Fourier matrices in mock data", "MISSING"),
        "wave_number_range": {"mode_indices": list(range(17)),
                              "wave_numbers": known([float(m) for m in range(17)]),
                              "definition": "Test-only kappa", "evidence_refs": [EVIDENCE]},
        "mask": _mask()})


def _point(dataset_id: str, q: float, mode: int) -> dict:
    rid = f"{dataset_id}.mode-{mode:02d}"
    context = _context(rid, dataset_id, q, experiment_id="spectrum", config_id=dataset_id,
                       semantic_id="spectral_abscissa", unit_quantity="inverse model time")
    return {**context, "experiment_id": "spectrum", "dataset_id": dataset_id, "collection_id": "mock.collection",
            "base_result_id": "mock.base", "configuration_id": dataset_id, "parameter_value": q,
            "spectrum_record_id": rid, "mode_index": mode, "wave_number": known(float(mode)),
            "real_lambda": known(-10.0 + mode), "imag_lambda": known(0.5 * mode),
            "spectral_abscissa": known(-10.0 + mode),
            "eigenvalues_ref": _array_ref(rid, "eigenvalues", [512], "complex128", ["rank"])}


def _points(dataset_id: str, q: float) -> SpectralPoints:
    return SpectralPoints.model_validate({
        "dataset_id": dataset_id, "collection_id": "mock.collection", "base_result_id": "mock.base",
        "configuration_id": dataset_id, "parameter_value": q,
        "points": [_point(dataset_id, q, mode) for mode in range(17)]})


def _eigenmode(dataset_id: str, mode: int, *, side: str = "RIGHT", rank: int = 0,
               representation: str = "COMPLEX_VECTOR", projection: str = "COMPLEX",
               field_component: str = "stored_vector") -> Eigenmode:
    q = DATASET_IDS[dataset_id]
    raw = representation == "COMPLEX_VECTOR"
    rid = (f"{dataset_id}.mode-{mode:02d}.{side.lower()}.rank-{rank:02d}."
           f"{representation.lower()}.{field_component}")
    context = _context(rid, dataset_id, q, experiment_id="spectrum", config_id=dataset_id,
                       semantic_id="eigenmode",
                       unit_quantity="stored eigenvector" if raw else "primitive amplitude")
    shape = [128, 4] if raw else [128]
    dtype = "complex128" if raw else "float64"
    axes = ["x", "conservative_component"] if raw else ["x"]
    return Eigenmode.model_validate({**context,
        "experiment_id": "spectrum", "eigenmode_id": rid, "configuration_id": dataset_id,
        "parameter_value": q, "spectrum_record_id": f"{dataset_id}.mode-{mode:02d}",
        "mode_index": mode, "side": side, "rank": rank, "field_component": field_component,
        "shape": shape,
        "normalization": {"id": "mock.normalization",
                          "definition": unresolved("Mock normalization has no bound convention"),
                          "phase_convention": unresolved("Mock phase has no bound convention"),
                          "component_order": known(["rho", "rho_u", "rho_v", "rho_E"] if raw else ["density", "u", "v", "pressure"]),
                          "processing_ref": _na("Mock read-only selection"), "evidence_refs": [EVIDENCE]},
        "localization_fraction": unresolved("No saved mock localization metric", "MISSING"),
        "localization_definition": "Test-only localization", "mask_reference": _mask(),
        "representation": representation, "projection": projection,
        "values_ref": _array_ref(rid, "eigenvector" if raw else "primitive_amplitude", shape, dtype, axes)})


def _validation(run_id: str) -> GrowthValidation:
    mode, q = RUN_IDS[run_id]
    dataset_id = f"mock.spectrum.q-{q}"
    history_id = f"{run_id}.history"
    context = _context(history_id, dataset_id, q, experiment_id="modal-validation", config_id=run_id,
                       semantic_id="modal_validation", unit_quantity="inverse model time", sampling="PER_STEP",
                       run=(mode, 1e-5))
    context["result"]["availability"] = "PARTIAL"
    time = [step / 100.0 for step in range(33)]
    cfd = [known(1e-5 + step / 100000.0) for step in range(33)]
    sigma_lin, sigma_rk3, sigma_cfd = -9.0, -9.125, -8.875
    absolute = abs(sigma_cfd - sigma_rk3)
    return GrowthValidation.model_validate({**context,
        "experiment_id": "modal-validation", "run_id": run_id, "mode_index": mode, "epsilon": 1e-5,
        "parameter_value": q, "configuration_id": run_id,
        "spectrum_record_id": f"{dataset_id}.mode-{mode:02d}",
        "eigenmode_id": f"{dataset_id}.mode-{mode:02d}.right.rank-00.complex_vector.stored_vector",
        "time": time, "step_indices": list(range(33)),
        "linear_amplitude": [unresolved("No saved linear amplitude history", "MISSING") for _ in range(33)],
        "cfd_amplitude": cfd,
        "growth_rate": {"linear": known(sigma_lin), "rk3": known(sigma_rk3), "cfd": known(sigma_cfd)},
        "error": {"absolute_discrepancy": known(absolute),
                  "relative_discrepancy": known(absolute / max(abs(sigma_rk3), 1.0)),
                  "definition_id": "mock.relative-discrepancy", "evidence_refs": [EVIDENCE]}})


class FakeSpectralAdapter:
    """Implements SpectralAdapterProtocol shape for the documented scenarios.

    ``mode`` selects:
      * ``valid``        -> datasets/curves/points/eigenmodes/validation all resolve
      * ``missing``      -> a recognized identity with an absent saved asset (MISSING slot)
      * ``missing_mode`` -> a registered dataset whose eigenmode vector is absent (MISSING_EIGENMODE)
      * ``unsupported``  -> a selector outside the verified set (UNSUPPORTED slot)
      * ``source``       -> the controlled frozen source read fails (ERROR slot)
    """

    def __init__(self, mode: str = "valid"):
        self.mode = mode

    # -- scenario helpers -------------------------------------------------------

    def _unregistered(self, identity, resource_type):
        if self.mode == "unsupported":
            raise unsupported_combination("Mock selector is outside the verified set",
                                          resource_type=resource_type, identity=unresolved("Unregistered mock selector"))
        return None

    def _fault(self, resource_type, identity):
        """Return a typed failure for the missing/source/unsupported scenarios, else None."""
        if self.mode == "missing":
            return self._slot_error(SpectrumDataset, "MISSING", missing_asset(
                "A recognized mock spectral asset is absent",
                resource_type=resource_type, identity=identity).body)
        if self.mode == "source":
            return self._slot_error(SpectrumDataset, "ERROR", source_error(
                "Frozen mock spectral source could not be read", resource_type=resource_type).body)
        if self.mode == "unsupported":
            return self._slot_error(SpectrumDataset, "UNSUPPORTED", unsupported_combination(
                "A registered mock identity cannot be rendered in the requested form",
                resource_type=resource_type, identity=identity).body)
        return None

    @staticmethod
    def _slot_error(model, availability, body):
        return ResourceSlot[model].model_validate({"availability": availability, "error": body})

    # -- protocol ---------------------------------------------------------------

    def list_spectral_datasets(self, *, registry_revision=None):
        return [_dataset(dataset_id, q) for dataset_id, q in DATASET_IDS.items()]

    def describe_spectrum(self, dataset_id, *, registry_revision=None):
        if dataset_id not in DATASET_IDS:
            self._unregistered(known(dataset_id), "spectrum")
            raise unsupported_combination("Select one of the four registered mock dataset identities",
                                          resource_type="spectrum", identity=unresolved("Unregistered mock dataset"))
        fault = self._fault("spectrum", known(dataset_id))
        if fault is not None:
            return ResourceSlot[SpectrumDataset].model_validate(
                {"availability": fault.root.availability, "error": fault.root.error})
        q = DATASET_IDS[dataset_id]
        return ResourceSlot[SpectrumDataset].model_validate(
            {"availability": "AVAILABLE", "value": _dataset(dataset_id, q)})

    def load_spectral_points(self, dataset_id, *, registry_revision=None):
        if dataset_id not in DATASET_IDS:
            self._unregistered(known(dataset_id), "spectrum")
            raise unsupported_combination("Select one of the four registered mock dataset identities",
                                          resource_type="spectrum", identity=unresolved("Unregistered mock dataset"))
        fault = self._fault("spectrum", known(dataset_id))
        if fault is not None:
            return ResourceSlot[SpectralPoints].model_validate(
                {"availability": fault.root.availability, "error": fault.root.error})
        q = DATASET_IDS[dataset_id]
        return ResourceSlot[SpectralPoints].model_validate(
            {"availability": "AVAILABLE", "value": _points(dataset_id, q)})

    def load_eigenmode(self, dataset_id, mode_index, *, side="RIGHT", rank=0,
                       representation="COMPLEX_VECTOR", projection="COMPLEX",
                       field_component="stored_vector", registry_revision=None):
        if self.mode == "missing_mode":
            return ResourceSlot[Eigenmode].model_validate({
                "availability": "MISSING",
                "error": missing_asset("The saved mock eigenmode vector is absent",
                                       resource_type="eigenmode", identity=known(dataset_id)).body})
        if dataset_id not in DATASET_IDS or type(mode_index) is not int or mode_index not in range(17):
            self._unregistered(known(dataset_id), "eigenmode")
            raise unsupported_combination("Only saved mock modes 0..16 are supported",
                                          resource_type="eigenmode", identity=unresolved("Unregistered mock mode"))
        fault = self._fault("eigenmode", known(dataset_id))
        if fault is not None:
            return ResourceSlot[Eigenmode].model_validate(
                {"availability": fault.root.availability, "error": fault.root.error})
        return ResourceSlot[Eigenmode].model_validate(
            {"availability": "AVAILABLE",
             "value": _eigenmode(dataset_id, mode_index, side=side, rank=rank,
                                 representation=representation, projection=projection,
                                 field_component=field_component)})

    def load_growth_validation(self, run_id, *, registry_revision=None):
        if run_id not in RUN_IDS:
            self._unregistered(known(run_id), "growth_validation")
            raise unsupported_combination("Select one of the registered mock validation runs",
                                          resource_type="growth_validation", identity=unresolved("Unregistered mock run"))
        if self.mode == "missing":
            return ResourceSlot[GrowthValidation].model_validate({
                "availability": "MISSING",
                "error": missing_asset("A recognized mock validation asset is absent",
                                       resource_type="growth_validation", identity=known(run_id)).body})
        if self.mode == "source":
            return ResourceSlot[GrowthValidation].model_validate({
                "availability": "ERROR",
                "error": source_error("Frozen mock validation source could not be read",
                                      resource_type="growth_validation").body})
        value = _validation(run_id)
        issue = missing_asset("No saved linear or RK3 amplitude histories in mock data",
                              resource_type="predicted_amplitude", identity=known(run_id)).body
        return ResourceSlot[GrowthValidation].model_validate(
            {"availability": "PARTIAL", "value": value, "issues": [issue]})
