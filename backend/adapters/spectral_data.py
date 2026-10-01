"""Read-only adapter for the frozen common Mach6 discrete-shock experiment.

Only registry identities select files/members. Immutable bytes are checked
against pinned hashes before decoding, then reobserved to reject mixed reads.
Saved mode and rank order is retained. No scientific code is executed, no
matrix/vector/curve reconstruction, normalization, interpolation or fitting.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
from zipfile import BadZipFile

import numpy as np

from backend.core.errors import DomainError, missing_asset, system_error, unsupported_combination
from backend.models.core import ResourceSlot, known, unresolved
from backend.models.results import ScientificArray
from backend.models.spectral import Eigenmode, GrowthValidation, SpectrumDataset, SpectralPoints
from backend.registry import spectral_registry as R


COMMON = (
    "SHA256_MANIFEST.json", "config.json", "method_identity.json", "validity_gates.json",
    "base_state/base_state.npz", "base_state/base_state_audit.json",
    "production_source/solver/fluxes/cross_mode_ec_unified_v1.py",
    "scripts/common.py", "scripts/spectrum_scan.py", "spectrum/shock_mask.json",
)
SPECTRUM = ("spectrum/spectral_summary.csv", "spectrum/eigenvalues.npz")
PRIMITIVE_COMPONENTS = ("density", "u", "v", "pressure")
LOCALIZATION = (
    "Saved RIGHT primitive-profile energy fraction in fixed shock cells 58..66; "
    "sum_x,sum_components |(drho/rho_pre,du/c_pre,dv/c_pre,dp/p_post)|^2; "
    "not conservative-vector energy and not a LEFT-vector metric"
)


class SpectralAdapter:
    """SpectralAdapterProtocol implementation; no API or registry activation."""

    def __init__(self, scientific_root: str | Path = R.SCIENTIFIC_ROOT):
        self._root = Path(scientific_root).resolve()

    @property
    def registry_revision(self):
        return R.REGISTRY_REVISION

    def _revision(self, revision):
        if revision is not None and revision != R.REGISTRY_REVISION:
            raise system_error("REVISION_UNAVAILABLE", "Spectral registry revision unavailable", status=409)

    @staticmethod
    def _dataset(dataset_id):
        if not isinstance(dataset_id, str) or dataset_id not in R.DATASETS:
            raise unsupported_combination("Select one of the four registered spectral dataset identities",
                                          resource_type="spectrum", identity=unresolved("Unregistered selector"))
        return R.DATASETS[dataset_id]

    def _selection(self, dataset_id, mode, side, rank, representation, projection, component):
        self._dataset(dataset_id)
        if (type(mode) is not int or mode not in range(17) or type(rank) is not int or rank not in range(32)
                or side not in ("LEFT", "RIGHT") or representation not in ("COMPLEX_VECTOR", "PRIMITIVE_PROFILE")
                or projection not in ("COMPLEX", "REAL", "IMAGINARY", "AMPLITUDE")):
            raise unsupported_combination("Only saved modes 0..16, ranks 0..31 and explicit representations are supported",
                                          resource_type="eigenmode", identity=known(dataset_id))
        if ((representation == "COMPLEX_VECTOR" and component != "stored_vector") or
                (representation == "PRIMITIVE_PROFILE" and
                 (side != "RIGHT" or projection != "AMPLITUDE" or component not in PRIMITIVE_COMPONENTS))):
            raise unsupported_combination("Raw stored_vector or saved RIGHT primitive amplitude component required",
                                          resource_type="eigenmode", identity=known(dataset_id))

    @staticmethod
    def _call(model, operation):
        try:
            return ResourceSlot[model].model_validate({"availability": "AVAILABLE", "value": operation()})
        except DomainError as error:
            return ResourceSlot[model].model_validate({"availability": error.availability, "error": error.body})
        except (ValueError, KeyError, TypeError, IndexError, EOFError, BadZipFile):
            error = system_error("CANONICAL_SCHEMA_MISMATCH", "Frozen spectral source schema or identity is inconsistent",
                                 domain="SCIENTIFIC")
            return ResourceSlot[model].model_validate({"availability": "ERROR", "error": error.body})

    @staticmethod
    def _changed():
        return system_error("SOURCE_CHANGED_DURING_READ", "Spectral dependencies changed during observation",
                            status=409, domain="SCIENTIFIC")

    def _read_bytes(self, name):
        # name is selected exclusively from R.ASSETS; never from caller paths.
        path = (self._root / R.FREEZE_DIR / name).resolve()
        if not path.is_relative_to(self._root):
            raise system_error("SOURCE_PATH_ESCAPE", "Registered dependency escapes the scientific root")
        try:
            before = path.stat()
            raw = path.read_bytes()
            after = path.stat()
        except FileNotFoundError:
            raise missing_asset("A registered frozen spectral asset is absent", resource_type="asset",
                                identity=known(R.ASSETS[name][0]), evidence_refs=[R.ASSETS[name][0]]) from None
        except OSError:
            raise system_error("SOURCE_READ_ERROR", "Frozen spectral dependency could not be read") from None
        stamp = lambda s: (s.st_size, s.st_mtime_ns, s.st_ino)
        if stamp(before) != stamp(after):
            raise self._changed()
        return raw, stamp(after)

    def _bundle(self, names, *, optional=()):
        blobs, stamps = {}, {}
        for name in dict.fromkeys((*COMMON, *names, *optional)):
            try:
                raw, stamp = self._read_bytes(name)
            except DomainError as error:
                if name in optional and error.availability == "MISSING":
                    continue
                raise
            if hashlib.sha256(raw).hexdigest() != R.ASSETS[name][1]:
                raise system_error("SOURCE_DATA_DRIFT", "Dependency SHA256 differs from the pinned registry baseline",
                                   status=409, domain="SCIENTIFIC", resource_type="asset",
                                   identity=known(R.ASSETS[name][0]), evidence_refs=[R.ASSETS[name][0]])
            blobs[name], stamps[name] = raw, stamp
        for name, raw in blobs.items():
            try:
                current, stamp = self._read_bytes(name)
            except DomainError:
                raise self._changed() from None
            if current != raw or stamp != stamps[name]:
                raise self._changed()
        entries = {item["path"]: item["sha256"] for item in json.loads(blobs["SHA256_MANIFEST.json"])["artifacts"]}
        for name in blobs:
            if name != "SHA256_MANIFEST.json" and entries[name] != R.ASSETS[name][1]:
                raise ValueError("Manifest baseline mismatch")
        config = json.loads(blobs["config.json"])
        identity = json.loads(blobs["method_identity.json"])
        gates = json.loads(blobs["validity_gates.json"])["checks"]
        audit = json.loads(blobs["base_state/base_state_audit.json"])
        if (config["method_id"] != R.METHOD_NAME or config["method_sha256"] != R.METHOD_HASH
                or config["physics"]["mach"] != 6.0 or config["q_at"] != list(R.DATASETS.values())
                or config["modes"] != list(range(17)) or (config["mesh"]["nx"], config["mesh"]["ny"]) != (128, 32)
                or identity["expected_sha256"] != R.METHOD_HASH or identity["actual_sha256"] != R.METHOD_HASH
                or identity["method_hash"] != "MATCH" or not gates or any(v != "PASS" for v in gates.values())
                or not audit["converged"] or not audit["shared_B_D"]):
            raise ValueError("Common Mach6 identity or upstream gates mismatch")
        base = self._npz(blobs["base_state/base_state.npz"])
        for member, shape in (("Ubar", (128, 4)), ("Ubar_2d", (32, 128, 4)), ("x", (128,)), ("y", (32,))):
            self._array_schema(base[member], shape, "float64")
        if not np.array_equal(base["Ubar_2d"], np.broadcast_to(base["Ubar"], (32, 128, 4))):
            raise ValueError("Base state is not the saved common discrete shock")
        mask = json.loads(blobs["spectrum/shock_mask.json"])
        if mask["indices"] != list(range(58, 67)):
            raise ValueError("Frozen shock mask mismatch")
        return blobs, config, datetime.now(timezone.utc)

    @staticmethod
    def _npz(raw):
        with np.load(BytesIO(raw), allow_pickle=False) as data:
            return {key: data[key] for key in data.files}

    @staticmethod
    def _array_schema(values, shape, dtype):
        if values.shape != shape or str(values.dtype) != dtype or not np.isfinite(values).all():
            raise ValueError("Invalid frozen array schema")

    def _axes(self, data):
        self._array_schema(data["q_at"], (4,), "float64")
        self._array_schema(data["m"], (17,), "int64")
        if data["q_at"].tolist() != list(R.DATASETS.values()) or data["m"].tolist() != list(range(17)):
            raise ValueError("Saved q/m identity or order mismatch; never reorder")

    @staticmethod
    def _csv(raw):
        return list(csv.DictReader(StringIO(raw.decode("utf-8-sig"))))

    def _spectrum(self, blobs):
        data = self._npz(blobs["spectrum/eigenvalues.npz"])
        self._axes(data)
        values = data["eigenvalues"]
        self._array_schema(values, (4, 17, 512), "complex128")
        rows = self._csv(blobs["spectrum/spectral_summary.csv"])
        # Source CSV is mode-major, then q-major. Filtering retains its order.
        identities = [(int(row["m"]), float(row["q_at"])) for row in rows]
        if identities != [(m, q) for m in range(17) for q in R.DATASETS.values()]:
            raise ValueError("Summary count, identity or recorded order mismatch")
        for row in rows:
            m, q = int(row["m"]), float(row["q_at"])
            block = values[list(R.DATASETS.values()).index(q), m]
            if (float(row["alpha"]) != float(block.real.max()) or float(row["alpha"]) != float(block[0].real)
                    or float(row["leading_imag"]) != float(block[0].imag)):
                raise ValueError("Saved summary differs from complex eigenvalue block")
        return rows, values

    @staticmethod
    def _unit(quantity="inverse model time"):
        return {"id": {"inverse model time": "spectral.inverse-model-time", "stored eigenvector": "spectral.stored-eigenvector",
                       "primitive amplitude": "spectral.primitive-amplitude"}[quantity],
                "system": "MODEL" if quantity == "inverse model time" else "UNKNOWN", "quantity": quantity, "label": quantity,
                "si_mapping": unresolved("No established SI mapping")}

    @staticmethod
    def _verification(blobs, observed):
        return {"status": "FROZEN_VERIFIED", "basis": [
            "Upstream common Mach6 freeze and validity gates retained",
            "Selected dependency SHA256 matched pinned Phase1 inventory and frozen manifest",
            "Immutable byte mapping with dependency reobservation; no new CFD certification"],
            "verified_at": unresolved("Upstream verification timestamp not recorded"),
            "observation_at": known(observed), "evidence_refs": [R.ASSETS[n][0] for n in blobs]}

    def _context(self, result_id, dataset_id, blobs, config, observed, *, run=None, interval=None):
        q = R.DATASETS[dataset_id]
        experiment, cid = ("spectrum", dataset_id) if run is None else ("modal-validation", run)
        verification = self._verification(blobs, observed)
        na = unresolved("Static frozen Fourier result" if run is None else "History has 33 recorded endpoints; no single endpoint selected",
                        "NOT_APPLICABLE")
        scope = {"id": "spectrum.common-base.x", "description": "Common Mach6 zero-residual discrete shock; selective modal response",
                 "boundary_scope": known("x_lower fixed pre-shock inflow; x_upper outflow; y periodic"),
                 "spatial_domain_ref": known("spectrum.common-base.x"), "mask_refs": [R.MASK_ID],
                 "definition_refs": ["spectral_abscissa" if run is None else "modal_validation"]}
        provenance = {"evidence_refs": verification["evidence_refs"], "source_asset_ids": verification["evidence_refs"],
                      "registry_revision": R.REGISTRY_REVISION, "data_revision": R.DATA_REVISION,
                      "release_id": unresolved("No release bundle", "NOT_APPLICABLE"), "source_drift": known(False)}
        time = {"sampling": "STATIC" if run is None else "PER_STEP", "accumulation": "NONE",
                "physical_time": na, "interval": na if interval is None else known(interval),
                "step_index": na, "stage_index": na, "snapshot_index": na,
                "index_convention": "Saved Fourier mode identity 0..16" if run is None else "Recorded accepted steps 0..32"}
        result = {"schema_version": "1.0.0", "result_id": result_id, "experiment_id": experiment,
                  "config_id": cid, "semantic_id": "spectral_abscissa" if run is None else "modal_validation",
                  "data_origin": "FROZEN_PRODUCTION", "availability": "AVAILABLE", "time": time, "scope": scope,
                  "unit": self._unit(), "verification": verification, "provenance": provenance, "limitations": []}
        dim = {"id": "dimensionless", "system": "DIMENSIONLESS", "quantity": "coefficient", "label": "dimensionless",
               "si_mapping": unresolved("Dimensionless", "NOT_APPLICABLE")}
        params = [{"name": "q_at", "value": known(q), "unit": dim},
                  {"name": "q_aa", "value": known(config["q_aa"]), "unit": dim}]
        if run is not None:
            m, _, eps, _ = R.RUNS[run]
            params += [{"name": "mode", "value": known(float(m)), "unit": dim},
                       {"name": "epsilon", "value": known(eps), "unit": dim}]
        configuration = {"id": cid, "experiment_id": experiment, "name": "Frozen common Mach6 discrete shock",
                         "parameters": params, "verification": verification, "limitations": [],
                         "evidence_refs": verification["evidence_refs"],
                         "protocol": {"method_name": known(R.METHOD_NAME), "method_hash": known(R.METHOD_HASH),
                                      "grid": known({"coordinate_system": "CARTESIAN",
                                                     "dimensions": [{"axis": "x", "size": 128}, {"axis": "y", "size": 32}],
                                                     "extent": [{"axis": "x", "lower": config["mesh"]["xlim"][0], "upper": config["mesh"]["xlim"][1]},
                                                                {"axis": "y", "lower": config["mesh"]["ylim"][0], "upper": config["mesh"]["ylim"][1]}]}),
                                      "integrator": known(config["numerics"]["integrator"]),
                                      "reconstruction": known(config["numerics"]["reconstruction"]),
                                      "final_time": na if interval is None else known(interval["end"]),
                                      "boundary_scope": scope["boundary_scope"],
                                      "protocol_asset_refs": [R.ASSETS["config.json"][0], R.ASSETS["method_identity.json"][0]]}}
        assets = []
        for name in blobs:
            aid, sha, role, fmt, status = R.ASSETS[name]
            asset_verification = verification if status == "FROZEN_VERIFIED" else {
                **verification, "status": status, "basis": ["Inventory hash observed; manifest self-hash excluded upstream"]}
            assets.append({"asset_id": aid, "source_id": "passage6.linear-perturbation.freeze", "source_display": name,
                           "relative_origin": known(f"{R.FREEZE_DIR}/{name}"), "role": role, "format": fmt,
                           "recorded_data_hash": known(sha), "current_data_hash": known(hashlib.sha256(blobs[name]).hexdigest()),
                           "data_drift": known(False), "verification": asset_verification,
                           "canonical_selected": True, "limitations": []})
        return {"result": result, "experiment_id": experiment, "configuration_id": cid, "parameter_value": q,
                "verification": verification, "provenance": provenance,
                "evidence": {"configuration": configuration, "source_assets": assets}}

    def _mask(self, context, blobs):
        return {"id": R.MASK_ID, "type": "SPECTRUM_FIXED_SHOCK_CELLS", "domain_refs": ["spectrum.common-base.x"],
                "definition": json.loads(blobs["spectrum/shock_mask.json"])["rule"], "parameters": [],
                "index_sets": [{"axis": "x", "indices": list(range(58, 67)), "index_base": 0}], "mask_array_refs": [],
                "scope": context["result"]["scope"], "verification": context["verification"],
                "evidence_refs": [R.ASSETS["spectrum/shock_mask.json"][0]]}

    @staticmethod
    def _ref(result_id, array_id, shape, axes, dtype="complex128"):
        return {"result_id": result_id, "descriptor": {"array_id": array_id, "dtype": dtype, "shape": shape,
                "axes": axes, "order": "C", "encoding": "FLAT_JSON", "element_count": int(np.prod(shape))}}

    def list_spectral_datasets(self, *, registry_revision=None) -> list[SpectrumDataset]:
        self._revision(registry_revision)
        # List's frozen protocol has no failed-slot variant; propagate failures.
        return [self._describe(dataset_id) for dataset_id in R.DATASETS]

    def _describe(self, dataset_id):
        self._dataset(dataset_id)
        blobs, config, observed = self._bundle(SPECTRUM)
        rows, _ = self._spectrum(blobs)
        context = self._context(dataset_id, dataset_id, blobs, config, observed)
        return SpectrumDataset.model_validate({**context, "dataset_id": dataset_id,
            "collection_id": R.COLLECTION_ID, "base_result_id": R.BASE_RESULT_ID,
            "matrix_source": unresolved("No serialized Fourier matrices were frozen", "MISSING"),
            "wave_number_range": {"mode_indices": list(range(17)),
                                  "wave_numbers": known([float(row["kappa"]) for row in rows if float(row["q_at"]) == R.DATASETS[dataset_id]]),
                                  "definition": "Saved kappa column; 2*pi*m/(y_upper-y_lower), scripts/spectrum_scan.py",
                                  "evidence_refs": [R.ASSETS["spectrum/spectral_summary.csv"][0], R.ASSETS["scripts/spectrum_scan.py"][0]]},
            "mask": self._mask(context, blobs)})

    def describe_spectrum(self, dataset_id, *, registry_revision=None) -> ResourceSlot[SpectrumDataset]:
        def read():
            self._revision(registry_revision)
            return self._describe(dataset_id)
        return self._call(SpectrumDataset, read)

    def load_spectral_points(self, dataset_id, *, registry_revision=None) -> ResourceSlot[SpectralPoints]:
        def read():
            self._revision(registry_revision)
            q = self._dataset(dataset_id)
            blobs, config, observed = self._bundle(SPECTRUM)
            rows, _ = self._spectrum(blobs)
            points = []
            for row in rows:
                if float(row["q_at"]) != q:
                    continue
                mode = int(row["m"])
                rid = R.record_id(dataset_id, mode)
                points.append({**self._context(rid, dataset_id, blobs, config, observed),
                    "dataset_id": dataset_id, "collection_id": R.COLLECTION_ID, "base_result_id": R.BASE_RESULT_ID,
                    "spectrum_record_id": rid, "mode_index": mode, "wave_number": known(float(row["kappa"])),
                    "real_lambda": known(float(row["alpha"])), "imag_lambda": known(float(row["leading_imag"])),
                    "spectral_abscissa": known(float(row["alpha"])),
                    "eigenvalues_ref": self._ref(rid, "eigenvalues", [512], ["rank"])})
            return {"dataset_id": dataset_id, "collection_id": R.COLLECTION_ID, "base_result_id": R.BASE_RESULT_ID,
                    "configuration_id": dataset_id, "parameter_value": q, "points": points}
        return self._call(SpectralPoints, read)

    def _eigenmode(self, dataset_id, mode, side, rank, representation, projection, component):
        self._selection(dataset_id, mode, side, rank, representation, projection, component)
        raw_vector = representation == "COMPLEX_VECTOR"
        name = f"spectrum/{side.lower()}_eigenvectors.npz" if raw_vector else "spectrum/leading_primitive_amplitude_profiles.npz"
        metrics_name = "spectrum/eigenvector_metrics.csv"
        blobs, config, observed = self._bundle((name,), optional=(metrics_name,) if side == "RIGHT" else ())
        data = self._npz(blobs[name])
        self._axes(data)
        qi = list(R.DATASETS.values()).index(R.DATASETS[dataset_id])
        if raw_vector:
            self._array_schema(data["ranks"], (32,), "int64")
            if data["ranks"].tolist() != list(range(32)):
                raise ValueError("Saved rank identity mismatch")
            self._array_schema(data["vectors"], (4, 17, 512, 32), "complex128")
            values = data["vectors"][qi, mode, :, rank].reshape(128, 4, order="C")
            shape, axes, dtype = [128, 4], ["x", "conservative_component"], "complex128"
        else:
            self._array_schema(data["amplitude"], (4, 17, 32, 128, 4), "float64")
            if (data["amplitude"] < 0).any():
                raise ValueError("Saved primitive amplitudes cannot be negative")
            values = data["amplitude"][qi, mode, rank, :, PRIMITIVE_COMPONENTS.index(component)]
            shape, axes, dtype = [128], ["x"], "float64"
        rid = R.eigenmode_id(dataset_id, mode, side, rank, representation, component)
        context = self._context(rid, dataset_id, blobs, config, observed)
        context["result"]["semantic_id"] = "eigenmode"
        context["result"]["unit"] = self._unit("stored eigenvector" if raw_vector else "primitive amplitude")
        localization = unresolved("No saved LEFT localization metric; RIGHT metric cannot be relabeled", "MISSING")
        if side == "RIGHT":
            localization = unresolved("Saved RIGHT localization metric is absent; no recomputation", "MISSING")
            if metrics_name in blobs:
                rows = self._csv(blobs[metrics_name])
                identities = [(int(r["m"]), float(r["q_at"]), int(r["rank"])) for r in rows]
                if identities != [(m, q, r) for m in range(17) for q in R.DATASETS.values() for r in range(32)]:
                    raise ValueError("Saved localization identity/order mismatch")
                metric = rows[identities.index((mode, R.DATASETS[dataset_id], rank))]
                localization = known(float(metric["shock_localization_fraction"]))
        model = Eigenmode.model_validate({**context, "eigenmode_id": rid, "spectrum_record_id": R.record_id(dataset_id, mode),
            "mode_index": mode, "side": side, "rank": rank, "field_component": component, "shape": shape,
            "normalization": {"id": "spectrum.saved-eigenvector-normalization",
                              "definition": unresolved("Raw eigensolver normalization has no bound explicit convention"),
                              "phase_convention": unresolved("Raw eigenvector phase has no bound convention; kept verbatim"),
                              "component_order": known(["rho", "rho_u", "rho_v", "rho_E"] if raw_vector else list(PRIMITIVE_COMPONENTS)),
                              "processing_ref": unresolved("Read-only saved array selection and C-order reshape", "NOT_APPLICABLE"),
                              "evidence_refs": [R.ASSETS["scripts/spectrum_scan.py"][0]]},
            "localization_fraction": localization,
            "localization_definition": LOCALIZATION, "mask_reference": self._mask(context, blobs),
            "representation": representation, "projection": projection,
            "values_ref": self._ref(rid, "eigenvector" if raw_vector else "primitive_amplitude", shape, axes, dtype)})
        return model, values

    def load_eigenmode(self, dataset_id, mode_index, *, side="RIGHT", rank=0,
                       representation="COMPLEX_VECTOR", projection="COMPLEX", field_component="stored_vector",
                       registry_revision=None) -> ResourceSlot[Eigenmode]:
        def read():
            self._revision(registry_revision)
            return self._eigenmode(dataset_id, mode_index, side, rank, representation, projection, field_component)[0]
        return self._call(Eigenmode, read)

    def load_array(self, result_id, array_id, *, registry_revision=None) -> ResourceSlot[ScientificArray]:
        """Resolve only exact registered result/array references; no NPZ keys."""
        def read():
            self._revision(registry_revision)
            if array_id == "eigenvalues":
                for dataset in R.DATASETS:
                    for mode in range(17):
                        if result_id == R.record_id(dataset, mode):
                            blobs, config, observed = self._bundle(SPECTRUM)
                            _, values = self._spectrum(blobs)
                            header = self._context(result_id, dataset, blobs, config, observed)["result"]
                            ref = self._ref(result_id, array_id, [512], ["rank"])
                            block = values[list(R.DATASETS.values()).index(R.DATASETS[dataset]), mode]
                            return self._scientific_array(header, ref, block)
            elif array_id in ("eigenvector", "primitive_amplitude"):
                representation = "COMPLEX_VECTOR" if array_id == "eigenvector" else "PRIMITIVE_PROFILE"
                components = ("stored_vector",) if representation == "COMPLEX_VECTOR" else PRIMITIVE_COMPONENTS
                for dataset in R.DATASETS:
                    for mode in range(17):
                        for side in (("RIGHT", "LEFT") if representation == "COMPLEX_VECTOR" else ("RIGHT",)):
                            for rank in range(32):
                                for component in components:
                                    if result_id == R.eigenmode_id(dataset, mode, side, rank, representation, component):
                                        model, values = self._eigenmode(dataset, mode, side, rank, representation,
                                                                        "COMPLEX" if representation == "COMPLEX_VECTOR" else "AMPLITUDE", component)
                                        return self._scientific_array(model.result, model.values_ref, values)
            raise unsupported_combination("Array/result combination is not registered", resource_type="array",
                                          identity=unresolved("Unregistered array selector"))
        return self._call(ScientificArray, read)

    @staticmethod
    def _scientific_array(header, ref, values):
        descriptor = ref["descriptor"] if isinstance(ref, dict) else ref.descriptor
        flat = values.ravel(order="C")
        elements = [{"real": float(v.real), "imag": float(v.imag)} for v in flat] if np.iscomplexobj(flat) else flat.tolist()
        return {"result": header, "descriptor": descriptor, "values": elements}

    def load_growth_validation(self, run_id, *, registry_revision=None) -> ResourceSlot[GrowthValidation]:
        def read():
            self._revision(registry_revision)
            if not isinstance(run_id, str) or run_id not in R.RUNS:
                raise unsupported_combination("Select one of the 24 registered validation runs",
                                              resource_type="growth_validation", identity=unresolved("Unregistered run selector"))
            mode, q, eps, history_name = R.RUNS[run_id]
            blobs, config, observed = self._bundle(("cfd_validation/validation_summary.csv", history_name,
                "cfd_validation/mode_selection.json", "scripts/cfd_validation.py", "spectrum/eigenvalues.npz"))
            rows = self._csv(blobs["cfd_validation/validation_summary.csv"])
            identities = [(int(row["m"]), float(row["q_at"]), float(row["epsilon"])) for row in rows]
            if identities != [v[:3] for v in R.RUNS.values()]:
                raise ValueError("Recorded 24-run identity/order mismatch")
            row = rows[identities.index((mode, q, eps))]
            if row["history_path"] != history_name.removeprefix("cfd_validation/"):
                raise ValueError("Summary history binding mismatch")
            rank = int(row["rank"])
            choices = json.loads(blobs["cfd_validation/mode_selection.json"])["choices"]
            choice = [c for c in choices if (c["m"], c["q_at"]) == (mode, q)]
            if len(choice) != 1 or choice[0]["rank"] != rank or choice[0]["branch_id"] != int(row["branch_id"]):
                raise ValueError("Saved validation branch identity mismatch")
            eigenvalues = self._npz(blobs["spectrum/eigenvalues.npz"])
            self._axes(eigenvalues)
            self._array_schema(eigenvalues["eigenvalues"], (4, 17, 512), "complex128")
            if rank not in range(32):
                raise ValueError("Unsaved validation rank")
            lam = eigenvalues["eigenvalues"][list(R.DATASETS.values()).index(q), mode, rank]
            if (float(row["lambda_real"]) != float(lam.real) or float(row["lambda_imag"]) != float(lam.imag)
                    or float(row["sigma_LIN"]) != float(lam.real)):
                raise ValueError("Validation lambda differs from saved branch")
            history = self._csv(blobs[history_name])
            time = [float(h["physical_time"]) for h in history]
            steps = [int(h["accepted_step"]) for h in history]
            amplitudes = [known(float(h["modal_amplitude"])) for h in history]
            dataset = R.dataset_id(q)
            context = self._context(f"{run_id}.history", dataset, blobs, config, observed, run=run_id,
                                    interval={"start": time[0], "end": time[-1]})
            context["result"]["availability"] = "PARTIAL"
            return {**context, "run_id": run_id, "mode_index": mode, "epsilon": eps,
                    "spectrum_record_id": R.record_id(dataset, mode),
                    "eigenmode_id": R.eigenmode_id(dataset, mode, "RIGHT", rank), "time": time, "step_indices": steps,
                    "linear_amplitude": [unresolved("No saved linear amplitude history; no exponential synthesis", "MISSING") for _ in history],
                    "cfd_amplitude": amplitudes, "growth_rate": {"linear": known(float(row["sigma_LIN"])),
                        "rk3": known(float(row["sigma_RK3"])), "cfd": known(float(row["sigma_CFD"]))},
                    "fit_start": int(row["fit_start_step"]), "fit_end": int(row["fit_end_step"]), "fit_point_count": int(row["fit_points"]),
                    "error": {"absolute_discrepancy": known(float(row["absolute_discrepancy_CFD_RK3"])),
                              "relative_discrepancy": known(float(row["relative_discrepancy_CFD_RK3"])),
                              "definition_id": "fig13.relative-discrepancy-CFD-RK3",
                              "evidence_refs": [R.ASSETS["cfd_validation/validation_summary.csv"][0], R.ASSETS["scripts/cfd_validation.py"][0]]}}
        slot = self._call(GrowthValidation, read)
        if slot.root.availability != "AVAILABLE":
            return slot
        issue = missing_asset("No saved linear or RK3 amplitude histories; stored rates and CFD history are available",
                              resource_type="predicted_amplitude", identity=known(run_id)).body
        return ResourceSlot[GrowthValidation].model_validate({"availability": "PARTIAL", "value": slot.root.value, "issues": [issue]})

    def describe_capabilities(self, *, registry_revision=None):
        """Internal capability observations. Missing optional assets disable their capability only."""
        self._revision(registry_revision)
        def support(slot):
            status = slot.root.availability
            return {"status": {"AVAILABLE": "SUPPORTED", "PARTIAL": "PARTIAL", "UNSUPPORTED": "UNSUPPORTED"}.get(status, "MISSING"),
                    "availability": status,
                    "reason": ("Saved linear/RK3/CFD rates and CFD history verified; linear/RK3 histories absent" if status == "PARTIAL"
                               else "Frozen asset loaded and hash verified" if status == "AVAILABLE" else slot.root.error.message)}
        dataset = next(iter(R.DATASETS))
        return {"registry_revision": R.REGISTRY_REVISION,
                "spectrum": {d: support(self.describe_spectrum(d)) for d in R.DATASETS},
                "eigenmode": {side: support(self.load_eigenmode(dataset, 0, side=side)) for side in ("RIGHT", "LEFT")},
                "growth_validation": {run: support(self.load_growth_validation(run)) for run in R.RUNS},
                "linear_amplitude": {"status": "MISSING", "availability": "MISSING", "reason": "No saved linear amplitude histories"},
                "rk3_amplitude": {"status": "MISSING", "availability": "MISSING", "reason": "No saved RK3 amplitude histories"}}
