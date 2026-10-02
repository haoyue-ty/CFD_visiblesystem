WINDOW=1_EVIDENCE_CORE
STATUS=PASS

PHASE8_PRESENT=YES
PHASE9_PRESENT=YES
PHASE10_PRESENT=YES

EVI01=PASS
EVI02=PASS
EVI03=PASS
EVI04=PASS

CURRENT=PASS
GAPS=PASS
HISTORY=PASS

RESULT_PROVENANCE=PASS
SOURCE_ASSET=PASS
HASH_SEMANTICS=PASS
SOURCE_DRIFT=PASS
PUBLIC_PATH_SAFETY=PASS

EXPERIMENT_COVERAGE=Case8;Gate Ablation;Allocation;Spectrum;Eigenmodes;Modal Validation/Fig13;Cylinder;Cross-flow;Entropy Closure;Mechanism;Explore existing references
EVIDENCE_RECORDS=15480 total;13296 CURRENT;199 accepted metadata groups/templates plus finite exact spectral selectors and inventory history/gaps
GAPS_COUNT=11
HISTORY_COUNT=2173

OPENAPI=PASS;3.1 validation;runtime=saved=independent export;pre-existing component schemas unchanged
GENERATED_TYPES=PASS;independent regeneration byte-identical;production typecheck/build PASS
TESTS=PASS;1343/1343 backend;62 dedicated evidence tests included;166/166 browser runner;0 failures/errors/skips/flaky;retries0

SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0

MERGE_READY=YES
BLOCKERS=NONE

BRANCH=phase11/evidence-core
WORKTREE=D:/code_project/CFD_visiblesystem_phase11_evidence_core
PHASE8_COMMIT=fceb3b6c569cf381b04767da77b4b92418a4b5ed
PHASE9_COMMIT=0df633ff6cd9bd939fdbd0eb2b39a3ec0ac7e880
PHASE10_COMMIT=004b0e7e8081e5331ed7aa6291b83afdcdc4f45b
PHASE11_BASE_COMMIT=884bcd382f8d6fe67062e779ce37bbeeebe7816f
INITIAL_WORKTREE_CLEAN=YES

## Accepted integration baseline

The Phase8, Phase9 and Phase10 final PASS audits were read from their accepted commits. Phase9 and Phase10 were parallel; the independent candidate started at accepted Phase10 and merged accepted Phase9. The base commit above contains all three accepted commits as ancestors. Shared app-factory registration, operation catalog expectations, frontend experiment routing, OpenAPI and generated types were reconciled in that integration commit. Baseline regression: 1280 passed, one local preservation-fixture skip. The final run supplies that fixture from the pre-change source inventory. The original shared checkout, `D:/code_project/CFD_visiblesystem`, remains untouched.

## Four frozen operations, one registry

| Operation | Frozen path | Delivered behavior |
| --- | --- | --- |
| EVI01 | GET /api/v1/evidence | Server filtering and pagination over CURRENT/GAPS/HISTORY/ALL |
| EVI02 | GET /api/v1/evidence/{evidence_id} | Complete frozen EvidenceRecord, including recorded contexts and current dependency observations |
| EVI03 | GET /api/v1/results/{result_id}/provenance | Every direct evidence record and source asset for the registered identity |
| EVI04 | GET /api/v1/assets/{asset_id} | Safe registered asset description and hash/verification facts; no file contents |

EVI01 retains the actual frozen `EvidenceQuery`: `registry_revision`, `section`, `experiment_id`, `status`, `offset`, `limit`. Default section is CURRENT, limit is 50, maximum 200. Filtering precedes pagination. `source_drift` is an output fact; it was not a legal frozen query field and is rejected with INVALID_REQUEST, as are arbitrary path/download fields and duplicate single-value parameters. No alternate provenance API or query schema was introduced.

EVI01/EVI04 use `evidence-registry-v1`. EVI02/EVI03 retain the scientific context's accepted registry revision when one exists. The registry contains 2438 registered assets and 14140 result/content identities. The Mechanism content identity is navigable through EVI03 without acquiring a numerical result header.

CURRENT contains the accepted selection, not the whole asset inventory. Nonselected legacy/superseded/unverified historical assets are HISTORY even if an inventory row had an old verification label. Known missing and unsupported evidence is GAPS. Missing or positively changed data dependencies move affected current numerical records to GAPS during a live index request; their recorded detail remains inspectable.

| Current family | Evidence records |
| --- | ---: |
| Case8 (including Allocation) | 105 |
| Gate Ablation | 3 |
| Spectrum and Eigenmodes | 13128 |
| Modal Validation / Fig13 | 24 |
| Cylinder | 18 |
| Entropy Closure | 16 |
| Mechanism | 1 |
| Shared implementation basis | 1 |

Explore and Mechanism foundation references continue to resolve existing evidence IDs. Cross-flow adds no duplicate science evidence: all 12 legal comparisons resolve separate Case8 and Cylinder records, including the established Cylinder missing-cumulative2D record. Gate min/max comparisons resolve all three direct allocation records.

## Scientific metadata and hash semantics

`data/evidence/canonical_metadata.json` consolidates accepted headers, definitions, masks, configuration and dependency bindings. It stores no numerical field/history/vector payloads. Spectral templates cover exact saved selectors (four datasets, modes 0–16, saved ranks 0–31 and legal representations); runtime expansion changes identities only. Evidence requests hash registered sources and read software metadata without invoking numerical adapters or scientific code.

The one-time consolidation script reads accepted frozen adapter output and extracts metadata; it does not calculate new science or establish a new freeze. Its accepted-base binding is explicit. Scientific creation/verification dates without authoritative events stay UNKNOWN. Live observation timestamps also remain UNKNOWN because no persisted observation event is recorded. File mtimes and the audit date are never used as scientific event dates.

Data hash, method hash, recorded/current implementation source hash and per-asset hash observations remain separate. Cylinder/Closure composite data hashes are UNKNOWN: the earlier locally assembled child-hash digest was removed. Existing authoritative single-asset data hashes remain intact. The Gate protocol-lock asset is CONFIG and uses its recorded inventory hash, rather than the method-code hash. Case8/Gate now include the actual unified method source as a separate dependency. No scientific payload ETag is invented.

Positive drift in any dependency wins over unknown observations. FALSE requires all dependencies to have known matching hashes; absent/unreadable/baseline-free inputs produce UNKNOWN. EVI02/EVI03/EVI04 remain readable after source drift, with explicit limitations and reduced current verification. Readability does not certify numerical reproduction. Numerical APIs preserve HTTP409 SOURCE_DATA_DRIFT; Case8 delivery gains a dependency guard, and Gate/Spectral transport no longer collapses this error into generic HTTP500. Cylinder/Closure retain their existing numerical guard semantics. Drift tests modify relocated temporary copies only.

Mechanism evidence is SCHEMATIC theory/implementation basis, with empty result_ids/result_contexts and an explicit limitation. Cylinder cumulative2D, Near1D authoritative five-epsilon raw, persisted Fourier matrices and unsaved Closure spatial trajectory remain missing. Case8's Cylinder front-band task is UNSUPPORTED with NOT_APPLICABLE verification. Recorded B_u D_at/E_at zeros retain their known numeric values.

## Source protection and public safety

Public SourceAsset fields retain their frozen schema. Controlled relative origins reject absolute/drive/UNC/file-URI/traversal paths. Backend locator resolution also checks root containment after symlink/junction resolution. No arbitrary source path enters EVI04, and no download/file-serving route is added.

The Phase8 preservation audit receives a narrow Phase11 software-seam allowance tied to this accepted metadata base. Its core scientific-code and frozen-document checks remain active, including rejection of an injected unauthorized core.py change. Closure's adapter preservation test permits only the exact evidence-hash removal; its numerical decoding, arithmetic checks and freeze binding remain identical to accepted Window1 bytes.

Full source-tree preservation compares relative paths, SHA256, sizes and mtime_ns for all 27742 files (5429246095 bytes) under the read-only scientific root. The source fingerprint and final reports are recorded in `WINDOW1_VALIDATION.json` and `WINDOW1_SOURCE_PRESERVATION.json`. Phase8–10 handoffs/freeze documents remain unchanged since the integration base.

SOURCE_PRESERVATION=PASS;27742/27742 files;all paths/hash/size/mtime_ns identical
SOURCE_FINGERPRINT=47ed91e8dbf02b88edb8a87768687d474cd24b8dde9165e17c3c0b83d62a001b;pre=post

## Validation and stop boundary

The 62 dedicated acceptance tests cover sections, frozen query fields, pagination, typed unknown IDs, representative EVI03 chains, all direct Cross-flow sources, safe EVI04, no download, hash/date separation, dependency drift, HTTP409 across five numerical families, missing versus recorded zero, nonnumerical Mechanism, Explore reuse, Phase5–10 registry coverage and OpenAPI parity. Final full backend and browser reports accompany this handoff. Initial failures and their repair descriptions are retained in the machine validation evidence.

Final backend: 1343 passed in 659.45s; zero skipped. Final browser: 166 passed in 510.21s; zero skipped, unexpected or flaky, retries0. All 2438 registered public asset DTOs were validated and scanned for absolute locators with zero matches. Independent contracts/types checks passed. Full regression reports: `WINDOW1_BACKEND_TESTS.xml`, `WINDOW1_BROWSER_TESTS.xml`; validation and source preservation: `WINDOW1_VALIDATION.json`, `WINDOW1_SOURCE_PRESERVATION.json`.

Reproduce the checks from this worktree using PowerShell 7:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.export_openapi --output .cache/phase11/openapi-independent.json
npm --prefix frontend exec -- openapi-typescript .cache/phase11/openapi-independent.json -o .cache/phase11/api-independent.d.ts
npm --prefix frontend run build
$env:E2E_API_PORT='5113'
$env:E2E_PRODUCTION_PORT='4413'
$env:E2E_MOCK_PORT='4513'
npm --prefix frontend exec -- playwright test --config frontend/playwright.phase11.integration.config.ts
```

The local runtime and dependency directories are ignored junctions to the already installed shared runtimes. The optional Phase6 source-preservation fixture is populated locally from the pre-change source inventory; it is not a new scientific baseline. The complete pre-change 27742-row inventory remains at `.cache/phase11/source_before.json`. Preserved initial/repair reports remain under `.cache/phase11`, and their test counts/repair explanations appear in the committed validation JSON.

Known scientific limitations remain the accepted limitations; this window does not fill absent raw data, change scientific conclusions or run CFD. Existing Vite chunk-size advisory remains. No accounts, database, export/download subsystem, cloud synchronization or UI polish was added. This delivery stops after committing Window1; it does not begin Window2 or merge into another branch.
