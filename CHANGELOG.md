# ShockPath Changelog

## V1_SCOPE_FREEZE — 2026-09-30 (Asia/Shanghai)

- Initial project scope frozen: seven V1 modules, P0/P1/P2, scientific claim boundaries, non-goals, data rules, demo story, acceptance and development order.
- No solver modification.
- No experiment or frozen evidence modification.
- No production CFD run.
- Next phase: `DATA_ASSET_INVENTORY` (not started in this freeze).

Future P0 changes must record **old scope / new scope / reason / impact / date** and create an updated freeze/hash. Scientific claim expansion additionally requires new real experimental or theoretical evidence.

## PHASE4_TECHNICAL_FOUNDATION_FREEZE — 2026-10-01 (Asia/Shanghai)

Version: **1.0.1**. Review: `PHASE4_REVIEW=PASS_WITH_MINOR_FIXES`.

Changes:

1. Clarified snapshot_index as strictly user-visible 1-based; the initial recorded snapshot may have snapshot_index=1 and step_index=0.
2. Marked Account Extension as P1 non-blocking, disabled by default; retained MySQL/QQ email/OTP/session/CSRF/AUTH designs and Anonymous Replay.
3. Clarified full-schema-design / vertical-slice-implementation policy, the Case8 schema subset, and contract-defined versus implemented API delivery.
4. Frozen Phase 4 technical foundation documents at 1.0.1 with SHA-256 records in docs/PHASE4_TECHNICAL_FOUNDATION_FREEZE.json and docs/PHASE4_FREEZE_MANIFEST.json.

Impact: NO scientific scope change; NO API semantic redesign; NO architecture redesign; NO new CFD runs; NO scientific asset modification. Phase 0/1/2/3 frozen content and prior freeze files remain unchanged.

The document patch version is 1.0.1; existing application payload schema_version=1.0.0 and /api/v1 remain unchanged. Future contract changes require CHANGELOG, version bump, re-freeze and new hashes; implementation changes that preserve the contract do not require a full Phase 4 re-freeze.

Next phase: `CASE8_FUNCTIONAL_VERTICAL_SLICE` (**not started**). Stop after this freeze and wait for human confirmation.
