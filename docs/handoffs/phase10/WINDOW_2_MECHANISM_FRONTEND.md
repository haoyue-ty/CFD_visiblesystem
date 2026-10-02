WINDOW=2_MECHANISM_FRONTEND
STATUS=PASS

MECHANISM_PAGE=PASS
SHARED_MECHANISM_VIEW=PASS
STRICT_1D=PASS
WEAKLY_2D=PASS
TRIGGER_OUTPUT_SEPARATION=PASS
SCHEMATIC_LABEL=PASS
NEAR1D_FAKE_NUMERICS=NO
EVIDENCE=PASS

BUILD=PASS
TESTS=PASS;74/74 full real-API frontend;22/22 final mechanism/route checks;101/101 W0/W1 content checks
MOCK_IN_PRODUCTION=NO

BRANCH=phase10/mechanism-ui
BASE=152e7d562e4233408c8c63f74406ef9e97ef90e6;accepted W1 including accepted W0
WORKTREE=C:/Users/t/.codex/worktrees/phase10-mechanism-ui/CFD_visiblesystem
AUDIT_DATE=2026-10-01;Asia/Shanghai

P05 opens at `/lab/mechanism` from Lab Workspace. `/explore?scene=2` and
`/explore?scene=3` render the same `views/mechanism/MechanismView.vue` used by
P05. CONTENT02 supplies the real scene title/conclusion; CONTENT03 supplies all
11 nodes, 13 directed edges, explanations, evidence references and limitations.
Only drawing coordinates and presentation labels reside in the frontend.
The graph shows the acoustic trigger separately from its two receiving outputs,
and joins background PSD, normal acoustic and tangential output at the
entropy-scaled dissipation combiner, then physical entropy variables.

The dashed TRIGGER node and solid blue OUTPUT nodes have explicit text labels,
keyboard selection and independent explanations. Selecting tangential output
shows exactly: “δ_t does not enter gate, but tangential receiving content affects
output amplitude.” Tangential receiving content connects to tangential output,
bypassing q_at and J. Clicking every registered node is covered against the real
API explanation.

There are exactly two discrete state choices and two q_at choices in P05/S3.
S2 uses node selection and directs state exploration to S3/P05, respecting its
frozen allowed controls. These are marked SCHEMATIC STATE, and no state change
requests numerical data or calculates J, a flux, or dissipation. Strict 1D keeps
the acoustic trigger visible and potentially nonzero while receiving content
is zero and enabled cross-mode output is inactive/zero. Weakly 2D labels
receiving content nonzero and enabled output active, conditional on the acoustic
trigger. Off disables the tangential pathway in either state and leaves the
gate explanation intact. There is no numeric amplitude claim.

Near-1D uses theoretical O(epsilon) action and O(epsilon^2) entropy prose with
the explicit notice: “No authoritative five-epsilon raw numerical scan is
registered.” No epsilon/q_at sliders, numeric input/points, five-point scan,
numerical chart, 3D animation, solver call or dynamic flux evaluation is added.

Every selected node has an Evidence quick action that loads real EVI02 and a
detail link to the existing P09. Theory, implementation and numerical result
scopes are separately explained. Method/source verification in the Spectrum
record remains scoped to that record; it does not upgrade this schematic or
certify Near-1D scaling. P09 shows this mechanism-specific context as well.

State, q_at and selected node are URL state. Lab arrivals return to Lab.
Explore arrivals carry source_scene; the return link restores Scene 2/3 and
current schematic selections. P09 carries the full return target. Browser Back
and reload are verified for scene, state, q_at and node selection.

The content facade is API-only, including development. Network failure, HTTP
503, failed success envelope and non-SCHEMATIC origin show an error with no graph
or synthetic fallback; retry reads the real API. Evidence outage shows its own
error while keeping the schematic available. Scene metadata outage/invalid
identity cannot fabricate an Explore scene.

Validation used PowerShell 7, the existing project Python environment and
Chromium Playwright against the actual backend and Vite production preview.
Full frontend regression covered existing Case8, allocation, spectra, Cylinder,
Cross-flow, evidence and route behavior, including the production mock bundle
audit. After the final tangential receiving-edge routing adjustment, vue-tsc /
Vite build and all 22 mechanism/route checks passed again. No test failed or
skipped. The existing Vite bundle-size advisory remains. Desktop and narrow
screenshots were inspected; the narrow diagram scrolls horizontally.

Commands (from worktree, frontend commands from frontend/):

```powershell
npm run build
npx playwright test --config playwright.mechanism.config.ts
npx playwright test --config playwright.mechanism.config.ts mechanism-real-api.spec.ts routes.spec.ts
& ./.venv/Scripts/python.exe -m pytest -q tests/window0_phase10_foundation tests/window1_content_api --junitxml=.cache/phase10-window2/content-contract.xml
& ./.venv/Scripts/python.exe -m scripts.verification.phase10_content
git diff --check
```

Local execution records: `.cache/phase10-window2/frontend-regression.json`
(74 passing), `playwright.json` (final 22 passing), `targeted-initial.json`
(initial 22 passing), `content-contract.xml` (101 passing),
`mechanism-workspace.png`, `mechanism-narrow.png`. Durable summary:
`WINDOW2_MECHANISM_VALIDATION.json`.

No backend, canonical content registry, numerical adapter, OpenAPI/generated
types, frozen contracts or scientific source was changed. The original dirty
Phase9 working directory was left in place. No CFD run was started. Backend
verification in this window is the 101 W0/W1 checks and content audit; the full
backend suite was not rerun because backend files were unchanged.

Explore delivery is limited to S2/S3. Other Scene IDs can show real metadata
with a delivery note; their interactive views remain outside Window 2. Styling
provides readable functional layout and trigger/output distinction; final UI
polish is not delivered.

STOP=Window 2 complete; no later window started.
