"""SPEC01-SPEC05: Spectral Lab dataset, curve, record, eigenmode and validation reads.

Blueprint -> SpectralService -> SpectralAdapterProtocol -> controlled registry -> READ_ONLY
frozen source. Nothing here opens a source, reconstructs a matrix, fits a growth curve or
interpolates ``q_at``. Every response carries ``representation``, the Fourier ``mode_index``
where applicable, ``q_at``, ``verification`` and ``provenance`` so the frontend never guesses
what it is looking at.

The operation set is deliberately query-selector only: q is one of four exact registered
configurations (never a continuous range), mode index is ell 0..16, and eigenmode rank is one
of the 32 saved ranks. ARRAY01 remains the only way to fetch the 512-value blocks or the
128x4 / 128 vectors, so this layer never ships a value payload.
"""
from flask import g

from backend.api.catalog import Operation, OperationCatalog
from backend.api.case8 import make_parser
from backend.core.errors import system_error
from backend.models import ApiEnvelope, ProjectInfo, known
from backend.models.spectral_api import (EigenmodeView, GrowthValidationView,
                                         SpectrumCurveView, SpectrumDatasetView,
                                         SpectralPointView, ValidationRunListView)
from backend.schemas.requests import (EigenmodeQuery, RegistryQuery, SpectrumModeQuery,
                                      SpectrumQuery, ValidationQuery)

SPECTRA_BASE = "/api/v1/spectra"


def _envelope(payload, project: ProjectInfo, response_model, *, availability: str = "AVAILABLE",
              issues=None):
    return response_model.model_validate({
        "schema_version": "1.0.0", "request_id": g.request_id,
        "registry_revision": known(project.registry_revision),
        "data_revision": known(project.data_revision),
        "availability": availability, "data": payload, "issues": issues or [],
    })


def _revision(query: RegistryQuery, project: ProjectInfo) -> None:
    if query.registry_revision is not None and query.registry_revision != project.registry_revision:
        raise system_error("REVISION_UNAVAILABLE", "Requested registry revision is unavailable", status=409)


def register_spectral_operations(catalog: OperationCatalog, project: ProjectInfo, service) -> None:
    def list_datasets(query: RegistryQuery):
        _revision(query, project)
        return _envelope(service.list_datasets(), project, ApiEnvelope[list[SpectrumDatasetView]])

    def dataset(query: SpectrumQuery, dataset_id: str):
        _revision(query, project)
        return _envelope(service.describe_dataset(dataset_id), project,
                         ApiEnvelope[SpectrumDatasetView])

    def points(query: SpectrumQuery, dataset_id: str):
        _revision(query, project)
        return _envelope(service.load_curve(dataset_id), project, ApiEnvelope[SpectrumCurveView])

    def point(query: SpectrumModeQuery, dataset_id: str, mode_index: str):
        _revision(query, project)
        return _envelope(service.load_point(dataset_id, query.mode_index), project,
                         ApiEnvelope[SpectralPointView])

    def eigenmodes(query: EigenmodeQuery, dataset_id: str, mode_index: str):
        _revision(query, project)
        return _envelope(service.load_eigenmode_view(
            dataset_id, query.mode_index, side=query.side, rank=query.rank,
            representation=query.representation, projection=query.projection,
            field_component=query.field_component), project, ApiEnvelope[EigenmodeView])

    def validation(query: ValidationQuery, run_id: str):
        _revision(query, project)
        view = service.load_validation_view(run_id)
        availability = "PARTIAL" if view.issues else "AVAILABLE"
        return _envelope(view, project, ApiEnvelope[GrowthValidationView],
                         availability=availability, issues=view.issues)

    def validation_runs(query: RegistryQuery):
        # The run selector identities come from the pinned registry metadata, so the
        # frontend can offer the 24 recorded runs without inventing an id.
        _revision(query, project)
        return _envelope(service.list_validation_runs(), project,
                         ApiEnvelope[ValidationRunListView])

    common_errors = {
        400: ("INVALID_REQUEST",), 405: ("METHOD_NOT_ALLOWED",),
        404: ("UNKNOWN_SPECTRUM", "UNKNOWN_MODE", "MISSING_EIGENMODE", "MISSING_ASSET"),
        409: ("REVISION_UNAVAILABLE",),
        422: ("UNSUPPORTED_PARAMETER",),
        500: ("SOURCE_ERROR", "CANONICAL_SCHEMA_MISMATCH", "INTERNAL_ERROR"),
        503: ("FEATURE_NOT_ENABLED",),
    }

    registry_parser = make_parser(RegistryQuery)
    spectrum_parser = make_parser(SpectrumQuery)
    mode_parser = make_parser(SpectrumModeQuery, integers=("mode_index",))
    eigenmode_parser = make_parser(EigenmodeQuery, integers=("mode_index", "rank"),
                                   optional=("side", "representation", "projection", "field_component"))
    validation_parser = make_parser(ValidationQuery)

    catalog.register(Operation(
        method="GET", path=SPECTRA_BASE, operation_id="SPEC00",
        blueprint="spectral", service="SpectralService", request_model=RegistryQuery,
        response_model=ApiEnvelope[list[SpectrumDatasetView]], documented_errors=common_errors,
        delivery_phase="Alpha", handler=list_datasets, request_parser=registry_parser,
        description="The four registered spectral dataset summaries; metadata and refs only."))
    catalog.register(Operation(
        method="GET", path=f"{SPECTRA_BASE}/{{dataset_id}}", operation_id="SPEC01",
        blueprint="spectral", service="SpectralService", request_model=SpectrumQuery,
        response_model=ApiEnvelope[SpectrumDatasetView], documented_errors=common_errors,
        delivery_phase="Alpha", handler=dataset, request_parser=spectrum_parser,
        description="One recorded q dataset summary: 17 blocks, refs only; no 512-value dump."))
    catalog.register(Operation(
        method="GET", path=f"{SPECTRA_BASE}/{{dataset_id}}/points", operation_id="SPEC02",
        blueprint="spectral", service="SpectralService", request_model=SpectrumQuery,
        response_model=ApiEnvelope[SpectrumCurveView], documented_errors=common_errors,
        delivery_phase="Alpha", handler=points, request_parser=spectrum_parser,
        description="The complete 17-block spectral curve for one q; q is never interpolated."))
    catalog.register(Operation(
        method="GET", path=f"{SPECTRA_BASE}/{{dataset_id}}/points/{{mode_index}}", operation_id="SPEC03",
        blueprint="spectral", service="SpectralService", request_model=SpectrumModeQuery,
        response_model=ApiEnvelope[SpectralPointView], documented_errors=common_errors,
        delivery_phase="Alpha", handler=point, request_parser=mode_parser,
        description="One Fourier block record: alpha, leading eigenvalue and eigenvalue ref."))
    catalog.register(Operation(
        method="GET", path=f"{SPECTRA_BASE}/{{dataset_id}}/eigenmodes/{{mode_index}}", operation_id="SPEC04",
        blueprint="spectral", service="SpectralService", request_model=EigenmodeQuery,
        response_model=ApiEnvelope[EigenmodeView], documented_errors=common_errors,
        delivery_phase="Alpha", handler=eigenmodes, request_parser=eigenmode_parser,
        description="A saved LEFT/RIGHT vector or primitive profile; values load via ARRAY01."))
    catalog.register(Operation(
        method="GET", path=f"{SPECTRA_BASE}/validation/runs", operation_id="SPEC06",
        blueprint="spectral", service="SpectralService", request_model=RegistryQuery,
        response_model=ApiEnvelope[ValidationRunListView], documented_errors=common_errors,
        delivery_phase="Alpha", handler=validation_runs, request_parser=registry_parser,
        description="The 24 registered Fig13 validation-run identities (selector metadata only)."))
    catalog.register(Operation(
        method="GET", path=f"{SPECTRA_BASE}/validation/{{run_id}}", operation_id="SPEC05",
        blueprint="spectral", service="SpectralService", request_model=ValidationQuery,
        response_model=ApiEnvelope[GrowthValidationView], documented_errors=common_errors,
        delivery_phase="Alpha", handler=validation, request_parser=validation_parser,
        description="One recorded Fig13 validation run: 33 steps, recorded rates, missing facts explicit."))
