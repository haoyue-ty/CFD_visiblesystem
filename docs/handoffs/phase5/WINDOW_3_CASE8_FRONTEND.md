WINDOW=WINDOW_3_CASE8_FUNCTIONAL_FRONTEND
STATUS=PASS
BASE_COMMIT=7d73806a436d95adacb9b7d3de5a88c14ad9dcba
HEAD_COMMIT=branch_tip_of_phase5/case8-frontend (single commit on BASE_COMMIT; see `git rev-parse phase5/case8-frontend`)
PAGES_IMPLEMENTED=P01_Entry,P02_Home,P04_Lab_P04Workspace,P06_Case8_Detail,P09_Evidence_Detail
CONFIG_SELECTOR=ENABLED(A_u,B_u,C_u,D_u; default D_u; URL query ?config=; invalid falls back to D_u)
SNAPSHOT_UI=ENABLED(recorded 1..6 only; shows "Snapshot n / 6" + actual completed step + actual physical time; index 0 rejected and not offered; Canvas 2D renders recorded values with no interpolation)
ENTROPY_UI=ENABLED(ECharts E_bg/E_aa/E_at; click selects a real accepted step; shows selected scalar time AND displayed snapshot time side by side with an explicit different-granularity warning)
METRICS_UI=ENABLED(width/front_RMS/HF each with value, definition text+id, unit, detector scope, time scope, resolution limit and View-evidence link; three bare numbers not shown)
EVIDENCE_NAV=ENABLED(any result -> "View evidence" -> P09 with return context; "Back to result" restores experiment+config+tab; direct deep-link shows no fake back target)
FRONTEND_TESTS=playwright:/tests/window3_frontend/case8_slice.spec.ts
DATA_PROVIDER=MOCK(typed DataProvider interface + createMockProvider; page -> dataService -> provider; setProviderKind('API') ready for integration, pages unchanged)
MOCK_LABEL_VISIBLE=YES(persistent appbar badge + per-region MockBadge; every result data_origin=MOCK, verification=NOT_APPLICABLE, result_id prefixed mock.)
BACKEND_FILES_MODIFIED=NONE
SCIENTIFIC_FILES_MODIFIED=NO
CONTRACT_GAPS=config/openapi.json + generated api.d.ts expose only SYS01/DOC01; frozen C801..C808 are contract-defined but not in the bootstrap artifact, so the data-service DTOs mirror the documented frozen shapes directly instead of the generated types
BLOCKERS=NONE
MERGE_READY=YES

CHANGED_PATHS
frontend/src/data/domain.ts
frontend/src/data/provider.ts
frontend/src/data/mockProvider.ts
frontend/src/data/index.ts
frontend/src/components/MockBadge.vue
frontend/src/components/LoadStateBlock.vue
frontend/src/pages/{Entry,Home,Lab,Experiment,Evidence}Page.vue
frontend/src/views/case8/{Overview,Flow,Entropy,Metrics,Evidence}Tab.vue
frontend/src/scientific/{SnapshotViewer,EntropyChart,MetricsPanel,ScientificStatus,EvidenceLink}.vue
frontend/src/App.vue, frontend/playwright.config.ts, tests/window3_frontend/case8_slice.spec.ts
