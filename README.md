# ShockPath V1

ShockPath replays recorded CFD experiments and links every scientific result to its evidence, method, configuration, source hashes and limitations. The integrated application includes Case8, Gate, Entropy Closure, Spectrum, Modal Validation, Cylinder, Mechanism Explorer, seven Explore scenes, Cross-flow Compare and the Evidence Center.

Use PowerShell 7. Python and Node dependencies are pinned in `requirements.lock.txt` and `frontend/package-lock.json`. The scientific source installation must already exist; the application reads it without running a solver. `SCIENTIFIC_DATA_ROOT` selects the read-only source root, with the existing local default defined in backend settings. Missing sources remain missing.

From the repository root, install software dependencies when needed:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
./.venv/Scripts/python.exe -m pip install --no-deps -e .
npm ci --prefix frontend
```

Start the Waitress backend in one terminal:

```powershell
./.venv/Scripts/python.exe -B -m scripts.serve_backend
```

Build and serve the production frontend in another terminal:

```powershell
Set-Location frontend
npm run build
npm run preview -- --port 4173 --strictPort
```

Open `http://127.0.0.1:4173/`, then choose **进入系统**. The backend listens on `127.0.0.1:5000`; Vite preview proxies `/api` to that address. To select another backend, set `API_PROXY_TARGET` for the frontend command. Settings use process environment variables; `.env.example` is a template and is not automatically loaded.

Navigation is Home / Explore / Lab / Evidence. Stable routes are `/`, `/home`, `/explore?scene=1`, `/lab`, `/lab/mechanism`, `/lab/experiments/:experiment_id`, `/cross-flow`, `/evidence`, and `/evidence/:evidence_id`. URL selectors preserve configuration, scene, tab and result return context through refresh and browser history. All six experiment catalog entries open their delivered workspaces. Unsupported selections and loading failures keep explicit unavailable states.

The scientific source, original freeze records and accepted scientific conclusions remain independent of a software functional freeze. Case8 cumulative allocation retains DIAGNOSTIC_RERUN origin; Cylinder retains VERIFIED_NOT_FROZEN. Cross-flow is DESCRIPTIVE_ONLY with NO_UNIFIED_RANKING. Fully-discrete entropy residual is a numerical diagnostic, not an exact entropy identity. Near-1D is a schematic explanation with missing authoritative raw scan.

Known scientific gaps remain explicit:

- Cylinder full-trajectory cumulative 2D Pi_at: MISSING.
- Near-1D authoritative five-epsilon raw evidence: MISSING.
- Spectrum serialized Jacobian/Fourier matrices: MISSING.
- Saved linear/RK3 modal amplitude histories: MISSING; recorded rates and CFD projected amplitude remain separate available observations.

`Verification.canonical_status` supplies the V1 presentation vocabulary. The original `status`, basis and independent data origin remain available for traceability. Original frozen Fact tokens, including known missing facts with reasons, are retained; UNKNOWN is never coerced to false and MISSING is never replaced by zero. Hash fields distinguish data, method, recorded source and current source; transport ETags do not establish scientific provenance. Evidence can remain readable during source drift while affected numerical results reject drifted dependencies. EVI04 exposes controlled asset metadata, never arbitrary local-file contents.

Run the complete existing verification workflow from the repository root:

```powershell
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration capture
./.venv/Scripts/python.exe -B -m pytest -q
npm run build --prefix frontend
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration contracts
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration public
./.venv/Scripts/python.exe -B -m scripts.verification.phase11_integration scan
Set-Location frontend
npx playwright test --config=playwright.phase11.integration.config.ts
```

The existing combined Playwright runner discovers the Phase12 checks, all prior production browser suites, 15 frontend unit checks and explicitly isolated development mock projects. It starts fresh Waitress and Vite preview servers with no reuse, retries=0 and one worker. Production bundles exclude the mock scientific provider. Development fixtures stay behind the DEV boundary. `npm run build` includes `vue-tsc --noEmit`; there is no separate npm typecheck script.

`backend/models` and the operation catalog are the contract source. Regenerate existing artifacts together when an authorized contract seam changes:

```powershell
./.venv/Scripts/python.exe -B -m scripts.export_openapi
npm run generate:types --prefix frontend
```

The contract gate independently exports and validates OpenAPI 3.1, compares runtime/export/committed schema, and regenerates TypeScript types for byte equality. The source preservation gate compares the full source directory's paths, sizes, modification times and SHA-256 with the captured baseline; all audit output belongs to the software workspace.

Phase12 acceptance and functional freeze records are in `docs/handoffs/phase12/`. After FUNCTIONAL_V1_FREEZE, authorized next work is UI and competition polish, presentation, documentation and demo material. No additional scientific experiments or functional scope are implied.
