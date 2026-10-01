PHASE7_SPECTRAL_INTEGRATION=PASS

FOUNDATION=PASS
ADAPTER=PASS
API=PASS
FRONTEND=PASS
EVIDENCE=PASS

MODES=17
QAT_VALUES=4

SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0

DELIVERY=Spectral Lab V1
PHASE=7C;SPECTRAL_INTEGRATION
AUDIT_DATE=2026-10-01;Asia/Shanghai
ROUTE=/lab/experiments/case8?tab=spectral
BLOCKERS=NONE

## Frozen prerequisites

PHASE4_HASH_UNCHANGED=PASS;3/3 current SHA-256 values match the frozen manifest.
PHASE5_FROZEN=PASS;FROZEN_ACCEPTED;freeze record and manifest unchanged.
PHASE6_FROZEN=PASS;FROZEN_ACCEPTED;freeze record unchanged;17/17 selected source dependencies match prior acceptance.

| Phase 4 document | Current SHA-256 |
| --- | --- |
| 04_SYSTEM_ARCHITECTURE.md | 5a7193d4203ecd205f487fc38c2f64d09256388a9cb88f64d7201496ef58e2ea |
| 05_DATA_SCHEMA.md | f61482eb917b81767864eb377a4db0c8b6dcf3e333676c2bd23201c7f0997099 |
| 06_API_CONTRACT.md | c115ef21d4c8ba2170cb888bfd4842ea12fe2c7f66cdf1b0519d08489dd4d9f1 |

Source preservation: all 93 files in the selected Spectral FREEZE tree have identical
pre/post relative names, SHA-256, size and mtime_ns. They also match the preceding
Window 1 source audit. Inventory fingerprint before and after:
`78f4853e1fa9f13a470dc207c2fc6df32e633cd23c3bd9f32e72a16ea40b0ddd`.
The Phase 6 check covers its 17 selected dependencies; this is not a new full-tree
audit of all `D:/Paper/passage6`.

## Complete chain

Scientific source → Adapter → Canonical Model → Flask API → Vue → Evidence = PASS.

The scientific source is read-only
`D:/Paper/passage6/experiments/linear_perturbation_analysis/FREEZE`.
The Window 0 canonical models, Window 1 adapter and pinned spectral registry remain
unchanged. The integrated default application activates the real adapter.

ARRAY01 now resolves exact registered spectral result/array identities through the
spectral adapter. Existing Case8 arrays and Allocation evidence still resolve through
their services. Spectrum envelopes, array envelopes and Evidence identify the
spectral registry/data revisions rather than borrowing the project revision.
Public provenance links now resolve to contextual `evidence.spectral.<result_id>`
records; the original source_asset_ids and per-asset hashes remain intact.

Evidence supplies the matching result/config, method identity, recorded/current
source and data hashes, source observations, freeze manifest reference, verification
and limitations. Unknown creation/verification/normalization metadata stays UNKNOWN.
The manifest's upstream AVAILABLE_UNVERIFIED status is retained; observing its current
hash does not promote its self-verification status.

## Real scientific acceptance

- Spectrum: q_at exactly 0, 0.132, 0.264, 0.396; all 17 ordered modes 0–16 per
  configuration, 68 records total. Every curve point matches both the saved CSV
  and rank-0 complex eigenvalue NPZ; individual point API responses also match.
- Curve: x=mode k, y=Re(lambda). Only recorded samples are supplied, with no
  smoothing, interpolated samples, fitted curve or replacement zeros.
- Eigenmode: all 68 default RIGHT/rank-0 vectors reach Vue through ARRAY01;
  complex128 real/imaginary values match the source exactly, with shape [128,4].
  Existing adapter regression additionally checks saved LEFT/RIGHT ranks and
  primitive profiles. Fourier mode and eigenpair rank remain distinct.
- Missing eigenmode semantics: an absent saved asset produces 404
  MISSING_EIGENMODE; the array produces MISSING_ASSET without numeric data.
  In-memory adapter fault injection and real-provider HTTP fault injection test
  this behavior without changing scientific files. The installed freeze contains
  the saved vectors; no genuine missing source is invented for acceptance.
- Validation: all 24 recorded mode/q_at/epsilon combinations match source rates,
  branch ranks, discrepancies and 33-step CFD histories. The saved rank-1 branches
  for modes 1/4 at q_at=0.396 remain separate from the rank-0 spectral envelope.
  Linear/RK3 amplitude histories remain absent and validation remains PARTIAL.

SCIENTIFIC_ACCEPTANCE=PASS

**Positive entropy production does not imply uniform modal damping.**
The page and its Evidence limitations explicitly state this constraint. The real
browser checks the complete page for `all stable`, `always improved`, and `universal`;
none appear.

Source-observed changes in alpha from q_at=0 to q_at=0.396:

| Mode | Delta Re(lambda) |
| --- | ---: |
| 1 | +0.0012093874912817437 |
| 3 | -0.04282753050763244 |
| 4 | -0.015228538257155755 |
| 8 | +0.3644067519251184 |
| 12 | +0.14151917068121556 |
| 16 | -2.0108359422010835e-12 |

The transverse maximum remains positive at mode 16: 17.739574265850862 at q_at=0
and 17.73957426584885 at q_at=0.396. The separately recorded Case8 D_u cumulative
E_at is positive, 0.0027771079325925934. That entropy budget is a separate source
context, not a matched sample on the spectral base. The frozen spectral base has
zero direct q_at output; no positive base-state entropy value is fabricated.

Integration also separates growth-rate facts from the CFD amplitude plot: their
units differ. Eigenmode axes label Re(v)/Im(v), and no multiplication by lambda is
claimed. Missing array entries cannot become zeros. Independent request guards
keep dataset metadata available; URL selection persists through Evidence and back.

## Validation results

BACKEND=PASS;790/790;0 failed;0 errors;0 skipped.
FOUNDATION_TESTS=PASS;147/147.
ADAPTER_TESTS=PASS;156/156.
SPECTRAL_API_CONTRACT=PASS;34/34.
CONTRACT_REGRESSION=PASS;154/154;Case8 API58+verification API46+Allocation API16+Spectral API34.
SCIENTIFIC_REGRESSION=PASS;527/527;prior scientific190+Spectral foundation147+adapter156+integration34.
REAL_SOURCE_INTEGRATION=PASS;34/34;included in the full backend run.
FRONTEND_BUILD=PASS;vue-tsc and Vite production build;nonblocking large-chunk warning.
FRONTEND_AND_E2E=PASS;71/71;full suite69+array identity/element-count guards2;0 skipped;0 flaky.
OPENAPI=PASS;OpenAPI3.1 validation;exported document equals live application catalog.
GENERATED_TYPES=PASS;independent regeneration is byte-for-byte identical.
PRODUCTION_MOCK_SCAN=PASS;no synthetic provider signatures in production assets.
GIT_DIFF_CHECK=PASS.

Real browser acceptance covers all four configurations and modes 0–16, curve and
eigenmode rendering, recorded linear/CFD rates, explicit missing history, four
contextual Evidence links and return-state restoration. API outage, missing vector,
wrong array identity and truncated array all refuse fabricated charts. Existing
Case8 and Allocation browser tests pass in the same full suite.

Commands were run in PowerShell 7:

```powershell
.venv/Scripts/python.exe -m pytest -q --junitxml=.cache/phase7/pytest.xml
.venv/Scripts/python.exe -m scripts.export_openapi
# From frontend:
npm run generate:types
npm run build
# Isolated ports: API5077; production4377; mock4477
npx playwright test --config=playwright.phase7.config.ts
# Two final negative guards, with PHASE7_REPORT selecting a separate JSON output:
npx playwright test --config=playwright.phase7.config.ts --project=real-api --grep 'real eigenmode rejects'
```

Durable acceptance evidence:
[PHASE7_SPECTRAL_INTEGRATION_EVIDENCE.json](PHASE7_SPECTRAL_INTEGRATION_EVIDENCE.json).
It contains the test counts, freeze hashes, source pre/post inventories and the
observed scientific differences. Raw local execution records are
`.cache/phase7/pytest.xml`, `pytest.log`, `playwright-full.json`,
`playwright-full.log`, `playwright-array-guards.json`,
`playwright-array-guards.log`, `source-before.json`, `source-after.json` and
`preservation.json`. Screenshots are not used as numeric data.

KNOWN_LIMITATIONS=

1. Serialized Fourier matrices are MISSING; no matrix reconstruction is supplied.
2. Validation covers only the saved 24 combinations; missing linear/RK3 amplitude histories remain PARTIAL.
3. Only 32 eigenvector ranks per block/side are saved; raw normalization/phase are UNKNOWN and LEFT localization is MISSING.
4. Scientific scope is the fixed 128×32 common Mach6 discrete base; SI mapping and broader nonlinear/continuum claims remain unsupported.
5. Spectral Evidence requires its current guarded source bundle; unavailable/drifted dependencies are rejected, and upstream manifest self-verification remains AVAILABLE_UNVERIFIED.

NEXT=STOP_AND_REVIEW
