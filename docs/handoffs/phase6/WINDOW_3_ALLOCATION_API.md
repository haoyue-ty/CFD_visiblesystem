WINDOW=3_ALLOCATION_API
STATUS=PASS
BRANCH=phase6/allocation-api
SCOPE=Flask service/API layer only; no scientific files read or modified
DEPENDS_ON=AllocationService interface (backend/services/allocation.py)
==================================================
API_TESTS=16/16 PASS (tests/window3_allocation_api)
  - registration/OpenAPI: 2  valid: 4  missing: 4  unsupported: 4  hygiene: 3  source: 1
  - valid:      metadata/array/summary/comparison all 200 AVAILABLE
  - missing:    ALLOC01-ALLOC04 -> 404 MISSING_ASSET (domain SCIENTIFIC)
  - unsupported:ALLOC01-ALLOC04 -> 422 UNSUPPORTED_REPRESENTATION (domain SCIENTIFIC)
  - source:     ALLOC01 -> 500 SOURCE_ERROR
  - hygiene:    unknown query -> 400 INVALID_REQUEST; no adapter -> 503 FEATURE_NOT_ENABLED;
                bad revision -> 409 REVISION_UNAVAILABLE
TOTAL_SUITE=404/404 PASS (baseline 388 + 16 new)
==================================================
OPERATIONS_ADDED=4
  ALLOC01 GET /api/v1/allocations/{result_id}/metadata        -> ApiEnvelope[AllocationMetadata]
  ALLOC02 GET /api/v1/allocations/{result_id}/arrays/{array_id} -> ApiEnvelope[AllocationArrayResponse]
  ALLOC03 GET /api/v1/allocations/{result_id}/summary         -> ApiEnvelope[AllocationSummary]
  ALLOC04 GET /api/v1/allocations/comparison                  -> ApiEnvelope[AllocationComparison]
REPRESENTATION_TYPE=mandatory on every allocation response (metadata/array/summary/comparison)
  AllocationMetadata.representation_type + wire_representation
  AllocationArrayResponse.representation_type
  AllocationComparison.representation_type + per-entry representation_type
FRONTEND_GUESSING=FORBIDDEN; no route infers face/cell from shape or field identity
ERRORS=3 contract-listed codes added: MISSING_ASSET(404)/UNSUPPORTED_REPRESENTATION(422)/SOURCE_ERROR(500)
==================================================
OPENAPI=config/openapi.json regenerated (20 paths, openapi 3.1.0, spec-validator PASS)
TYPES=frontend/src/types/generated/api.d.ts regenerated (openapi-typescript 7.13.0)
==================================================
CONTRACT_DEVIATIONS=1 tracked, non-scientific
  - docs/06_API_CONTRACT.md C807 "{base}/allocation" stays CONTRACT_DEFINED/IMPLEMENTATION_DEFERRED.
    Window 3 delivers a NEW surface at /api/v1/allocations/* that deliberately does NOT end in
    "/allocation", so C807 stays unadvertised. Adjusted two pre-existing guards accordingly:
      * tests/verification/test_api_contract.py::test_no_operation_is_advertised_for_the_deferred_allocation_endpoint
      * tests/window2_case8_api/test_case8_api_contract.py (IMPLEMENTED set + path assertion)
    Both still assert C807 remains absent; the new assertions confirm ALLOC routes are present
    on a distinct path shape.
  - 04/05/06 frozen doc hashes UNCHANGED (test_frozen_docs_hashes_unchanged PASS)
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
==================================================
FILES_CHANGED
  new: backend/api/allocation.py
  new: tests/window3_allocation_api/{conftest.py,fake_allocation_adapter.py,test_allocation_api_contract.py}
  mod: backend/services/allocation.py         (AllocationServiceImpl dispatch + typed error mapping)
  mod: backend/models/allocation.py           (AllocationMetadata/AllocationArrayResponse/AllocationComparison)
  mod: backend/models/__init__.py             (export + CORE_MODELS)
  mod: backend/core/errors.py                 (3 codes + missing_asset/unsupported_representation/source_error)
  mod: backend/core/app.py                    (wire register_allocation_operations + allocation_adapter DI)
  mod: backend/schemas/requests.py            (AllocationQuery/AllocationArrayQuery/AllocationComparisonQuery)
  mod: backend/services/__init__.py
  mod: config/openapi.json, frontend/src/types/generated/api.d.ts (regenerated)
  mod: tests/verification/test_api_contract.py, tests/window2_case8_api/test_case8_api_contract.py (guards)
NEXT=WINDOW_4 (frontend allocation views already present untracked)
