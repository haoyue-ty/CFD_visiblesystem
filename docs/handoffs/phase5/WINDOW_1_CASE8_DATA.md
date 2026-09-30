WINDOW=1_CASE8_DATA
STATUS=PASS
BRANCH=phase5/case8-data
BASE_COMMIT=7d73806a436d95adacb9b7d3de5a88c14ad9dcba
HEAD_COMMIT=d5ec5f7187e824dd572765efe173e9eedea3966c
MERGE_BASE=PHASE5_BOOTSTRAP_BASE(7d73806)=confirmed_ancestor
CONFIGS=4/4
SNAPSHOTS=24/24
HISTORY_ROWS=A:1912,B:1912,C:1912,D:1912
FINAL_DU=step1912,time0.08
ADAPTER_TESTS=50/50 (full_suite=109/109)
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
API_FILES_MODIFIED=NO
FRONTEND_FILES_MODIFIED=NO
CONTRACT_GAPS=0
BLOCKERS=NONE
MERGE_READY=YES

NOTES:
- snapshot_index 1..6; snapshot1=step0/t0.0; no snapshot_index 0 anywhere.
- Every intermediate step/time read from real NPZ (no interpolation/rounding).
- density/pressure/front read as real members; A/B/C allocation = MISSING (no zero map).
- D_u allocation = registry metadata only, IMPLEMENTATION_DEFERRED.
- VERIFIED_NOT_FROZEN preserved (not promoted); recorded hashes match source.

CHANGED_PATHS:
- backend/adapters/case8.py
- backend/adapters/__init__.py
- backend/registry/case8_source_constants.py
- backend/registry/case8_semantics.py
- backend/registry/case8_evidence.py
- backend/registry/case8_registry.py
- backend/registry/__init__.py
- tests/window1_case8_data/test_case8_adapter.py
- pyproject.toml
- requirements.lock.txt
