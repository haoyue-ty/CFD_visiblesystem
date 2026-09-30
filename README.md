# ShockPath Phase 5A bootstrap

This branch implements the engineering and contract foundation of the frozen
Phase 4 v1.0.1 design. It does not implement the Case8 scientific slice.
Python 3.12+ and Node 24 are the verified local runtimes. Use PowerShell 7.

From the repository root:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
./.venv/Scripts/python.exe -m pip install --no-deps -e .
./.venv/Scripts/python.exe -m scripts.serve_backend
```

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

The backend listens on `127.0.0.1:5000`; Vite proxies `/api` there.
`GET /api/v1/system` (SYS01) provides software-owned bootstrap metadata.
`GET /api/v1/openapi.json` (DOC01) provides a native OpenAPI 3.1 document.
The five frontend routes are `/`, `/home`, `/lab`,
`/lab/experiments/:experiment_id`, and `/evidence/:evidence_id`.
These pages show placeholders and have no scientific data requests.

Settings read the process environment; `.env.example` is a template, not an
automatically loaded file. Empty API_HOST/API_PORT use loopback/5000.
Scientific path settings are reserved and never opened during bootstrap.
The explicit revisions in `config/bootstrap_project.json` describe only this
software metadata and the absence of loaded scientific data. They are not
Phase 1 inventory revisions or a scientific certification. All six experiment
references are PLANNED. Accounts are disabled and enabling them is rejected.

Regenerate and validate the shared contract from the root:

```powershell
./.venv/Scripts/python.exe -m scripts.export_openapi
./.venv/Scripts/python.exe -m pytest -q
Set-Location frontend
npm run generate:types
npm run build
npx playwright install chromium
npm run test:routes
```

`backend/models` is the only scientific type source. All frozen Case8 subset
models and their actual dependencies are exported through `backend.models`.
`config/openapi.json` and `frontend/src/types/generated/api.d.ts` are generated
artifacts; regenerate them together after changing models/catalog. Validators
enforce local structure and cross-field invariants. Registry membership, real
source identities/hashes, and scientific regressions remain Window 1/2 work.
Local Swagger UI (DOC02) is deferred; no CDN resource is introduced.

Window 1 implements `backend.adapters.Case8AdapterProtocol`. It contains no
implementation, locator, file parser, or solver import. Window 2 can call
`create_app(case8_adapter=fake)` immediately and use
`app.extensions['case8_service']`, independent of Window 1. Missing adapter
calls raise typed 503 FEATURE_NOT_ENABLED. `configure_catalog(catalog, service)`
adds operations before Blueprint binding. Each operation owns its request and
response models, errors and phase. Path fields belong to the request model;
numeric/repeated query parsing is supplied through `Operation.request_parser`
when those operations are implemented, before strict request validation.
This parser receives path values and multi-value query fields; it must reject
duplicates of single-value fields and explicitly convert permitted numeric
strings. Unknown query fields and query overrides of path selectors are
rejected before parsing. SYS01 uses the string-only RegistryQuery contract.

Frontend components are exported from `frontend/src/scientific/index.ts`.
Their public props are fixed for subsequent windows: SnapshotViewer takes
`snapshot`, `field`, and optional `array`; EntropyChart takes `history`;
MetricsPanel takes `collection`; ScientificStatus takes `verification`,
`availability`, and `limitations`; EvidenceLink takes `evidenceId`.
All scientific props reference generated schema types. Window 3 replaces
placeholder internals while retaining these inputs. URL state belongs to
Router, temporary state to Pinia, and loaded results to Vue Query.

No formal CFD directory is read, no scientific source is copied or modified,
no CFD process is launched, and no database/email/account operations exist.
The repository was initialized from the original frozen files on `main`,
then all engineering work was isolated on `phase5/bootstrap`.

`PHASE5_BOOTSTRAP_BASE` names the tested implementation commit. The handoff
records that commit in `HEAD_COMMIT` and is committed afterward as a report-only
change, since a tracked file cannot embed the SHA of its own containing commit.
Start parallel development from the tag; the branch also contains the handoff.
