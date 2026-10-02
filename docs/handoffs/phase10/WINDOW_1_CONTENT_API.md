WINDOW=1_CONTENT_API
STATUS=PASS

CONTENT01=PASS
CONTENT02=PASS
CONTENT03=PASS

SCENES=7/7
MECHANISM=PASS
SCHEMATIC_ONLY=YES
NEAR1D_NUMERICAL_ENDPOINT=NO

OPENAPI=PASS
GENERATED_TYPES=PASS

TESTS=1088/1088 full backend;43/43 final content;157/157 targeted;frontend build PASS

SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0

PARALLEL_MERGE_SEAMS=
app factory
operation catalog
OpenAPI
generated types

MERGE_READY=YES

## Baseline and integration

BRANCH=phase10/content-api
WORKTREE=D:/code_project/CFD_visiblesystem_phase10_content_api
PHASE10_BASE_COMMIT=5d6ceb4bb64e15a5db51ecc77b297add5c9c39e3
ACCEPTED_WINDOW0_COMMIT=48286e3fc32e834f91f568d5a7f2d094840bde4d
WINDOW0_CHERRY_PICK=638b81e

The independent worktree starts at the accepted Phase10 base and cherry-picks
Window0. The original workspace remains on its Phase9 branch. No Phase9 code,
commits, OpenAPI artifacts or generated types were manually merged. Only
CONTENT01, CONTENT02 and CONTENT03 were added to the existing operation catalog.

## Delivered behavior

- CONTENT01: GET `/api/v1/explore/scenes`, `ApiEnvelope[SceneList]`, exactly seven
  full presets in their frozen 1..7 order. There is no scientific availability
  filter. Metadata survives unavailable, drifted and failed child services.
- CONTENT02: GET `/api/v1/explore/scenes/{scene_id}`,
  `ApiEnvelope[ScenePreset]`. Only the canonical integer identities 1..7 are
  valid. 0, 8 and malformed identities return 400 `INVALID_REQUEST`, availability
  ERROR, domain SYSTEM, using the existing FailedEnvelope. No new error code was
  invented. Path selectors cannot be overridden by query.
- CONTENT03: GET `/api/v1/mechanism`, `ApiEnvelope[MechanismContent]`, always
  SCHEMATIC. Its 11 unique nodes and 13 valid edges include interface state,
  background PSD, acoustic information, acoustic gate J, normal/tangential
  pathways, entropy-scaled combination and physical entropy-variable mapping.

All three operations accept only the frozen optional `registry_revision` query.
Unknown/repeated queries return typed 400; unavailable revision returns typed
409; POST returns typed 405 with Allow. Response request IDs and no-store headers
use the existing factory/catalog conventions. Content revisions are
`content-registry-v1.0.1` and `content-schematic-v1.0.1`.

`ContentService` loads the strict canonical content registry and never calls a
numerical adapter. Scientific targets retain existing experiment/config/result
identities; nine ScientificTarget objects reference 14 registered results.
Their real resource and result provenance endpoints resolve. No array, sampled
curve, scientific value, shadow result or frontend implementation was added to
the presets. `config/content/scenes.json` retains the accepted Window0 bytes and
SHA-256 `ee220d9e56f4eed297d64219931d30f91cf0f4809a2a316e485ef3db3b6980b4`.

## Mechanism and evidence boundary

Window0 omitted the combiner/mapping portion required by this window and the
frozen project scope. This delivery extends that graph with `combiner` and
`entropy-variable-mapping`, connecting the three existing dissipation pathways
to the combiner and the combiner to the mapping. The graph validator and content
freeze are updated to metadata version 1.0.1; no canonical DTO fields change.

The explanation was checked by reading the frozen production method and its
unbounded PSD implementation, without importing or executing them. The
combination/mapping prose expresses the frozen entropy-variable dissipative
action; it does not introduce a frontend formula evaluator.

The supported states remain exactly STRICT_1D and WEAKLY_2D. Display-state
changes belong to the frontend. Tangential receiving content does not enter J;
STRICT_1D can retain an acoustic trigger while tangential output vanishes. The
enabled weakly two-dimensional pathway remains conditional on receiving
content. No epsilon numeric query, state-vector API, live flux calculation or
numerical Near-1D endpoint exists.

All evidence references resolve through EVI02. Mechanism evidence reuses the
existing Spectrum record's production method/hash as explicitly limited
implementation context. Its existing numerical spectra are not claimed as a
Near-1D asymptotic scan; the raw Near-1D evidence gap remains MISSING. No fake
numerical evidence or new scientific result was registered.

## Contract generation and regression

OpenAPI was exported through `scripts.export_openapi` with deterministic LF
newlines matching Git checkout bytes; TypeScript was generated
with locked `openapi-typescript` 7.13.0. Tests export/generate twice in independent
processes and compare exact bytes with the checked-in artifacts. The runtime
document, catalog, routes and actual success/error payloads agree. Every
pre-existing OpenAPI path and schema remains semantically identical to the
Phase10 base. Existing catalog-coverage tests were updated to include the three
new operations.

The first full regression found one historical Phase8 reproduction test that
required current software seams to equal the old accepted application. Its
remaining 1087 tests passed. The reproduction test now materializes the
immutable accepted Phase8 commit for historical software checks, using actual
repository Git objects. Its scientific SOURCE_ROOT remains live and all
original scientific observations, hashes, source inventories and write guards
remain enforced. The corrected historical check passed separately. The source
audit implementation and historical source-map artifacts were not changed.
The final complete rerun passed 1088/1088 with no failures or skips. After
fixing export newlines, the 43 content/contract checks passed again on the final
artifacts; their exact working-tree bytes also match the Git index.

Frontend `npm run build` passes both vue-tsc and the Vite production build. Vite
retains the existing bundle-size advisory; no UI/source dependency changed.
The four frozen 03/04/05/06 contract documents retain their exact base bytes.
Scientific preservation covers all 189 accepted selected dependencies by path,
SHA-256, size and mtime_ns; this is not a new whole-passage6 audit.

Durable execution summary: `WINDOW1_CONTENT_VALIDATION.json`.
Local XML records: `.cache/phase10-window1/targeted.xml`, `initial-regression.xml`,
`historical-audit.xml`, `backend-full.xml`. The initial failure record is retained.

## Final V1 integration

Merge the source registration, request model and content service changes with
the other accepted windows. Resolve the app factory and operation catalog seams
explicitly. Regenerate the complete OpenAPI and generated TypeScript types from
the final integrated catalog; do not manually combine generated artifacts.
The same final catalog-coverage assertions must include all accepted operations.

WINDOW2_STARTED=NO
STOP=Window 1 only; no frontend implementation or later window started.
