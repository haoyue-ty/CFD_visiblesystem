# Cylinder scientific adapter — Window 1 handoff

Branch: `phase8/cylinder-adapter`.
Independent worktree: `D:/code_project/CFD_visiblesystem_phase8_cylinder_adapter`.
Parent baseline: `69a318b65b9378066b9a55e429dfca162cef32af` (`PHASE8_BASE_COMMIT`).

`CylinderAdapter` reads only selected, pinned J2C formal-v2 source assets.
`CylinderService` validates results independently of Flask and accepts a
`CylinderAdapterProtocol` implementation for Window 2 injection. Nothing is
activated in the application and no Flask operation, frontend, frozen document,
Phase4 public model export or saved OpenAPI contract is changed.

The four allocation variants in frozen 05 section 9 are materialized in
`backend.models.cylinder.AllocationResult`. Import that scoped union and
`CylinderAllocationOverview` for Cylinder operations. Existing Phase4/6 exported
models remain untouched. This adds no new wire fields or representations.

| Operation | Scientific service method | Result |
| --- | --- | --- |
| CYL01 | `list_snapshots(config_id)` | `SnapshotIndex` |
| CYL02 | `load_snapshot_metadata(config_id, snapshot_index)` | `FieldSnapshot` |
| CYL03 | `load_field(config_id, snapshot_index, field_id)` | `FieldResponse` |
| CYL04 | `load_entropy_history(config_id, series=None, offset=0, limit=2000)` | `EntropyHistory` |
| CYL05 | `load_scalar_series(config_id, series_id, offset=0, limit=2000)` | `ScalarSeries` |
| CYL06 | `load_allocation_overview(config_id)` | `CylinderAllocationOverview` |
| CYL07 | `load_sectors(config_id)` | frozen `ANGULAR_SECTORS` |
| CYL08 | `load_front_band(config_id)` | frozen `REGION_SCALAR` |
| CYL09 | `load_metrics(config_id, metric_id=None, snapshot_index=None)` | `MetricCollection` |
| ARRAY01 seam | `load_array(result_id, array_id)` | `ScientificArray` |
| Evidence seam | `load_evidence(evidence_id)` / `load_provenance(result_id)` | `EvidenceRecord` / `ResultProvenance` |

History pagination keywords are keyword-only. Limits are 1..5000. Default entropy
history contains the four cumulative entropy channels; the registry declares 35
saved series per configuration, including stage rates and accepted-step increments.
Stage points preserve their accepted interval and stage index; exact stage-state
time is UNKNOWN, rather than falsely assigning the endpoint time to an RK input.
Cumulative and increment points retain the real interval end time. Source row
step 0..9756 maps to canonical completed endpoint 1..9757.

A_u, B_u and D_u are the only registered configurations; C_u is rejected as
422 UNSUPPORTED_COMBINATION before reading a source. Five snapshots use recorded
indices 1..5 and completed steps 0/2439/4878/7318/9757. Real NPZ times are
0/0.4999487547401866/0.9998975094803731/1.5000512452598136/2.

Field selectors are the saved members, for example `radial_interior_pi_at`
and `angular_interior_pi_at`, with native shapes [31,128] and [32,128]. There
are six saved diagnostic quantities per family: pi_bg/pi_aa/pi_at/pi_total/J/
pt_z_norm2. Primitive density/pressure/velocity movie fields are MISSING.
No Cartesian cell projection is made. ARRAY01 descriptors preserve float64,
native shapes and C-order values. Source `face_measure` remains separate from
instantaneous field densities.

All seven geometry members per family are independently registered with their
native shapes and correct units: face_measure, unit_normal_x, unit_normal_y,
x_face, y_face, r_face, theta_face. A field domain's geometry_ref points to its
saved x_face member; other geometry can be obtained through registered identities
`cylinder.{config}.snapshot.{index}.geometry.{family}_{member}` and corresponding
array_id `{family}_{member}`. The adapter's `list_array_refs(result_id)` provides
descriptors only. Full geometry arrays are genuine NPZ members, never a synthesized
Cartesian mesh or a packed mixed-unit array.

Sectors retain bg/aa/at/total, 16 channel values and 17 edges. Edges use a separate
`cylinder.{config}.sectors.geometry` result with radian units. Channel arrays use
model integrated entropy. The source sum check uses rtol 1e-13, atol 1e-14 against
canonical accepted-step terminal E_*_int. Values already include dt, RK weights
1/6,1/6,2/3 and native interior face measures. Fractions use canonical E_at_int;
A/B fractions are NOT_APPLICABLE because the saved denominator is zero.

The front band loads saved shock_at: a trajectory-integrated [0,2] scalar,
interior-only, with a fixed A_u authoritative radial band +/-0.16 restricted to
the unwrapped anchor angular span. Anchors and their recorded hash are checked.
No mask bitmap is invented. D_u fraction is 0.00777687219301986. A/B saved band
values are real zeros; their fractions remain NOT_APPLICABLE. Full cumulative 2D
is a MISSING ResourceSlot without value and has separate missing evidence.
The independent Fig15 rerun remains outside the selected frozen scope.

Fifteen real terminal metrics retain source definitions, units and detectors.
Width readings retain the B/D detector-floor limitation; nominal dr is contextual
resolution, not a numerical uncertainty or error bar. Front RMS is population
standard deviation of eight front radii. HF-RMS is the source's three-point
high-pass after quadratic detrending, normalized by local radial spacing: it is
dimensionless, despite the older general schema example's length shorthand.
High angular energy uses the saved unnormalized rfft definition and length squared.
No metric is recomputed from fields. Nonterminal metric requests are unsupported.

Every scientific result binds nonempty evidence_refs, source assets, pinned hashes,
verification, protocol, definitions, relevant masks and explicit processing.
Results remain VERIFIED_PRODUCTION / VERIFIED_NOT_FROZEN; this adapter does not
promote source scientific verification to FROZEN_VERIFIED. Upstream result hashes
are retained where recorded; other dependencies use the Window 0 recorded
observation hashes. Source/data drift blocks numeric delivery, including cached
history and descriptors and the terminal state dependency of physical metrics.
There is no dependency on the bootstrap worktree at runtime: the selected source
manifest is copied into `data/cylinder/source_manifest.json`, with its original
Window 0 source-map SHA256.

Tests: run `python -m pytest -q tests/window1_cylinder_adapter` from this worktree.
Test corruption is applied only to temporary software fixtures. Source preservation
covers 189 selected/dependency/off-contract audited files by path, SHA256, size and
mtime_ns, and also checks directory member names. No solver module is imported,
no CFD is started, and scientific source files are never written.

The final machine-readable report and regression evidence are saved beside this
handoff. The pre-existing Phase5 raw-byte hash failure also reproduces unchanged
in the bootstrap worktree: Git checkout CRLF/LF normalization differs from the
accepted Windows freeze bytes. This Window does not alter the Phase5 freeze or
its manifest to suppress that baseline failure.
