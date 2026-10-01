WINDOW=2_GATE_ALLOCATION
STATUS=PASS
BRANCH=phase6/gate-allocation
BASE_BRANCH=phase5/case8-integration
INPUTS_READ=05_DATA_SCHEMA.md;06_API_CONTRACT.md;docs/handoffs/phase6/WINDOW_0_ALLOCATION_FOUNDATION.md;docs/handoffs/phase6/ALLOCATION_FOUNDATION_DESIGN.md
GATES=3/3
GATE_IDS=Acoustic;Pressure;Ungated;exact;no fourth gate exists
MATCHED_QAT=Acoustic 0.4;Pressure 0.31018332312583474;Ungated 0.03483470441226932;from frozen matched_qat.json only
CELL_FIELD=PASS
REPRESENTATION_TYPE=CELL_FIELD only;never converted to face
LOCATION_TYPE=CARTESIAN_CELL;single [32,128] field;no x-face/y-face pair created
ARRAY_SHAPE=32x128;float64;C-order [y,x];element_count 4096
COORDINATES=cell centers x=(i+.5)/128, y=(j+.5)/32 on [0,1]^2;derived from frozen grid
SEMANTICS=PASS
TIME_SEMANTICS=STATIC + TRAJECTORY_INTEGRATED [0,0.08];1912 accepted steps
MEASURE=cell integrated;includes_time_weights=True;includes_spatial_measure=True;integral_rule=sum(values)=E_at
NORMALIZATION_PRESERVED=YES;sum(Pi_at)=E_at;no extra dx/dy/dt
SHOCK_WINDOW=GATE_CELL_SHOCK_WINDOW;cell-center abs(x_i-x_s(y_j))<=0.08;x_s(y)=0.5+0.0125 sin(8 pi y);not recentered
CELL_CENTERED=YES
TRAJECTORY_INTEGRATED=YES
QAT_INTERPOLATION=FORBIDDEN_AND_REJECTED;only three matched values addressable
GATE_FABRICATION=FORBIDDEN_AND_REJECTED;unknown gate -> UNKNOWN_CONFIG/MISSING
BUDGETS_MODIFIED=NO;three frozen budgets preserved by identity
FACE_CONVERSION=FORBIDDEN_AND_REJECTED;CELL_FIELD has no face variant
INTEGRAL_ABS_ERROR=Acoustic 5.637851296924623e-18;Pressure 3.0357660829594124e-18;Ungated 1.3010426069826053e-18;threshold 1e-10
OUTPUT_SURFACE=GateAllocationAdapter;list_gates;load_allocation_metadata;load_allocation_array;load_mask;load_summary_metrics;describe_allocation
ADAPTER_PROTOCOL_CONFORMANCE=AllocationAdapterProtocol;isinstance PASS
ERROR_SEMANTICS=missing root MISSING;unknown gate MISSING;unsupported experiment UNSUPPORTED;drifted array SOURCE_DATA_DRIFT;no empty success
SCIENTIFIC_FILES_MODIFIED=NO
SOURCE_HASHES_VERIFIED=9/9;Pi_at/entropy x3+matched_qat+analysis_csv+readme unchanged
CFD_RUNS_STARTED=0
FROZEN_CONTRACTS_CHANGED=NO;04/05/06 SHA-256 match Phase4 manifest
API_IMPLEMENTED=NO;no route/adapter-delivery state changed in this window
FRONTEND_CHANGED=NO
FILES_ADDED=backend/adapters/gate_allocation.py;backend/registry/gate_registry.py;backend/registry/gate_evidence.py;tests/window2_gate_allocation/
FILES_CHANGED=backend/adapters/__init__.py;additive export only
TESTS_ADDED=55
TESTS_RESULT=window2 55/55 PASS;allocation-related 158/158 PASS
SCIENTIFIC_SEMANTICS_EVIDENCE=docs/handoffs/phase6/WINDOW_2_ALLOCATION_SEMANTICS.json
MERGE_READY=YES
NEXT=PARALLEL_ALLOCATION_WINDOWS
