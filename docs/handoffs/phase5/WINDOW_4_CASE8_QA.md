WINDOW=4_CASE8_QA
STATUS=READY_WITH_EXPECTED_FAILS
BRANCH=phase5/case8-qa
WORKTREE=D:\code_project\CFD_visiblesystem_qa_w4
BASE_COMMIT=7d73806a436d95adacb9b7d3de5a88c14ad9dcba
HEAD_COMMIT=RESOLVED_BY_TAG_phase5/case8-qa (harness + handoff in one commit)
BASE_TAG=PHASE5_BOOTSTRAP_BASE
SCIENTIFIC_ASSERTIONS=46/46 pass (0 contradictory)
CONTRACT_TESTS_READY=YES (48 merge-ready cases, 0 written against a private reimplementation)
FRONTEND_E2E_READY=YES (12 spec cases authored; pending frontend slice)
FRONTEND_E2E_RUN=playwright:7_pass;11_skipped(declared pending);0_fail;frontend_build=pass
EXPECTED_FAILS=49 (48 WAITING_FOR_IMPLEMENTATION + 1 FOUND_FAILURE)
UNEXPECTED_FAILS=0
CONFIG_COUNT_EXPECTED=4 (verified from L1/L2 evidence)
SNAPSHOT_COUNT_EXPECTED=24 (verified = 4 config x 6 recorded frames)
HISTORY_ROWS_EXPECTED=7648 (verified = 4 config x 1912 accepted steps)
DU_FINAL_EXPECTED=snapshot6,step1912,time0.08 (matched against canonical schedule)
SNAPSHOT_ZERO_ALLOWED=NO (asserted rejected as INVALID_REQUEST, not aliased)
SCIENTIFIC_FILES_MODIFIED=NO
PRODUCTION_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
BLOCKERS=Case8 blueprint (C801-C808, ARRAY01, EVI02/03) and frontend slice not merged into PHASE5_BOOTSTRAP_BASE; 49 merge-gated expectations cannot resolve until they land. One production defect filed (see below).
MERGE_READY=YES
DEFECT_FILED=1 public-DTO locator scrubber absent: ScientificResult.scope.description is unrestricted free text, so an absolute source path can serialize into a public payload; violates contract §1.1 "no absolute path". Reported only; production untouched.
GOLDEN_VALUES=all derived at import time from frozen evidence (L1 repo data/, L2 read-only D:\Paper\passage6, L3 window-level aggregates); no snapshot time hard-coded as T/5; T/5 explicitly asserted false.

Key test files (10):
- tests/verification/case8_facts.py - L1/L2/L3 fact source, single origin of all golden values
- tests/verification/test_case8_scientific_truth.py - 28 golden assertions (configs, counts, D_u final, no-T/5)
- tests/verification/test_semantics.py - cumulative!=increment, E_at!=Pi_at, MISSING!=0, UNKNOWN!=MISSING, statuses
- tests/verification/test_provenance.py - identity/hash/evidence refs + absolute-path leak detector
- tests/verification/test_api_contract.py - snapshot 0/7, unknown config, pagination, array shape, envelopes, evidence, OpenAPI
- tests/verification/conftest.py - real catalog/app fixtures (no private route reimplementation)
- scripts/verification/qa_status.py - emits the JSON status block quoted above
- frontend/tests/case8-acceptance.spec.ts - Entry->Home->Lab->Case8->D_u->Snapshot6->Entropy->Metrics->Evidence->Back
- docs/handoffs/phase5/WINDOW_4_CASE8_QA.md - this report
NOTES=QA ran in an isolated git worktree; the Window 2/3 worktrees and their in-flight files were read only. A stray tests/verification directory briefly created inside the Window 2 worktree was removed and that worktree restored to its prior state.
