WINDOW=0_PHASE8_BOOTSTRAP
STATUS=PASS_WITH_SCOPE_DISCREPANCY
PHASE8_BASE_COMMIT=69a318b65b9378066b9a55e429dfca162cef32af
CURRENT_BRANCH=phase8/bootstrap
WORKTREE=D:/code_project/CFD_visiblesystem_phase8_bootstrap
WORKTREE_CLEAN=YES_AT_CREATION;bootstrap artifacts committed at completion
BASELINE=phase7/spectral-integration;materialized from 161/161 hash-matched accepted files
BASELINE_ANCESTOR=088909baa13733999c75148a315326d6be819f19
ORIGINAL_STATE=phase7/spectral-adapter;dirty accepted working tree and index preserved
ALL_PHASE8_WINDOWS=branch from PHASE8_BASE_COMMIT above
PHASE4_03_04_05_06=UNCHANGED;all four raw SHA256 match freeze
PHASE5=FROZEN_ACCEPTED;original freeze SHA256 match;checkout differs only by line endings
PHASE6=FROZEN_ACCEPTED;freeze SHA256 unchanged
PHASE7=FROZEN_ACCEPTED;accepted working-tree content verified before materialization
CHECKOUT_NORMALIZATION=44 accepted files CRLF/LF only;details in source map
CYLINDER_CONFIGS=A_u,B_u,D_u;C_u=UNSUPPORTED/422
PROTOCOL=Mach3;O-grid;nr32;ntheta128;r=.5..8;stretch3;T2;protocol/driver/raw files checked
SNAPSHOT_IDENTITIES=1..5;completed steps=0,2439,4878,7318,9757;three configs
SNAPSHOT_TIMES=0,0.4999487547401866,0.9998975094803731,1.5000512452598136,2;from NPZ
SNAPSHOT_FIELDS=instantaneous pi_bg/pi_aa/pi_at/pi_total/J/pt_z_norm2;two interior families
FACE_GEOMETRY=stored coordinates,normals,measure;radial31x128;angular32x128
PRIMITIVE_MOVIE=MISSING;final conservative state exists;no five-frame density/pressure promise
SCALAR_HISTORY=9757/config;source step0..9756 -> completed1..9757;real start/end intervals
HISTORY_SEMANTICS=35 series;stage instantaneous,accepted-step increments,cumulative separate
BUDGET_SCOPE=INTERIOR_ONLY;native-face measure;SSP-RK3 weights1/6,1/6,2/3
SECTOR_COUNT=16;BIN_EDGES=17;bg/aa/at/total;already measured and trajectory-integrated
SECTOR_FRACTIONS=per-channel totals;A/B at denominator0 => undefined/UNSUPPORTED,not zeros
FRONT_BAND=fixed A_u authoritative anchors;radial+/-0.16;anchor angular span only;cumulative/interior-only
FRONT_BAND_D_FRACTION=0.00777687219301986;A/B fractions undefined because E_at=0
CUMULATIVE_2D=MISSING
MISSING_SCOPE=selected J2C formal v2 and frozen Phase4/Phase8 contract
MISSING_RECORDS=validated EvidenceRecord,ScientificLimitation,ResourceSlot MISSING;no value
CROSS_FLOW_POLICY=NO_UNIFIED_RANKING;left Case8/right Cylinder;default DESCRIPTIVE_ONLY
COMPARABILITY=localization,HF,detectors,budget scope,masks,geometry,time horizon remain separate
SOURCE_AUDIT=PASS;189 selected/dependency files;before/after SHA256,size,mtime_ns,paths identical
SOURCE_MAP=docs/handoffs/phase8/PHASE8_CYLINDER_SOURCE_MAP.json
TESTS=34/34 PASS;tests/window0_phase8_bootstrap;source write guard included
REPRODUCE=python -m scripts.phase8.audit_cylinder_sources;python -m pytest -q tests/window0_phase8_bootstrap
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
ADAPTER_API_VUE_IMPLEMENTED=NO
CONTRACT_DEVIATIONS=none in delivered scope;source-selection contradiction disclosed
SOURCE_SCOPE_DISCREPANCY=Fig15 independent D_u diagnostic-rerun FREEZE has cumulative2D;77 hashes verified;excluded
NEXT=WINDOW1_WINDOW2_WINDOW3
STOP=bootstrap complete;do not silently adopt Fig15 arrays or expand the frozen contract
