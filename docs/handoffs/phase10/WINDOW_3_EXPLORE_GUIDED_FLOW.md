WINDOW=3_EXPLORE_GUIDED_FLOW
STATUS=PASS

SCENES=7/7

S1_ENTROPY=PASS
S2_MECHANISM=PASS
S3_TRIGGER_OUTPUT=PASS
S4_GATE_ALLOCATION=PASS
S5_SPECTRAL=PASS
S6_CROSS_FLOW=PASS
S7_EVIDENCE=PASS

LAB_REUSE=PASS
SCIENTIFIC_DATA_DUPLICATED=NO
URL_STATE=PASS
RETURN_CONTEXT=PASS

BUILD=PASS
TESTS=PASS;109/109 full frontend regression;67/67 final affected-view regression;101/101 W0/W1 contracts
MOCK_IN_PRODUCTION=NO

BRANCH=phase10/explore-ui
BASE=d6280fc;accepted W2 including accepted W0/W1
WORKTREE=C:/Users/t/.codex/worktrees/phase10-explore-ui/CFD_visiblesystem
AUDIT_DATE=2026-10-01;Asia/Shanghai

P03 is one guided container at `/explore?scene=1` through `scene=7`.
CONTENT01 supplies all seven navigation presets; CONTENT02 supplies the active
scene's targets, controls, evidence and limitations. No numerical result JSON
or scientific arrays are embedded in Explore. Only the active scene mounts its
scientific views. The content registry and backend remain unchanged from W2.

S1 reuses EntropyTab and EntropyChart for legal Case8 B_u / D_u histories.
All three cumulative pathways and terminal values come from the recorded 1912
accepted-step histories, with units, time and verification. No frontend
integration, metric recomputation or interpolated spatial frame is introduced.
Guided mode removes scalar/snapshot controls; full Lab retains them. Chart width
is explicitly checked and the rendered budget curves were visually inspected.

S2/S3 reuse the accepted MechanismView and CONTENT03 schematic. S2 explains J,
trigger, normal output and tangential output. S3 retains STRICT_1D / WEAKLY_2D
and OFF / ENABLED states, strict-1D zero tangential output, and the explicit
delta_t gate exclusion. No numerical Near1D graph or optional instantaneous
Case8 overlay is introduced; schematic and numerical evidence stay distinct.

S4 reuses CellAllocationView and AllocationSummary in a shared GateComparisonView
also accessible from full Lab. ALLOC04 supplies the shared min/max colour extent;
ALLOC01/02/03 supply saved cell arrays, budgets, fixed-window definition/counts,
and real inside/outside fractions. Acoustic q_at=0.4, Pressure
q_at=0.31018332312583474 and Ungated q_at=0.03483470441226932 are read from each
real EVI02 configuration, because the generic Gate config-list route is not
delivered. They are not frontend constants. Budget matching remains approximate,
and no best-gate or universal localization verdict is emitted.

S5 is guided mode of the existing SpectralTab. Both complete SPEC02 curves at
q_at=0/.396 remain visible with ell0..16 and a table of recorded Re(lambda)
facts. Modes4/8 receive presentation emphasis. Negative, positive and near-zero
directions remain visible; near-zero means equal at ten displayed decimal places,
not a formal stability threshold or a recalculated shift metric. Full Spectral
Lab retains all four configurations, Modes, Validation and Evidence.

S6 uses CrossFlowView extracted from the existing P07 page, with the real CMP01
D_u/D_u pair fixed in guided mode. Case8 remains FACE_FIELD with separate native
x/y renderers; Cylinder remains ANGULAR_SECTORS plus REGION_SCALAR. Both policies
DESCRIPTIVE_ONLY and NO_UNIFIED_RANKING are visible. Cylinder cumulative2D stays
MISSING without a replacement image. Canonical budgets and the leading recorded
response metrics show units, scope, detector and verification. Verbose definitions
and the complete metric collection remain expandable; full P07 retains its
original selectors and full detail. No common score or browser-derived ratio is
computed.

S7 uses EvidenceDetailView extracted from P09. Only the selected curated EVI02
record loads; no scientific array requests are needed. Method/config/source,
recorded/current hashes, per-asset hashes and verification, UNKNOWN facts,
limitations and freeze boundaries are retained. A real Evidence Detail opens
and returns to the originating Scene. Numerical spectra do not certify the
mechanism schematic or the missing Near1D raw scan.

Previous/Next and scene navigation push only the Scene destination. Direct links,
reload, browser Back, invalid IDs, rapid scene changes and selected Evidence
identity are tested. Full Lab links carry the correct experiment, legal config,
tab, source_scene and an explicit original Scene return payload. Case8 Lab edits,
reload, Mechanism controls, Cross-flow and Evidence returns preserve that context.
Home Start Explore and global Explore now enter Scene1; Home shows IMPLEMENTED.
Lab includes Mechanism Explorer and Explore / Guided Story. No automatic timing
or final homepage styling was added.

Production uses real APIs. Content outages prevent mounting science, scientific
outages show honest ERROR/MISSING/UNSUPPORTED states, and no mock fallback occurs.
The final compiled bundle is scanned for synthetic provider/fixture identifiers.

Validation commands (PowerShell7; frontend commands from frontend/):

```powershell
npm run build
npx playwright test --config playwright.explore.config.ts
npx playwright test --config playwright.explore.config.ts explore-real-api.spec.ts cylinder-crossflow-real-api.spec.ts case8-acceptance.spec.ts
& ./.venv/Scripts/python.exe -m pytest -q tests/window0_phase10_foundation tests/window1_content_api --junitxml=.cache/phase10-window3/content-contract.xml
& ./.venv/Scripts/python.exe -m scripts.verification.phase10_content
git diff --check
```

Full frontend regression passed109/109. Subsequent visual inspection identified
the guided Entropy chart's zero-width container after its full-Lab hint was hidden;
the layout was fixed and the final67 affected-view checks passed. S6 verbose
definitions were also folded into expandable existing views. Final screenshots
were inspected for the actual budget curves, common Gate scale, mixed modal
directions, separate cross-flow renderers and hash boundaries. Content contracts
passed101/101; the content audit passed with seven scenes, zero numerical reads,
zero duplicated numerical data and zero CFD runs.

Initial validation exposed an unsupported generic Gate configs route (replaced
by the already bound EVI02 configs), outage-test envelopes that incorrectly
declared MISSING while asserting ERROR (corrected test input), and a test reading
inside_fraction instead of the actual inside slot (corrected assertion). An
initial parallel full run also timed out on an unchanged Cylinder history view
under source-read contention. The final runner serializes scientific tests with
the same30s expectation/90s test limits and no retry or skipped tests.

Local records: `.cache/phase10-window3/frontend-regression.json` (109 passing),
`playwright.json` (final67 passing), `content-contract.xml` (101 passing),
`production-scan.json`, `source-preservation.json`, and `scene-1.png` through
`scene-7.png`. Durable summary: `WINDOW3_EXPLORE_VALIDATION.json`.
The existing Vite bundle-size advisory remains; compilation succeeded.

No backend, numerical adapter, canonical content, generated contract or scientific
source was edited. Backend verification is scoped to the101 W0/W1 checks and
content audit; the full backend suite was not rerun. Work occurred in the isolated
W3 worktree, with no edits to the original Phase9 checkout and no solver run.

STOP=Window3 complete; no later window started.
