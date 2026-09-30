from uuid import uuid4

from flask import Flask, g

from backend.adapters import Case8AdapterProtocol
from backend.api.catalog import OperationCatalog
from backend.api.system import register_system_operations
from backend.core.errors import register_error_handlers
from backend.core.settings import Settings
from backend.models import ProjectInfo
from backend.registry import load_bootstrap_project
from backend.services import Case8Service


def create_app(settings: Settings | None = None, *, case8_adapter: Case8AdapterProtocol | None = None,
               project: ProjectInfo | None = None, configure_catalog=None) -> Flask:
    settings = settings or Settings.from_env()
    if settings.enable_accounts:
        raise ValueError("Accounts must remain disabled in Phase 5A")
    app = Flask(__name__, static_folder=None)
    app.config.update(TESTING=False, JSON_SORT_KEYS=False)
    app.extensions["settings"] = settings
    app.extensions["case8_service"] = Case8Service(case8_adapter)
    project = project or load_bootstrap_project()
    if project.account_extension.enabled:
        raise ValueError("Bootstrap project metadata must disable accounts")
    catalog = OperationCatalog()
    register_system_operations(catalog, project)
    if configure_catalog is not None:
        configure_catalog(catalog, app.extensions["case8_service"])
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
