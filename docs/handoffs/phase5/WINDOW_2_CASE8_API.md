WINDOW=2_CASE8_FLASK_SERVICE_API
STATUS=PASS
BRANCH=phase5/case8-api
BASE_COMMIT=7d73806a436d95adacb9b7d3de5a88c14ad9dcba
HEAD_COMMIT=c6f557691544349a9b8bdc01f05871ea2f96fdd9
OPERATIONS_IMPLEMENTED=SYS01,DOC01,REG01,REG02,REG03,REG04,C801,C802,C803,C804,C805,C806,C808,ARRAY01,EVI02,EVI03
OPERATIONS_DEFERRED=C807(CONTRACT_DEFINED/IMPLEMENTATION_DEFERRED),EVI01,EVI04,AUTH01-06
API_TESTS=pytest:117_PASS(59_pre-existing+58_window2);openapi_spec_validator:PASS;jsonschema_Draft202012:PASS
OPENAPI_EXPORT=config/openapi.json(16_paths,158_schemas,OpenAPI_3.1.0,validated)
SNAPSHOT_ZERO_REJECTED=YES(400_INVALID_REQUEST,never_reaches_adapter)
SNAPSHOT_SEVEN=SNAPSHOT_NOT_FOUND_404
UNSUPPORTED_VS_UNKNOWN=C_u->422_UNSUPPORTED_COMBINATION;Z_u->404_UNKNOWN_CONFIG
HISTORY_PAGINATION_TOTAL_PRESERVED=YES(limit=1_page_still_declares_total_point_count=1912)
REAL_SCIENTIFIC_FILES_READ=NO
SCIENTIFIC_FILES_MODIFIED=NO
FRONTEND_FILES_MODIFIED=NO
ACCOUNTS_IMPLEMENTED=NO
GATE_SPECTRUM_CYLINDER_IMPLEMENTED=NO
MYSQL_CONFIGURED=NO
CONTRACT_GAPS=C807_not_registered_by_design;EVI01/EVI04_deferred;C807+D_u_cumulative_absent_from_OpenAPI
BLOCKERS=NONE
MERGE_READY=YES(subject_to_Window1_adapter_delivery)

CHANGED_PATHS
- backend/api/registry.py (new, REG01-04)
- backend/api/case8.py (new, C801-C806/C808)
- backend/api/arrays.py (new, ARRAY01)
- backend/api/evidence.py (new, EVI02/EVI03)
- backend/api/catalog.py (unchanged; reused as-is)
- backend/core/errors.py (typed scientific errors + SERVER_SIDE_CODES)
- backend/core/app.py (wire five operation registrars)
- backend/schemas/requests.py (path-declaring request models)
- backend/adapters/case8.py + backend/services/case8.py (+load_snapshot_alignment)
- config/openapi.json, tests/window2_case8_api/, docs/handoffs/phase5/WINDOW_2_CASE8_API.md
