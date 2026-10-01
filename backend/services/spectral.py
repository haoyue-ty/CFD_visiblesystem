"""Flask-independent SpectralService for the Phase 7B Window 2 Spectral Lab API.

Window 0/1 froze ``SpectralAdapterProtocol`` and its concrete read-only adapter. This
window adds ``SpectralServiceImpl``: a thin seam that adapts that protocol to the HTTP
layer and maps adapter failures onto the five typed spectral errors from frozen 06
§10/§11 — without touching the adapter, opening a file, interpolating ``q_at`` or
synthesizing a scientific value.

Adapter contract (unchanged): every selector method returns ``ResourceSlot[Model]``.
The slot is authoritative:

* ``AVAILABLE``  -> project the internal model into the public DTO
* ``PARTIAL``    -> project and carry the adapter's issue list
* ``MISSING``    -> 404, split by which identity is absent (spectrum vs eigenmode)
* ``UNSUPPORTED``-> 422 UNSUPPORTED_PARAMETER
* ``ERROR``      -> 500 SOURCE_ERROR (a controlled source could not be read faithfully)

Selection parameters (mode index, side, rank, representation, projection, epsilon) are
validated against the frozen enumerations *before* dispatch only to reject a clearly
out-of-range request with the contract code; the adapter remains the authority for
whether a specific saved vector exists, and its MISSING slot becomes MISSING_EIGENMODE.
"""
from typing import Protocol, runtime_checkable
from backend.services.spectral_resources import bind_evidence

from backend.adapters.spectral import SpectralAdapterProtocol
from backend.core.errors import (DomainError, missing_asset, missing_eigenmode,
                                 source_error, system_error, unknown_mode,
                                 unknown_spectrum, unsupported_parameter)
from backend.models.spectral import FOURIER_MODES
from backend.models.spectral_api import (EigenmodeView, GrowthValidationView,
                                         SpectrumCurveView, SpectrumDatasetView,
                                         SpectralPointView, ValidationRunListView,
                                         project_curve, project_dataset,
                                         project_eigenmode, project_point,
                                         project_validation, project_validation_runs)

# The four public views of a spectrum: the curve, one record, the dataset summary and modes.
VIEWS = ("dataset", "curve", "point", "eigenmode", "validation")

_FLIP_SIDES = ("LEFT", "RIGHT")
_REPRESENTATIONS = ("COMPLEX_VECTOR", "PRIMITIVE_PROFILE")
_PROJECTIONS = ("COMPLEX", "REAL", "IMAGINARY", "AMPLITUDE")


@runtime_checkable
class SpectralService(SpectralAdapterProtocol, Protocol):
    """Shared interface: the adapter protocol plus the public projection methods."""


class SpectralServiceImpl:
    """Concrete dispatch for the five SPEC operations.

    A missing adapter is a delivery gap (503 FEATURE_NOT_ENABLED), not a scientific
    failure: the capability is advertised only once a loader is wired in.
    """

    def __init__(self, adapter: SpectralAdapterProtocol | None):
        self.adapter = adapter
        self._registry_cache: dict[str | None, frozenset[str]] = {}

    # --- adapter dispatch ------------------------------------------------------

    def _require_adapter(self, method: str):
        if self.adapter is None:
            raise system_error("FEATURE_NOT_ENABLED", "Spectral adapter has not been delivered",
                               status=503, retryable=True)
        handler = getattr(self.adapter, method, None)
        if handler is None:
            raise system_error("FEATURE_NOT_ENABLED",
                               "Spectral adapter does not implement this capability",
                               status=503, retryable=True)
        return handler

    def _slot(self, method: str, *args, **kwargs):
        """Invoke the adapter and normalize a raised DomainError into a typed slot-like result."""
        handler = self._require_adapter(method)
        try:
            return handler(*args, **kwargs)
        except DomainError as error:
            raise self._translate(error) from None
        except NotImplementedError:
            raise unsupported_parameter(
                "Requested spectral representation is not implemented by this adapter",
                resource_type="spectrum", identity=None) from None
        except (FileNotFoundError, OSError):
            raise source_error("Recorded spectral source could not be read", retryable=False,
                               resource_type="spectrum", identity=None) from None
        except KeyError:
            raise unknown_spectrum("Requested spectral identity is not registered",
                                   identity=None) from None

    def _translate(self, error: DomainError) -> DomainError:
        """Map an adapter DomainError onto the five contract spectral codes.

        The adapter is frozen and may raise the older combination/asset codes; the service
        owns the wire vocabulary the contract documents for Spectrum. An
        ``UNSUPPORTED_COMBINATION`` against an *unresolved* identity means the selector was
        never registered (404); against a *known* identity it is a registered but
        unrenderable request (422).
        """
        code = error.body.code
        target = error.body.target
        identity = target.identity
        resource = target.resource_type
        unresolved_identity = getattr(identity.root, "state", "KNOWN") != "KNOWN"
        if code in {"MISSING_ASSET", "MISSING_SCIENTIFIC_ASSET"}:
            if resource in {"eigenmode", "eigenvector"}:
                return missing_eigenmode(error.body.message, identity=identity)
            return missing_asset(error.body.message, resource_type=resource, identity=identity)
        if code == "UNSUPPORTED_COMBINATION":
            if unresolved_identity:
                return unknown_spectrum(error.body.message, resource_type=resource, identity=identity)
            return unsupported_parameter(error.body.message, resource_type=resource, identity=identity)
        if code in {"SOURCE_READ_ERROR", "SOURCE_DATA_DRIFT", "SOURCE_CHANGED_DURING_READ",
                    "CANONICAL_SCHEMA_MISMATCH"}:
            return source_error(error.body.message, retryable=False,
                                resource_type=resource, identity=identity)
        if code == "REVISION_UNAVAILABLE":
            return system_error(code, error.body.message, status=409, resource_type=resource,
                                identity=identity)
        return error

    @staticmethod
    def _unwrap(slot, *, missing, resource_type, identity):
        """Turn a ResourceSlot into its value or raise the mapped typed failure.

        An UNSUPPORTED slot against an *unresolved* identity means the selector was never
        registered (404 UNKNOWN_SPECTRUM); against a *known* identity it is a registered but
        unrenderable request (422 UNSUPPORTED_PARAMETER). This mirrors `_translate` so a
        raised DomainError and a returned slot fail identically.
        """
        root = slot.root
        status = root.availability
        if status in ("AVAILABLE", "PARTIAL"):
            return root.value, (list(getattr(root, "issues", [])) if status == "PARTIAL" else [])
        if status == "MISSING":
            raise missing(root.error.message, resource_type=resource_type, identity=identity)
        if status == "UNSUPPORTED":
            if getattr(root.error.target.identity.root, "state", "KNOWN") != "KNOWN":
                raise unknown_spectrum(root.error.message, resource_type=resource_type, identity=identity)
            raise unsupported_parameter(root.error.message, resource_type=resource_type,
                                        identity=identity)
        raise source_error(root.error.message, retryable=False, resource_type=resource_type,
                           identity=identity)

    # --- selection validation (clear out-of-range requests) --------------------

    @staticmethod
    def _mode(mode_index) -> int:
        if type(mode_index) is not int or mode_index not in FOURIER_MODES:
            raise unknown_mode("Fourier mode index must be one of the 17 recorded blocks 0..16",
                               identity=None)
        return mode_index

    def _registered_dataset(self, dataset_id: str, registry_revision: str | None = None) -> str:
        """Resolve a dataset identity against the adapter's own declared registry.

        The frozen protocol exposes ``list_spectral_datasets`` as its only registry source;
        the concrete adapter's list is authoritative. This keeps the service's notion of
        "unknown spectrum" independent of any hard-coded module, and a MOCK adapter's ids
        resolve exactly like the production ones.
        """
        handler = self._require_adapter("list_spectral_datasets")
        if registry_revision not in self._registry_cache:
            try:
                datasets = handler(registry_revision=registry_revision)
            except DomainError as error:
                raise self._translate(error) from None
            self._registry_cache[registry_revision] = frozenset(d.dataset_id for d in datasets)
        if not isinstance(dataset_id, str) or dataset_id not in self._registry_cache[registry_revision]:
            raise unknown_spectrum("Select one of the registered spectral dataset identities",
                                   identity=None)
        return dataset_id

    # --- public operations -----------------------------------------------------

    def list_datasets(self, *, registry_revision: str | None = None) -> list[SpectrumDatasetView]:
        """SPEC01 uses a specific dataset identity; this lists the registered summaries."""
        handler = self._require_adapter("list_spectral_datasets")
        try:
            datasets = handler(registry_revision=registry_revision)
        except DomainError as error:
            raise self._translate(error) from None
        return [bind_evidence(project_dataset(dataset)) for dataset in datasets]

    def describe_dataset(self, dataset_id: str, *,
                         registry_revision: str | None = None) -> SpectrumDatasetView:
        self._registered_dataset(dataset_id, registry_revision)
        slot = self._slot("describe_spectrum", dataset_id, registry_revision=registry_revision)
        value, _ = self._unwrap(slot, missing=missing_asset, resource_type="spectrum",
                                identity=self._identity(dataset_id))
        return bind_evidence(project_dataset(value))

    def load_curve(self, dataset_id: str, *,
                   registry_revision: str | None = None) -> SpectrumCurveView:
        self._registered_dataset(dataset_id, registry_revision)
        slot = self._slot("load_spectral_points", dataset_id, registry_revision=registry_revision)
        value, _ = self._unwrap(slot, missing=missing_asset, resource_type="spectrum",
                                identity=self._identity(dataset_id))
        return bind_evidence(project_curve(value))

    def load_point(self, dataset_id: str, mode_index: int, *,
                   registry_revision: str | None = None) -> SpectralPointView:
        self._registered_dataset(dataset_id, registry_revision)
        mode = self._mode(mode_index)
        slot = self._slot("load_spectral_points", dataset_id, registry_revision=registry_revision)
        value, _ = self._unwrap(slot, missing=missing_asset, resource_type="spectrum",
                                identity=self._identity(dataset_id))
        selected = [point for point in value.points if point.mode_index == mode]
        if not selected:
            raise unknown_mode("Requested Fourier mode is not recorded for this dataset",
                               identity=self._identity(dataset_id))
        return bind_evidence(project_point(selected[0]))

    def load_eigenmode_view(self, dataset_id: str, mode_index: int, *, side: str = "RIGHT",
                            rank: int = 0, representation: str = "COMPLEX_VECTOR",
                            projection: str = "COMPLEX", field_component: str = "stored_vector",
                            registry_revision: str | None = None) -> EigenmodeView:
        self._registered_dataset(dataset_id, registry_revision)
        mode = self._mode(mode_index)
        self._selection(side=side, rank=rank, representation=representation,
                        projection=projection, field_component=field_component,
                        identity=self._identity(dataset_id))
        slot = self._slot("load_eigenmode", dataset_id, mode, side=side, rank=rank,
                          representation=representation, projection=projection,
                          field_component=field_component, registry_revision=registry_revision)
        value, _ = self._unwrap(slot, missing=missing_eigenmode, resource_type="eigenmode",
                                identity=self._identity(dataset_id))
        return bind_evidence(project_eigenmode(value))

    def load_validation_view(self, run_id: str, *,
                             registry_revision: str | None = None) -> GrowthValidationView:
        slot = self._slot("load_growth_validation", run_id, registry_revision=registry_revision)
        value, issues = self._unwrap(slot, missing=missing_asset, resource_type="growth_validation",
                                     identity=self._identity(run_id))
        return bind_evidence(project_validation(value, partial_issues=issues))

    def list_validation_runs(self, *, registry_revision: str | None = None) -> ValidationRunListView:
        """SPEC06: the registered validation-run identities.

        This reads ONLY the pinned registry metadata (identity + mode/q/epsilon),
        never a scientific source file: it exists so the frontend can build the run
        selector without constructing a ``modal-validation.*`` id itself. The
        registry is the frozen identity source; a revision mismatch is a 409.
        """
        from backend.registry import spectral_registry as registry
        if registry_revision is not None and registry_revision != registry.REGISTRY_REVISION:
            raise system_error("REVISION_UNAVAILABLE", "Spectral registry revision unavailable",
                              status=409, resource_type="growth_validation", identity=None)
        rows = [{
            "run_id": run_id, "mode_index": mode, "q_at": q_at, "epsilon": epsilon,
            "label": f"mode {mode} · q_at={q_at} · ε={epsilon:g}",
        } for run_id, (mode, q_at, epsilon, _history) in registry.RUNS.items()]
        return project_validation_runs(rows)

    # --- helpers ---------------------------------------------------------------

    def _selection(self, *, side, rank, representation, projection, field_component, identity):
        if side not in _FLIP_SIDES or representation not in _REPRESENTATIONS or projection not in _PROJECTIONS:
            raise unsupported_parameter(
                "Side, representation and projection must be explicit supported values",
                resource_type="eigenmode", identity=identity)
        if type(rank) is not int or rank not in range(32):
            raise unsupported_parameter("Only saved eigenpair ranks 0..31 are supported",
                                        resource_type="eigenmode", identity=identity)
        if representation == "COMPLEX_VECTOR" and field_component != "stored_vector":
            raise unsupported_parameter(
                "Raw composite vectors use stored_vector; a component order cannot be invented",
                resource_type="eigenmode", identity=identity)
        if representation == "PRIMITIVE_PROFILE" and (
                side != "RIGHT" or projection != "AMPLITUDE"
                or field_component not in ("density", "u", "v", "pressure")):
            raise unsupported_parameter(
                "Only a saved RIGHT primitive amplitude component profile is supported",
                resource_type="eigenmode", identity=identity)

    @staticmethod
    def _identity(value: str) -> dict:
        from backend.models.core import known
        return known(value)

    # --- capability helpers reused by EVI/capability projections ---------------

    def describe_capabilities(self, *, registry_revision: str | None = None):
        handler = getattr(self.adapter, "describe_capabilities", None)
        if handler is None:
            raise system_error("FEATURE_NOT_ENABLED",
                               "Spectral adapter has no capability observation",
                               status=503, retryable=True)
        return handler(registry_revision=registry_revision)
