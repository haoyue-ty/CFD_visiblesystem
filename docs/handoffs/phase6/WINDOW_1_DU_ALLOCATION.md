WINDOW=1_DU_ALLOCATION
STATUS=PASS_WITH_FOUNDATION_DEPENDENCY
BRANCH=phase6/case8-du-allocation
BASE=phase5/case8-integration;08679fc
FACE_FIELD=PASS
ARRAY_LOAD=PASS
PROVENANCE=PASS
SCIENTIFIC_FILES_MODIFIED=NO
CFD_RUNS_STARTED=0
TESTS=332/332 isolated pytest PASS;109/109 final focused regression PASS;45 Window1 tests
BLOCKERS=Phase6A backend/models/allocation.py is still untracked and absent from base; merge its foundation first; model/service changes are outside Window1 ownership
MERGE_READY=NO
ADAPTER=backend.adapters.Case8AllocationAdapter;optional AllocationAdapterProtocol
METHODS=describe_allocation;load_allocation_metadata;load_allocation_array;load_mask;load_summary_metrics;load_evidence;load_provenance
RESULT=case8.D_u.allocation;Case8_face_Pi_at_integrated;DIAGNOSTIC_RERUN
SOURCE=Paper/fig/fig_14/Du_spatial_rerun/FREEZE/Pi_at_trajectory_integrated.npz
SOURCE_ASSET=asset_1930484b4ef9
SOURCE_SHA256=a0796191d2d5600916d22ad01163433fe5a71ca7c0daef07054b638dae2f00a5
ARRAYS=pi_at_x_faces[32,129];pi_at_y_faces[32,128];float64;C-order[y,x];x-normal/y-normal
COORDINATES=x-normal:x=i/128,y=(j+.5)/32;y-normal:x=(i+.5)/128,y=j/32;saved x_face/x_cell/y_face loaded verbatim;y_cell not fabricated
TIME=TERMINAL/TRAJECTORY_INTEGRATED [0,.08];1912 accepted steps;SSP-RK3 dt*(stage0/6+stage1/6+2*stage2/3) already included
MEASURE=dy*sum(xfaces)+dx*sum(yfaces);dx=1/128;dy=1/32;x boundaries retained;periodic y seam once
UNITS=model time-integrated face entropy density;budget=model integrated entropy;SI mapping UNKNOWN
SUM=0.002777107932592589;recorded=0.0027771079325925934;absolute_error=4.336808689942018e-18
MISSING=A_u/B_u/C_u:MISSING_SCIENTIFIC_ASSET;unknown IDs distinct;no zero maps;unstored spatial curve MISSING
GUARDS=all 8 selected dependencies hash-pinned and reobserved;SOURCE_DATA_DRIFT/SOURCE_CHANGED_DURING_READ;schema/mask/shape/dtype/finite/closure checks
VERIFICATION=existing FROZEN_VERIFIED diagnostic retained;manifest AVAILABLE_UNVERIFIED retained;no CFD re-certification
SOURCE_PRESERVATION=8 selected dependencies SHA256/size/mtime unchanged during tests
PREREQUISITES=Phase6A model and protocol supplied read-only as working-tree dependencies for validation;no model/service/API/frontend changes committed by Window1
