from uuid import uuid4

from flask import Flask, g

from backend.adapters import Case8Adapter, Case8AdapterProtocol
from backend.api.allocation import register_allocation_operations
from backend.api.arrays import register_array_operations
from backend.api.case8 import register_case8_operations
from backend.api.cylinder import register_cylinder_operations
from backend.api.crossflow import register_crossflow_operations
from backend.api.content import register_content_operations
from backend.api.closure import register_closure_operations
from backend.api.catalog import OperationCatalog
from backend.api.evidence import register_evidence_operations
from backend.api.registry import register_registry_operations
from backend.api.spectral import register_spectral_operations
from backend.api.system import register_system_operations
from backend.core.errors import register_error_handlers
from backend.core.settings import Settings
from backend.models import ProjectInfo
from backend.registry import load_bootstrap_project
from backend.services import Case8Service, AllocationServiceImpl, SpectralServiceImpl


_DEFAULT_ADAPTER = object()


def create_app(settings: Settings | None = None, *, case8_adapter: Case8AdapterProtocol | None | object = _DEFAULT_ADAPTER,
               allocation_adapter=_DEFAULT_ADAPTER, spectral_adapter=_DEFAULT_ADAPTER,
               cylinder_adapter=_DEFAULT_ADAPTER,
               closure_adapter=_DEFAULT_ADAPTER,
               project: ProjectInfo | None = None,
               configure_catalog=None) -> Flask:
    settings = settings or Settings.from_env()
    if settings.enable_accounts:
        raise ValueError("Accounts must remain disabled in Phase 5A")
    if case8_adapter is _DEFAULT_ADAPTER:
        case8_adapter = Case8Adapter(settings.scientific_data_root) if settings.scientific_data_root else Case8Adapter()
    if allocation_adapter is _DEFAULT_ADAPTER:
        from backend.adapters.allocation_integration import IntegratedAllocationAdapter
        allocation_adapter = IntegratedAllocationAdapter(case8_root=settings.scientific_data_root or None)
    if spectral_adapter is _DEFAULT_ADAPTER:
        from backend.adapters.spectral_data import SpectralAdapter
        spectral_adapter = SpectralAdapter()
    if cylinder_adapter is _DEFAULT_ADAPTER:
        from backend.adapters.cylinder import CylinderAdapter
        cylinder_adapter = CylinderAdapter(settings.scientific_data_root) if settings.scientific_data_root else CylinderAdapter()
    if closure_adapter is _DEFAULT_ADAPTER:
        from backend.adapters.entropy_closure import EntropyClosureAdapter
        closure_adapter = EntropyClosureAdapter(settings.scientific_data_root) if settings.scientific_data_root else EntropyClosureAdapter()
    app = Flask(__name__, static_folder=None)
    app.config.update(TESTING=False, JSON_SORT_KEYS=False)
    app.extensions["settings"] = settings
    app.extensions["case8_service"] = Case8Service(case8_adapter)
    app.extensions["allocation_service"] = AllocationServiceImpl(allocation_adapter)
    app.extensions["spectral_service"] = SpectralServiceImpl(spectral_adapter)
    from backend.services.cylinder import CylinderService
    app.extensions["cylinder_service"] = CylinderService(cylinder_adapter)
    from backend.services.closure import ClosureService
    app.extensions["closure_service"] = ClosureService(closure_adapter)
    project = project or load_bootstrap_project()
    if project.account_extension.enabled:
        raise ValueError("Bootstrap project metadata must disable accounts")
    if isinstance(case8_adapter, Case8Adapter):
        from backend.registry import case8_registry as registry
        project = project.model_copy(update={
            "registry_revision": registry.REGISTRY_REVISION,
            "data_revision": registry.DATA_REVISION,
            "experiments": [ref.model_copy(update={"delivery_status": "IMPLEMENTED"})
                            if ref.experiment_id == "case8" else ref for ref in project.experiments],
        })
    if cylinder_adapter is not None:
        project = project.model_copy(update={"experiments": [
            ref.model_copy(update={"delivery_status": "IMPLEMENTED"}) if ref.experiment_id == "cylinder" else ref
            for ref in project.experiments]})
    if closure_adapter is not None:
        project = project.model_copy(update={"experiments": [
            ref.model_copy(update={"delivery_status": "IMPLEMENTED"}) if ref.experiment_id == "entropy-closure" else ref
            for ref in project.experiments]})
    catalog = OperationCatalog()
    service = app.extensions["case8_service"]
    allocation_service = app.extensions["allocation_service"]
    spectral_service = app.extensions["spectral_service"]
    from backend.services.spectral_resources import ResultResourceRouter, SpectralResources
    from backend.services.cylinder_resources import CylinderResources
    from backend.services.closure_resources import ClosureResources
    from backend.services.crossflow import ComparisonService
    cylinder_service = app.extensions["cylinder_service"]
    closure_service = app.extensions["closure_service"]
    resources = ResultResourceRouter(service, SpectralResources(spectral_service), project,
                                     CylinderResources(cylinder_service), allocation_service, ClosureResources(closure_service))
    app.extensions["result_resources"] = resources
    comparison_service = ComparisonService(service, cylinder_service, allocation_service)
    app.extensions["comparison_service"] = comparison_service
    from backend.services.evidence import EvidenceService
    from backend.registry import cylinder_registry, closure_registry
    from backend.registry import case8_allocation, spectral_registry
    roots = {}
    for adapter, assets in ((cylinder_adapter, cylinder_registry.ASSETS), (closure_adapter, closure_registry.ASSETS)):
        if hasattr(adapter, "_root"):
            roots.update({a["asset_id"]: adapter._root for a in assets.values()})
    if hasattr(spectral_adapter, "_root"):
        roots.update({a[0]: spectral_adapter._root for a in spectral_registry.ASSETS.values()})
    if hasattr(allocation_adapter, "face"):
        roots.update({a[0]: allocation_adapter.face._root for a in case8_allocation.ASSETS.values()})
        for config in ("Acoustic", "Pressure", "Ungated"):
            roots.update({a["asset_id"]: allocation_adapter.cell._root for a in allocation_adapter._gate_assets(config)})
    evidence_service = EvidenceService(settings.scientific_data_root or getattr(case8_adapter, "_root", "D:/Paper/passage6"), roots=roots)
    app.extensions["evidence_service"] = evidence_service
    if isinstance(case8_adapter, Case8Adapter):
        service.evidence_guard = evidence_service
    register_system_operations(catalog, project)
    register_registry_operations(catalog, project, service, cylinder_service, closure_service)
    register_case8_operations(catalog, project, service)
    register_array_operations(catalog, project, resources)
    register_evidence_operations(catalog, project, resources, allocation_service, evidence_service)
    register_allocation_operations(catalog, project, allocation_service)
    register_spectral_operations(catalog, project, spectral_service)
    from backend.registry import cylinder_registry as cylinder_registry
    cylinder_project = project.model_copy(update={"registry_revision": cylinder_registry.REGISTRY_REVISION,
                                                  "data_revision": cylinder_registry.DATA_REVISION})
    register_cylinder_operations(catalog, cylinder_project, cylinder_service)
    register_crossflow_operations(catalog, project, comparison_service)
    from backend.services.content import ContentService
    content_service = ContentService()
    app.extensions["content_service"] = content_service
    register_content_operations(catalog, content_service)
    from backend.registry import closure_registry
    closure_project = project.model_copy(update={"registry_revision": closure_registry.REGISTRY_REVISION,
                                                 "data_revision": closure_registry.DATA_REVISION})
    register_closure_operations(catalog, closure_project, closure_service)
    if configure_catalog is not None:
        configure_catalog(catalog, service)
    app.extensions["operation_catalog"] = catalog

    @app.before_request
    def request_identity():
        g.request_id = str(uuid4())

    @app.after_request
    def response_headers(response):
        response.headers["X-Request-ID"] = g.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    register_error_handlers(app)
    catalog.bind(app)
    return app
