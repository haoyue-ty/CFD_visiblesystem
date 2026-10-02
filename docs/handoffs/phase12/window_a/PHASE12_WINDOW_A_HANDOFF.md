# Phase12 Window A — V1 final integration

```text
WINDOW=PHASE12_A
BASE_HEAD=49f29f1c1a4817640aee757e520692395baf17b2
FINAL_HEAD=d9f2f1b66bf146cf3c42217f8509752f970755a1
WINDOW_A_ACCEPTED_COMMIT=d9f2f1b66bf146cf3c42217f8509752f970755a1
PHASE8_PRESENT=YES
PHASE9_PRESENT=YES
PHASE10_PRESENT=YES
PHASE11_PRESENT=YES
V1_INTEGRATED_CANDIDATE=YES
OPENAPI_SYNC=PASS
TS_TYPES_SYNC=PASS
PRODUCTION_MOCK_SCAN=0
SOURCE_PATH_EXPOSURE=0
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
BACKEND_TESTS=1356 passed; 0 failed; 0 errors; 0 skipped
FRONTEND_UNIT=15 passed
FRONTEND_E2E=202 passed; 167 production real API + 35 isolated DEV mock
FRONTEND_TOTAL=217 passed; 0 failed; 0 skipped; 0 flaky; retries=0
TYPECHECK=PASS
BUILD=PASS
BROWSER_SMOKE=PASS
```

The clean candidate starts from the actual Phase11 final integration commit. Phase8 final `fceb3b6c569cf381b04767da77b4b92418a4b5ed`, Phase9 final `0df633ff6cd9bd939fdbd0eb2b39a3ec0ac7e880`, Phase10 final `004b0e7e8081e5331ed7aa6291b83afdcdc4f45b` and Phase11 final are all actual ancestors. The original Phase9 W1 and its effective cherry-pick have the same stable patch ID; see lineage.json. The primary checkout started clean at the full SHA in repository-audit.json, on phase9/closure-ui. Its branch is preserved.

The 34 individually reviewed OWNED files repair delivered Gate/Spectrum/Modal registry metadata, existing REG01–04 configuration/capability seams, family-driven workspace tabs, explicit unsupported selections, config-disabled Allocation without redirect, canonical verification display, generated contracts and current launch instructions. Case8's legacy Spectral Lab route remains compatible but is explicitly an independent workspace shortcut outside the Case8 capability tablist. Existing scientific views, arrays, methods, registries, source assets and accepted conclusions are unchanged.

Verification adds a derived `canonical_status` with the required nine V1 tokens and keeps the frozen source `status`, basis and separate origin for traceability. DIAGNOSTIC_RERUN remains an origin, never promoted into frozen acceptance. The existing Fact wire tokens, including MISSING with a reason, remain compatible with accepted scientific snapshots; KNOWN/UNKNOWN/NOT_APPLICABLE semantics are unchanged. UNKNOWN is not false, MISSING is not zero, and recorded zero remains a known value. The historical schema QA allows exactly the one approved Verification property, then requires every old schema field to match exactly. The historical source audit removes only the validated derived alias before exact comparison. Strict JSON datetime roundtrip is explicitly tested.

The existing complete pytest and combined Playwright runners were used, with fresh Waitress, production Vite preview and isolated development servers. Build includes vue-tsc. No duplicate test/export workflow or new scientific experiment was added. Completed full-suite XML, JSON, logs and machine gate reports are adjacent. Earlier candidate failures were repaired and the full suites rerun; the accepted reports contain no retries or omissions. The production journey checks page errors, console errors, failed requests (expected aborts excluded) and server failures; separate negative tests inject outages and verify explicit failure.

All seven Explore scenes and the Home/Lab/Mechanism/Case8/Gate/Closure/Spectrum/Modal/Cylinder/Cross-flow/Evidence paths run against production APIs. Quick View, Detail, result return, Explore return, browser history and deep-link refresh remain working. Public asset audit covers all 2,438 SourceAssets and real result/evidence chains, safe EVI04 metadata, no file download route, distinct provenance hashes and all three required missing records. CURRENT=13296, GAPS=11, HISTORY=2173, ALL=15480.

The full scientific directory audit compares 27,843 paths, sizes, mtime_ns and SHA-256; the 5,429,811,970 bytes retain manifest fingerprint `8c9bf82f0e0caa69ce671e057c4202faf42f4b579e92deee94aef7ad6f05ad46`. All output is in the software workspace. No solver was started.

Known gaps remain: Cylinder cumulative2D=MISSING; Near1D authoritative five-epsilon raw=MISSING; Spectrum serialized matrices=MISSING; saved linear/RK3 amplitude histories=MISSING. Cross-flow remains DESCRIPTIVE_ONLY / NO_UNIFIED_RANKING; fully-discrete residual remains a numerical diagnostic, not an exact entropy identity. The existing Vite bundle-size advisory remains a polish consideration, with no build/type errors.

This report follows the accepted implementation commit; Window B must independently validate the committed candidate before functional freeze. No Phase12 final freeze is asserted by this Window A record.
