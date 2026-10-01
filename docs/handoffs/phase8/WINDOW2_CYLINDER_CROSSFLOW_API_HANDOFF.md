# Window 2 Cylinder API and cross-flow composite

Branch: `phase8/cylinder-crossflow-api`.
Worktree: `D:/code_project/CFD_visiblesystem_phase8_cylinder_crossflow_api`.
Base: `69a318b65b9378066b9a55e429dfca162cef32af` (`PHASE8_BASE_COMMIT`).
Window 1 commit `27907da` was cherry-picked as `77b9685`; its adapter, service and
scientific registry implementations are reused unchanged.

CYL01–09 are registered at the exact frozen paths under
`/api/v1/experiments/cylinder/configs/{config_id}`. A_u/B_u/D_u are accepted;
C_u is always 422 UNSUPPORTED_COMBINATION. Unknown configs are 404, unknown or
duplicate query keys are 400, and snapshot zero is 400. Snapshot 1 is completed
step 0; five real NPZ times are retained. History pagination keeps 9757 total
points, with a default page of 2000 and maximum page of 5000.

CYL06 returns HTTP 200 PARTIAL with sectors and front_band AVAILABLE and
cumulative_2d MISSING without value. The envelope issues contain
MISSING_SCIENTIFIC_ASSET and the missing evidence reference. CYL07 retains
ANGULAR_SECTORS, 16 bins, 17 edges and four channels; CYL08 retains REGION_SCALAR,
the cumulative interior-only fixed A_u radial band and undefined A/B fractions.
No cumulative-map, heatmap or spatial-map route is registered.

Cylinder results use the existing ARRAY01 resource router with exact ownership
membership drawn from the frozen registry. All 576 materialized result identities
have canonical owners. Field members, native saved geometry, sector edges and
channel arrays are decoded exclusively by the accepted adapter. Unknown Cylinder
IDs do not dispatch to that adapter or become paths. Case8 native-face ArrayRefs
emitted by the composite also use ARRAY01 with their own allocation revision.
The existing EVI02/EVI03 surfaces resolve Cylinder evidence and provenance.
REG01–04 expose the delivered Cylinder registry and its cumulative-2d gap.

CMP01 is `GET /api/v1/comparisons/case8-cylinder`, with frozen ComparisonQuery
fields registry_revision, case8_config and cylinder_config, defaulting to D_u/D_u.
It accepts only Case8 A/B/C/D and Cylinder A/B/D. There are no q_at, normalize,
sort or winner selectors. The outer comparison revision is the existing project
registry revision; each original child retains its own revision and data revision.

ComparisonService assembles validated CrossFlowSide children on the server.
Budget MetricCollections project the recorded last cumulative bg/aa/at scalar
values directly, retaining original result IDs, definition IDs, units, scope,
time and provenance. No channel sum or cross-flow normalization is performed.
Snapshot and history data are referenced rather than embedded as numeric arrays.
Case8 D_u native-face allocation remains DIAGNOSTIC_RERUN; A/B/C maps remain
MISSING. Case8 front_band is UNSUPPORTED. Cylinder retains sectors and front-band;
the missing cumulative2D evidence and limitation persist on the composite.

Four explicit ComparabilityRules cover FACE_FIELD localization versus radial band,
high-k versus HF-RMS, Cartesian versus radial widths/detector floor, and different
budget scopes/time horizons. Every rule is DESCRIPTIVE_ONLY, with no declared
mapping. ranking_policy is exactly NO_UNIFIED_RANKING. The frozen DTO forbids extra
winner/score/rank fields. Missing independent child results preserve other children;
a partial MetricCollection preserves its available entries and reports its issues.

The composite aggregates navigable EvidenceRecord IDs from both sides. Legacy
Case8 config/domain metadata uses some SourceAsset IDs in evidence_refs; those
remain intact on the original children while the composite summary list includes
only registered evidence identities. All summary evidence links are tested through
EVI02. Detector, origin and missing-data limitations are retained and aggregated.

OpenAPI 3.1 and generated frontend TypeScript declarations include all ten new
operations. Every pre-existing OpenAPI component remains identical to the base.
The complete frozen allocation union has the schema name CylinderAllocationResult
to avoid overwriting the existing two-variant Phase 6 AllocationResult component;
the Window 1 AllocationResult import alias and all frozen wire fields are preserved.
No adapter is reimplemented. The old tests' branch labels, Case8-only catalog
assumptions and blanket prohibition on every family's `/allocation` path were
updated to reflect integration; scientific assertions and frozen hash checks remain.

Validation evidence is recorded in WINDOW2_TESTS.xml, WINDOW2_PRIOR_SLICES.xml,
WINDOW2_FINAL_ARRAY_REGRESSION.xml and WINDOW2_FULL_REGRESSION.xml. API examples
are in WINDOW2_API_EVIDENCE.json. Final counts and merge readiness are recorded in
WINDOW_2_CYLINDER_CROSSFLOW_API.md and WINDOW2_CYLINDER_CROSSFLOW_API_REPORT.json.

One pre-existing baseline failure is retained: the Phase5 freeze JSON has LF in
Git checkouts while its accepted raw-byte hash records CRLF. Window 1 already
reproduced the failure in the unmodified bootstrap. The expected hash and accepted
original bytes are preserved; the freeze and manifest have not been edited.

Reproduce from this worktree:

```powershell
& 'D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe' -m scripts.export_openapi
npm run generate:types --prefix frontend
& 'D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe' -m pytest -q tests/window2_cylinder_crossflow_api
npm run build --prefix frontend
& 'D:/code_project/CFD_visiblesystem/.venv/Scripts/python.exe' -m scripts.verification.cylinder_crossflow_audit
```

Source preservation checks cover 189 selected, dependency and excluded audited
scientific files by SHA256, size, mtime_ns and directory membership. All remain
unchanged. Frozen Phase4 documents and existing OpenAPI components are checked
against the base. No CFD was started and no scientific files were written.
The original dirty Phase7 worktree was preserved. Delivery ends at this window.
