import os,json,csv,re,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
R=Path(r'D:\Paper\passage6');O=Path(r'D:\比赛\数媒\data');S=Path(r'D:\code_project\CFD_visiblesystem')
def j(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
A=j(O/'inventory_inspected.json');H=j(O/'hash_verification.json');V=j(O/'evidence_validation.json');F=j(S/'PROJECT_FREEZE.json')
MH=V['method_source_hash'];METHOD='cross_mode_ec_unified_v1'
B='jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal';C='jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2';L='experiments/linear_perturbation_analysis/FREEZE';G='experiments/gate_ablation/FREEZE';E='experiments/entropy_budget_closure';P='Paper/fig/fig_14/Du_spatial_rerun/FREEZE';M='results/high_order_transfer'
by={x['relative_source_path']:x for x in A}
def aid(path):return by[path]['asset_id']
def ids(paths):return [aid(p) for p in paths if p in by]
# Metadata refinement from exact evidence, never filename identity alone.
for a in A:
    p=a['relative_source_path'];lo=p.lower();ins=a['inspection']
    if a['status']=='AVAILABLE_UNVERIFIED' and 'experiments/linear_perturbation_analysis/' in p and '/FREEZE/' not in p:
        twin=p.replace('experiments/linear_perturbation_analysis/','experiments/linear_perturbation_analysis/FREEZE/',1)
        if twin in by and by[twin]['status']=='FROZEN_VERIFIED' and by[twin]['sha256']==a['sha256']:
            a.update(status='VERIFIED_NOT_FROZEN',verification_status='BYTE_IDENTICAL_TO_EXPLICIT_FROZEN_COUNTERPART',freeze_status='SOURCE_COPY; frozen counterpart separately inventoried',duplicate_of=aid(twin))
    if 'J1_entropy_channel_theory/' in p or 'unified_corrected_method_v3/' in p or p=='solver/fluxes/cross_mode_ec_unified_v1.py':
        a.update(module=['01','07'],method=METHOD,method_hash=MH,evidence_links=['jcp_extension_v1/J1_entropy_channel_theory/J1_IMPLEMENTATION_AUDIT.md','unified_corrected_method_v3/CERTIFICATION_MANIFEST.json'],semantic_meaning='Final-method mechanism, operator definitions and fixed-interface certification; schematic explanation evidence')
    if 'J2D_case7_formal_v3/' in p:
        a.update(case='Case7_Isentropic_Vortex',module=['02','03','07'],method=METHOD,method_hash=MH,reconstruction='first-order',final_time=10,evidence_links=['jcp_extension_v1/J2_entropy_diagnostics/J2D_case7_formal_v3/J2D_V3_RESULT_SUMMARY.md'])
    if '/checkpoint_' in p and a['case']=='Cylinder_external':a['time_granularity']='MULTI_SNAPSHOT'
    if a['case']=='Case8_external':a.update(grid={'nx':128,'ny':32},CFL=.05,final_time=.08,reconstruction='first-order',coordinate_system={'x':[0,1],'y':[0,1]},mask_definition='external production detector; distinct from pathway allocation masks')
    if a['case']=='Cylinder_external':a.update(grid={'nr':32,'ntheta':128},final_time=2,reconstruction='first-order',coordinate_system='stretched polar O-grid, exact geometry in production_manifest.json')
    if a['case'] in ['Case8_external','Cylinder_external'] and '/canonical/' in p:
        a['method']='mixed external reference table; original/proposed rows excluded from final internal comparison'
        a['frontend_ready']='SUMMARY_ONLY';a['frontend_ready_reason']='Select explicit external rows only, retain unknown/missing cells; see Figure17 audit'
    if p==L+'/spectrum/spectral_summary.csv':a.update(q_at=[0,.132,.264,.396],variable=ins['columns'],semantic_meaning='Spectral abscissa alpha=max real eigenvalue for each transverse mode and q_at; mixed-sign delta_alpha',units={'alpha':'inverse model time; no SI conversion established','delta_alpha':'inverse model time','m':'dimensionless mode index','other':'UNKNOWN'})
    if p.startswith(L+'/spectrum/') and p.endswith('.npz'):a['q_at']=[0,.132,.264,.396]
    if p.startswith(L+'/cfd_validation/runs/'):
        a.update(variable=ins['columns'],semantic_meaning='Projected complex modal coefficient and amplitude at 33 accepted endpoints; not full CFD spatial-state trajectory',units={'physical_time':'model time; SI UNKNOWN','modal_amplitude':'normalization defined by left/right eigenvectors','other':'UNKNOWN'},replay_candidate=True)
    if a['status']=='AVAILABLE_UNVERIFIED':
        # Availability is useful to inventory, but is not scientific release verification.
        a['frontend_ready']='NOT_USABLE';a['replay_candidate']=False;a['frontend_ready_reason']='Available, metadata inspected, but identity/hash/semantic release verification not established'
    if a.get('hash_evidence') and any(x['result']=='MISMATCH' for x in a['hash_evidence']):
        a['scientific_notes'].append('Historical recorded source hash drift; current source must not be treated as the exact original executable without review')
        if a['data_format']=='PY':a.update(status='PARTIAL',frontend_ready='NOT_USABLE',replay_candidate=False)
    if a['status'] in ['LEGACY','SUPERSEDED']:a.update(frontend_ready='NOT_USABLE',replay_candidate=False)
for run in V['case8_flow_snapshots']:
    for q in run['snapshots']:
        p=q['path'].replace('\\','/');a=by[p]
        assert q['finite_density_pressure'] and run['endpoint_equals_hash_verified_J2B_state']
        a.update(status='VERIFIED_NOT_FROZEN',verification_status='READONLY_FINITE_FIELDS_PROTOCOL_TIMESTAMPS_AND_BITWISE_TERMINAL_MATCH',freeze_status='NO_UPSTREAM_PER_CHECKPOINT_HASH_FOUND; Phase1 records current source SHA256',frontend_ready='ADAPTER_REQUIRED',requires_postprocess=False,replay_candidate=True,frontend_ready_reason='Saved density, pressure, primitive, front and width already exist; schema/coordinate conversion required',snapshot_time=q['time'],time_granularity='MULTI_SNAPSHOT',scientific_notes=['Six snapshot schedule verified, final conservative state bitwise equal to hash-verified J2B state. Intermediate states not independently re-solved.'],evidence_links=['evidence_validation.json',B+'/J2B_PROTOCOL_LOCK.json',B+'/J2B_STATUS.json'])
    assert len(run['snapshots'])==6
# Explicit summary cross-checks, rather than granting credibility to all nearby files.
def rows(p):
    with (R/p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
external=[]
for root,col,other in [('baseline_production_case8_v2','shock_width_physical','shock_width_metrics.csv'),('baseline_production_cylinder_v1','center_width_physical','centerline_width.csv')]:
    summary=root+'/canonical/'+('case8_external_baseline_summary.csv' if 'case8' in root else 'cylinder_external_baseline_summary.csv')
    rr={x['method']:x for x in rows(summary)};ss={x['method']:x for x in rows(root+'/canonical/'+other)}
    for method in ['roe_hh','hlle','hllemcc','chandrashekar_ec_ev_llf']:
        assert float(rr[method][col])==float(ss[method][col])
        paths=[x['relative_source_path'] for x in A if x['relative_source_path'].startswith(root+'/raw/'+method+'/') and x['data_format'] in ['NPZ','NPY']]
        external.append({'case':'Case8' if 'case8' in root else 'Cylinder','method':method,'width':float(rr[method][col]),'column':col,'summary_asset':aid(summary),'raw_field_asset_ids':ids(paths),'raw_field_file_count':len(paths),'status':'SUMMARY_CROSSCHECK_PASS; raw fields AVAILABLE_UNVERIFIED unless separately hash verified'})
    for pp in [summary,root+'/canonical/'+other]:
        a=by[pp]
        if a['status']=='AVAILABLE_UNVERIFIED':a.update(status='VERIFIED_NOT_FROZEN',verification_status='EXACT_WIDTH_EQUALITY_TO_INDEPENDENT_CANONICAL_TABLE_AND_PROVENANCE_AUDIT',freeze_status='NO_PER_FILE_UPSTREAM_FREEZE_HASH_FOUND')
        a.update(frontend_ready='SUMMARY_ONLY',replay_candidate=True,requires_postprocess=False)
save('external_context_validation.json',external)
missing_defs=[
 ('near1d_raw_epsilon_scan',['01','02'],'Near1D_Mach6','Five epsilon runs 1e-2..1e-6: authoritative raw outputs/configuration/hash/trajectory','No raw five-amplitude production set found; Figure7 CSV explicitly transcribed from manuscript','NO; remove formal numerical near-1D scan from V1 experiment choices until proven'),
 ('near1d_spatial_pi_at',['02','04'],'Near1D_Mach6','Authoritative instantaneous/spatial Pi_at and exact shock-band/amplitude data','Only approximate manuscript-transcribed percentages and amplitude ratios found','NO; optional near-1D evidence extension'),
 ('cylinder_trajectory_spatial_pi_at',['03','06'],'Mach3_Cylinder','Full-trajectory native-face/cell spatial Pi_at map','Five instantaneous faces and 16 cumulative angular bins are present; full spatial trajectory accumulation unavailable','PARTIAL; budget/sector/fixed-band comparison works; full cumulative heatmap cannot be delivered'),
 ('case8_per_step_state',['02','03'],'Case8_Mach6','1912-step full flow-state time series','Six saved flow snapshots per A/B/C/D, not 1912 full states','NO for discrete Replay; cannot promise continuous/per-step field playback'),
 ('case8_per_stage_spatial_fields',['03'],'Case8_Mach6','Saved instantaneous spatial fields at all actual SSP-RK3 stages','Only six endpoint native-face snapshots; stage rates are aggregated in logs','PARTIAL; synchronized ledger/field allowed only at saved endpoints'),
 ('case8_AC_trajectory_maps',['03','06'],'Case8_Mach6','Persisted A_u/C_u full-trajectory spatial channel maps comparable to D_u diagnostic rerun','Only D_u accumulated spatial field located; original A/B/C/D have scalar cumulative histories','NO; A/B q_at-zero identities are proven by logs, C spatial cumulative map cannot be invented'),
 ('persisted_jacobian_fourier_blocks',['05','07'],'Common_Mach6_Zero_Residual_Discrete_Shock','Serialized numerical Jacobian and four-by-17 Fourier matrices','Spectrum/eigenpairs/base/verification and construction code exist; no stored full matrices found','NO; frozen spectra/modes suffice; matrix inspection/reproduction remains unavailable'),
 ('muscl_spatial_pi_at',['02','04'],'MUSCL-MC','Persisted spatial Pi_at and dense trajectory flow fields','Eight final density arrays and summaries exist; shock-window scalar/max production exist without saved Pi map','NO; MUSCL transfer is P1 context, summary and final-density views only')]
missing=[]
for name,mods,case,required,lim,block in missing_defs:
    x={k:'UNKNOWN' for k in A[0] if k not in ['inspection','hash_evidence','duplicate_of','snapshot_time']}
    x.update(asset_id='missing_'+name,module=mods,case=case,experiment=case,status='MISSING',freeze_status='UNKNOWN',verification_status='NOT_FOUND_IN_READONLY_SOURCE_SCAN',frontend_ready='NOT_USABLE',requires_postprocess='UNKNOWN',replay_candidate=False,live_demo_candidate='UNKNOWN',semantic_meaning=required,scientific_notes=[],limitations=[lim],p0_impact=block,absolute_source_path='UNKNOWN',relative_source_path='UNKNOWN',file_size='UNKNOWN',sha256='UNKNOWN',evidence_links=['source_tree_before.json'])
    missing.append(x)
A+=missing
byid={a['asset_id']:a for a in A}
module_defs=[
 ('01','Mechanism Explorer',['Final flux/operator identity','J/gate and output decomposition','Strict-1D/near-1D conditions'],['solver/fluxes/cross_mode_ec_unified_v1.py','jcp_extension_v1/J1_entropy_channel_theory/J1_IMPLEMENTATION_AUDIT.md','jcp_extension_v1/J2_entropy_diagnostics/J2A_DIAGNOSTIC_DESIGN.md'],['missing_near1d_raw_epsilon_scan'],['Verified small interface-state table; illustrative schematic must be labelled']),
 ('02','CFD Experiment Lab',['Case8 configurations + field snapshots + temporal metadata','Available real case/configuration registry'],[B+'/J2B_PROTOCOL_LOCK.json',B+'/runs/case8_D_u/final_state.npz',C+'/J2C_V2_PROTOCOL_LOCK.json',E+'/config.json',L+'/config.json'],['missing_near1d_raw_epsilon_scan','missing_case8_per_step_state'],['MUSCL transfer','external reference fields after identity audit','future small Live demo']),
 ('03','Entropy Ledger',['E_bg/E_aa/E_at per accepted step','Instantaneous spatial rates at saved times','Case7 G+D and fully-discrete residual'],[B+'/runs/case8_D_u/stage_weighted_history.csv',B+'/runs/case8_D_u/snapshots/native_faces_step_001912.npz',E+'/outputs/Du_cfl_005/stage_closure.csv',E+'/outputs/Du_cfl_005/step_closure.csv'],['missing_case8_per_stage_spatial_fields','missing_cylinder_trajectory_spatial_pi_at'],['D_u frozen accumulated spatial map','B_u zero-channel and D_u CFL sequence']),
 ('04','Allocation Explorer',['Matched gate q_at and summary','Cumulative cell maps','Exact fixed cell window and sum convention'],[G+'/gate_ablation_analysis.csv',G+'/calibration_snapshot/matched_qat.json',G+'/results_snapshot/Acoustic/Pi_at.npy',G+'/results_snapshot/Pressure/Pi_at.npy',G+'/results_snapshot/Ungated/Pi_at.npy'],[],['qat_sweep; not arbitrary interpolation']),
 ('05','Spectral Lab',['Common zero-residual base','68 alpha records','Selected leading modes and fixed mask','24 nonlinear validation histories'],[L+'/base_state/base_state.npz',L+'/spectrum/spectral_summary.csv',L+'/spectrum/right_eigenvectors.npz',L+'/spectrum/left_eigenvectors.npz',L+'/spectrum/shock_mask.json',L+'/cfd_validation/validation_summary.csv'],['missing_persisted_jacobian_fourier_blocks'],['Full 512 eigenvalues each block; top32 eigenvectors; early-time Fig13 amplitude playback']),
 ('06','Cross-flow Compare',['Case8/Cylinder budgets and metric provenance','Distinct spatial masks','Cylinder cumulative sectors and fixed-band scalar'],[B+'/J2B_CHANNEL_BUDGET.csv',C+'/J2C_V2_CHANNEL_BUDGET.csv',C+'/runs/cylinder_D_u/spatial_cumulative.npz',C+'/analysis/causal_values.json',P+'/Pi_at_trajectory_integrated.npz'],['missing_cylinder_trajectory_spatial_pi_at'],['Four-method external width context; no universal ranking']),
 ('07','Reproducibility Center',['Method SHA/config/grid/integrator','Source indices, recorded freeze hashes and observed verification status'],['final_corrected_evidence_freeze_v1/FINAL_EVIDENCE_MANIFEST.json',L+'/SHA256_MANIFEST.json',G+'/checksums.txt',E+'/FREEZE/FREEZE_MANIFEST.json',B+'/provenance/result_hashes.csv',C+'/provenance/result_hashes.csv'],['missing_near1d_raw_epsilon_scan','missing_persisted_jacobian_fourier_blocks'],['Current-vs-historical source drift table; missing hashes remain visible'])]
modules=[]
for num,name,req,paths,gaps,opt in module_defs:
    if num=='02':
        paths=paths+[q['path'].replace('\\','/') for run in V['case8_flow_snapshots'] for q in run['snapshots']]
    for p in paths:
        if p in by and num not in by[p]['module']:by[p]['module'].append(num)
    modules.append({'module_id':num,'name':name,'REQUIRED_ASSETS':req,'FOUND_ASSETS':ids(paths),'MISSING_ASSETS':gaps,'OPTIONAL_ASSETS':opt,'all_related_asset_ids':[a['asset_id'] for a in A if num in a['module']]})
semantics=[
 ('Pi_at_instantaneous','Pi_at instantaneous','0.5*q_at*J*||P_t z||² at one face/state; unweighted rate','endpoint native-face maps; not actual stored RK-stage trajectories','instantaneous rate in model normalization; SI UNKNOWN',B+'/runs/case8_D_u/snapshots/native_faces_step_001912.npz','Do not call accumulated maps instantaneous'),
 ('Pi_at_stage_weighted','Pi_at stage-weighted','dt*(dotE_s0/6+dotE_s1/6+2*dotE_s2/3); may be domain/region aggregate','PER_STEP records with three stage aggregates','entropy-production increment in model normalization; SI UNKNOWN',B+'/runs/case8_D_u/stage_weighted_history.csv','Stage-weighted CSV has one row per step; not raw spatial stage fields'),
 ('Gate_cell_Pi_at_integrated','Gate trajectory-integrated Pi_at','Cell allocation already includes native face measure and RK/time integration; sum(array)=E_at','32x128 [y,x] cumulative cells','model integrated entropy; SI UNKNOWN',G+'/README.md','No extra dx*dy or dt; pressure/ungated are recorded gate variants'),
 ('Case8_face_Pi_at_integrated','Case8 D_u trajectory-integrated Pi_at','Sum of dt*RK weights of face rate; E_at=dy*sum(x_faces)+dx*sum(y_faces)','32x129 x-faces +32x128 y-faces','time-integrated face rate; SI UNKNOWN',P+'/rerun_provenance.md','Existing DIAGNOSTIC_RERUN, not original production output; derived cell average is not authoritative integral'),
 ('E_at','E_at','Sum of accepted-step channel increments over trajectory; fixed face/boundary scope','Scalar or PER_STEP cumulative','model integrated entropy; SI UNKNOWN',B+'/J2B_PROTOCOL_LOCK.json','Cylinder primary budget is interior-only; compare scopes explicitly'),
 ('allocation_fraction','Allocation fraction f_at','E_at/(E_bg+E_aa+E_at)','cumulative budget fraction','dimensionless',G+'/gate_ablation_analysis.csv','Not shock localization; zero denominator must be handled explicitly'),
 ('gate_shock_window_fraction','Gate cell-centered shock-window fraction','sum(saved cell allocation in |x_i-x_s(y_j)|<=.08)/E_at; x_s=.5+.0125*sin(8*pi*y)','fixed prescribed initial-front window','dimensionless',G+'/README.md','Cell mask; cannot merge with J2 native-face percentage'),
 ('case8_J2_face_localization','Case8 J2 face-based shock localization','RK/time/face-measure weighted native x/y face production in prescribed +/- .08 front window / trajectory E_at','native-face fixed geometry; cumulative','dimensionless',B+'/J2B_PROTOCOL_LOCK.json','Face coordinates and boundary scope differ from gate cells; follow enumerator, do not infer from labels'),
 ('cylinder_front_band_fraction','Cylinder cumulative front-band fraction','shock_at / sum(channel_at) from spatial_cumulative.npz; fixed A_u authoritative anchors +/- .16 radial band','16 cumulative angular bins plus scalar band; interior-only','dimensionless',C+'/J2C_V2_PROTOCOL_LOCK.json','Audit corrected semantic label: cumulative, not final-rate; not directly ranked against Case8'),
 ('cylinder_angular_fraction','Cylinder angular allocation','channel_at[bin] / E_at_int; bins partition theta [-pi,pi] into16','cumulative stage/time/face weighting','dimensionless',C+'/runs/cylinder_D_u/spatial_cumulative.npz','16 bins are not a full spatial Pi_at heatmap'),
 ('spectral_abscissa','Spectral abscissa alpha','max(Re(lambda)) over 512 eigenvalues of each common-base Fourier block','STATIC; 4 q_at x17 modes','inverse model time',L+'/spectrum/spectral_summary.csv','Alpha>0 is allowed; q_at shifts have mixed signs; m=16 max is essentially unchanged'),
 ('growth_rate','Growth rate','sigma_LIN=Re(lambda); sigma_RK3=log|R(dt*lambda)|/dt; sigma_CFD=OLS slope(log projected amplitude)','33 endpoints, common steps0..32; 24 runs','inverse model time',L+'/cfd_validation/validation_summary.csv','Not interchangeable with envelope alpha; common early window only; relative error is a fraction'),
 ('case8_front_RMS','Case8 front RMS','RMS of p50 detected front displacement about its mean','y-row front; checkpoint/terminal','model length; SI UNKNOWN','solver/diagnostics/flagship_cross_modal_case8.py','Not transverse velocity RMS or growth rate'),
 ('case8_HF','Case8 high-k metric','sum(|rfft(signal)/N|²) for k>seed mode4; fraction divides by sum(k>=1 energy)','front-displacement or transverse signal must be identified','signal amplitude squared; SI UNKNOWN','solver/diagnostics/flagship_cross_modal_case8.py','front_high_k_energy, transverse_high_k_energy and fraction must remain separate'),
 ('cylinder_HF','Cylinder HF-RMS/high angular energy','Saved cylinder front high-pass RMS and angular spectral energy from authoritative detector','curved-front angular samples','model length / length²; SI UNKNOWN','solver/diagnostics/cylinder.py','Not the Case8 normalized k>4 statistic; no common colourbar without mapping'),
 ('case8_width','Case8 shock width','Mean row-local pressure p10-p90 crossing distance anchored to expected p50 front','row widths and summary','model length; cells only when divided by declared dx','solver/diagnostics/flagship_cross_modal_case8.py','physical vs cell-normalized labels must differ; MUSCL is a different protocol'),
 ('cylinder_width','Cylinder centerline/front width','p10-p90 crossing distances along radial bow-front detector; centerline and front mean distinct','O-grid detector/terminal','model length; nominal cell normalization separate','Paper/fig/fig_17/data_audit.md','B/D and several external values detector limited; nominal dr=.234375 is not an error bar'),
 ('closure_SD','Semi-discrete closure','G(U)=entropy-variable contraction of actual FV RHS; D(U)=unique-face observer production; R_SD=G+D','PER_STAGE','model entropy rate; eps_SD dimensionless',E+'/FREEZE/frozen_experiment_report.md','Measured floating-point closure is not a fully-discrete identity'),
 ('closure_time','Fully discrete residual R(T)','DeltaS(T)+E_obs(T); actual state entropy change plus weighted trajectory production','PER_STEP / terminal refinement','model entropy; SI UNKNOWN',E+'/outputs/Du_cfl_005/step_closure.csv','Sum E_*_step if drawing cumulative channels; E_*_step is not itself cumulative; no recalculation performed here')]
sem=[{'metric_id':id,'label':label,'definition':d,'scope':scope,'units':u,'source':src,'constraint':note,'source_asset_ids':ids([src])} for id,label,d,scope,u,src,note in semantics]
dependency=[
 {'chain':['actual accepted SSP-RK3 stage state','unchanged FV RHS + entropy-variable contraction G','unique-face channel observer D_bg/D_aa/D_at','raw stage_closure.csv','step RK weights(1/6,1/6,2/3) and dt','step_closure.csv and terminal R(T)','temporal refinement summary'],'evidence':ids([E+'/outputs/Du_cfl_005/stage_closure.csv',E+'/outputs/Du_cfl_005/step_closure.csv',E+'/temporal_refinement_summary.csv']),'missing':['saved full stage state fields']},
 {'chain':['Gate face observer at every stage','face-to-cell allocation with measure','dt/RK accumulation','Pi_at.npy','fixed cell shock window','gate_ablation_analysis.csv'],'evidence':ids([G+'/results_snapshot/Acoustic/Pi_at.npy',G+'/gate_ablation_analysis.csv']),'missing':[]},
 {'chain':['Case8 formal stage observer','aggregated step histories + six instantaneous face maps','existing D_u DIAGNOSTIC_RERUN adds accumulator','Pi_at_trajectory_integrated native-face arrays','fixed native-face localization'],'evidence':ids([B+'/runs/case8_D_u/stage_weighted_history.csv',P+'/Pi_at_trajectory_integrated.npz',P+'/verification_report.json']),'missing':['original full trajectory spatial maps for other configurations']},
 {'chain':['Cylinder native interior radial/angular faces at stages','time/RK/face-measure weighted bins and fixed-region sums','spatial_cumulative.npz','sector fractions and fixed-band localization'],'evidence':ids([C+'/runs/cylinder_D_u/spatial_cumulative.npz',C+'/runs/cylinder_D_u/run_result.json']),'missing':['full trajectory per-face/cell spatial accumulation map']},
 {'chain':['common zero-residual base','central finite-difference numerical Jacobian construction','Fourier reduction','eigenvalues and left/right eigenvectors','spectral abscissa and selected branches','24 pre-registered nonlinear runs','projected modal histories and fitted growth rates'],'evidence':ids([L+'/base_state/base_state.npz',L+'/jacobian/fourier_reduction_audit.csv',L+'/spectrum/eigenvalues.npz',L+'/spectrum/right_eigenvectors.npz',L+'/cfd_validation/validation_summary.csv']),'missing':['serialized Jacobian/Fourier matrices'],'note':'Construction code and audits exist; matrices were not regenerated'}]
replay=[
 {'case':'Case8 production','classification':'GOOD_CANDIDATE','time_support':'6 actual flow/instantaneous-face snapshots per configuration; 1912 accepted-step scalar histories','evidence':ids([B+'/runs/case8_D_u/stage_weighted_history.csv',B+'/runs/case8_D_u/final_state.npz']),'constraint':'Discrete snapshot slider; no per-step spatial trajectory; snapshots are VERIFIED_NOT_FROZEN with exact terminal match'},
 {'case':'Gate ablation','classification':'GOOD_CANDIDATE','time_support':'STATIC trajectory-integrated maps + terminal metrics; no saved map time series','evidence':ids([G+'/gate_ablation_analysis.csv',G+'/results_snapshot/Acoustic/Pi_at.npy']),'constraint':'Gate/config selection; do not animate cumulative map as instantaneous evolution'},
 {'case':'Entropy closure','classification':'GOOD_CANDIDATE','time_support':'PER_STAGE and PER_STEP scalar logs for five runs','evidence':ids([E+'/outputs/Du_cfl_005/stage_closure.csv',E+'/outputs/Du_cfl_005/step_closure.csv']),'constraint':'Stage-level diagnostic timeline, not full spatial-stage CFD replay'},
 {'case':'Spectrum','classification':'GOOD_CANDIDATE','time_support':'STATIC 68 combinations','evidence':ids([L+'/spectrum/spectral_summary.csv']),'constraint':'Only four recorded q_at; no continuous predicted spectrum'},
 {'case':'Eigenmodes','classification':'GOOD_CANDIDATE','time_support':'STATIC complex modes and leading primitive profiles','evidence':ids([L+'/spectrum/right_eigenvectors.npz',L+'/spectrum/leading_primitive_amplitude_profiles.npz']),'constraint':'Any phase sweep is eigenmode illustration, not stored time evolution; 32 eigenvectors per block'},
 {'case':'Fig13 validation','classification':'GOOD_CANDIDATE','time_support':'24 time-series of33 points each','evidence':ids([L+'/cfd_validation/validation_summary.csv']),'constraint':'Projected amplitude playback over common early window, no spatial field movie'},
 {'case':'Cylinder','classification':'POSSIBLE','time_support':'5 instantaneous-face checkpoints per A/B/D; 9757-step scalar histories; 16 cumulative sectors','evidence':ids([C+'/runs/cylinder_D_u/stage_weighted_history.csv',C+'/runs/cylinder_D_u/spatial_cumulative.npz']),'constraint':'Full cumulative spatial heatmap missing; use sectors/band/metrics and label interior-only'}]
live=[
 {'case':'small periodic vortex / entropy observer','classification':'POSSIBLE','reason':'Existing Cartesian periodic first-order path and observer; production128² T10 has3451..27603 steps. Small grid/short time may fit after independent runtime/identity qualification. No run started.','source':E+'/run_entropy_budget_closure.py'},
 {'case':'small Case8','classification':'POSSIBLE','reason':'Existing128x32 Cartesian driver; original1912 steps, saved D_u observer run wall time~378s. Smaller grid/shorter T needs separate protocol approval and performance measurement; not scientifically equivalent production.','source':B+'/runs/case8_D_u/run_result.json'},
 {'case':'three matched-budget gates','classification':'NOT_RECOMMENDED','reason':'Frozen matched q_at values depend on128x32,T=.08 and1912 steps; changing grid/time invalidates matched-budget calibration. Use Replay.','source':G+'/MANIFEST.md'},
 {'case':'common-base Jacobian + Fourier spectrum','classification':'NOT_RECOMMENDED','reason':'Base Newton solve, finite-difference columns and68 complex512x512 eigensystems; unsuitable live browser generation. Use frozen eigensystem.','source':L+'/config.json'},
 {'case':'short nonlinear selected modal validation','classification':'POSSIBLE','reason':'Only32 accepted steps but requires exact common base, selected complex left/right modes, perturbation normalization and positive states; timing/packaging unverified.','source':L+'/scripts/cfd_validation.py'},
 {'case':'Mach3 Cylinder','classification':'NOT_RECOMMENDED','reason':'Stretched curvilinear32x128 O-grid and9757 steps; interior-face/boundary scope and detector limitations require protocol control; Replay has sufficient summaries.','source':C+'/J2C_V2_PROTOCOL_LOCK.json'},
 {'case':'Near1D epsilon scan','classification':'UNKNOWN','reason':'Five-amplitude raw protocol and source identity not proven. Quirk single weak perturbation cannot replace it.','source':'Paper/fig/fig_7/README.md'},
 {'case':'MUSCL smooth/shock transfer','classification':'NOT_RECOMMENDED','reason':'Limiter/reconstruction/positivity protocol; vortex64²..256² with3448..13805 steps and prior interrupted256² attempts; production scale costly.','source':M+'/experiment2_freeze/EXPERIMENT2_FREEZE_README.md'}]
p0states=['SUPPORTED','SUPPORTED_WITH_ADAPTER','PARTIALLY_SUPPORTED','SUPPORTED_WITH_ADAPTER','SUPPORTED_WITH_ADAPTER','PARTIALLY_SUPPORTED','SUPPORTED_WITH_ADAPTER','SUPPORTED_WITH_ADAPTER','SUPPORTED_WITH_ADAPTER','SUPPORTED_WITH_ADAPTER']
p0modules=['01','02','03','04','05','06','07','07','01/04/05/06/07','02/03/05/07']
p0why=[
 'Final mechanism identity/theory source present; explanation and schematic supported. Formal near-1D numerical scan withheld.',
 'A/B/C/D configs, six genuine density/pressure/front checkpoints each and1912-step scalar histories; loader schema conversion required.',
 'Budget logs and Case7 raw-stage closure are complete; spatial synchronization limited to saved endpoints. Dense per-stage/step flow fields missing.',
 'Three hash-matched cumulative cell arrays and matched parameters/metrics/window definitions; adapter required.',
 '68 alpha rows,512 eigenvalues each,32 left/right eigenvectors per block, fixed mask and24x33 histories; adapter/complex mode decoding required.',
 'Budgets, widths, RMS, instantaneous faces and16 cumulative sectors exist. Cylinder full-trajectory spatial Pi_at map unavailable; use labelled sector/fixed-band comparison.',
 'Scope/method freeze hashes and key experiment manifests checked. Source drift and unavailable hashes must remain visible; archived code required for exact replay execution.',
 'Real sources indexed with independent shape/header/time/hash metadata. No loader is implemented in Phase1; frozen/default release asset list can be chosen from evidence.',
 'Frozen mechanism→gate→spectrum→cross-flow→reproducibility story has minimal real-data support; near-1D/cumulative-cylinder map excluded.',
 'Case/config/time availability can be browsed from explicit metadata; unsupported choices must remain unavailable.']
p0=[{'p0_id':f'P0-{i+1:02}','feature':name,'module':p0modules[i],'status':p0states[i],'p0_blocker':False,'reason':p0why[i]} for i,name in enumerate(F['p0_modules'])]
support=[]
for i,x in enumerate(p0):
    mod=modules[min(i,6)] if i<7 else modules[6 if i==7 else (0 if i==8 else 1)]
    if i>=7:
        chosen=range(7) if i==7 else ([0,3,4,5,6] if i==8 else [1,2,4,6])
        mod={'REQUIRED_ASSETS':list(dict.fromkeys(q for n in chosen for q in modules[n]['REQUIRED_ASSETS'])),'FOUND_ASSETS':list(dict.fromkeys(q for n in chosen for q in modules[n]['FOUND_ASSETS']))}
    support.append({**x,'required_data':mod['REQUIRED_ASSETS'],'asset_ids':mod['FOUND_ASSETS'],'asset_statuses':{q:byid[q]['status'] for q in mod['FOUND_ASSETS']},'frontend_readiness':'ADAPTER_REQUIRED' if x['status']=='SUPPORTED_WITH_ADAPTER' else ('SUMMARY_ONLY / schematic' if i==0 else 'ADAPTER_REQUIRED / limited temporal/spatial support')})
gaps=[
 'Near1D Mach6五档ε的权威raw输出、配置、method/hash与精确空间/振幅指标未找到；Figure7表来自论文抄录，不能当正式数据。',
 'Cylinder full-trajectory空间Pi_at累计场缺失；已有16角向累计分箱及固定band标量，不是完整场。',
 'Case8只有6个真实流场/瞬时face快照；缺1912步完整空间轨迹与全部RK stage场，Ledger同步受限。',
 '原始Case8其他配置的完整轨迹累计空间通道图未找到；近期冻结诊断重跑仅覆盖D_u。',
 'Serialized Jacobian/Fourier blocks未找到；MUSCL只存终态密度和summary，缺空间Pi_at；当前部分driver/observer历史hash漂移需保留。']
constraints=[
 'Time slider只在真实已存时间点播放：Case8六帧，Cylinder五个瞬时face；Gate累计图和谱数据STATIC，不能暗示实时轨迹。',
 '严格分开Gate cell累计分配、Case8 native-face累计率积分、Cylinder interior-only sector/band口径；不得重复乘dt/面积或统一排名。',
 'Near1D五档scan论文抄录数值不进入正式展示；Quirk单次弱扰动和Fourier验证epsilon不能替代该scan。',
 '参数只选已运行组合：A/B/C/D、三种校准gate、四档q_at、既存CFL/ε；谱位移与宏观响应非单调，不能插值成新科研结果。',
 '保留method/hash/config/掩膜/模型单位与验证状态；D_u不是通用更优解，Cylinder宽度受检测器限制；Live仅候选，本阶段未运行。']
timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
counts=Counter(a['status'] for a in A)
timeassets=[a for a in A if a['time_granularity'] in ['PER_STAGE','PER_STEP','MULTI_SNAPSHOT'] and a['data_format']=='CSV' and isinstance(a['shape'],list) and a['shape'][0]>1 and a['status'] in ['FROZEN_VERIFIED','VERIFIED_NOT_FROZEN','DERIVED_VERIFIED'] and a['frontend_ready']!='NOT_USABLE']
summary={'DATA_ASSET_INVENTORY':'PASS','SCIENTIFIC_FILES_MODIFIED':'NO','CFD_RUNS_STARTED':0,'ASSET_COUNT':len(A),'EXISTING_FILE_ASSET_COUNT':len(A)-len(missing),'FROZEN_VERIFIED_COUNT':counts['FROZEN_VERIFIED'],'LEGACY_COUNT':counts['LEGACY']+counts['SUPERSEDED'],'LEGACY_STATUS_COUNT':counts['LEGACY'],'SUPERSEDED_COUNT':counts['SUPERSEDED'],'MISSING_ASSET_COUNT':len(missing),'P0_SUPPORTED_COUNT':sum(x['status'] in ['SUPPORTED','SUPPORTED_WITH_ADAPTER'] for x in p0),'P0_PARTIAL_COUNT':sum(x['status']=='PARTIALLY_SUPPORTED' for x in p0),'P0_BLOCKED_COUNT':sum(x['status']=='BLOCKED' for x in p0),'TIME_SERIES_ASSET_COUNT':len(timeassets),'REPLAY_CANDIDATE_COUNT':len(replay),'LIVE_DEMO_CANDIDATE_COUNT':sum(x['classification'] in ['GOOD_CANDIDATE','POSSIBLE'] for x in live),'REPLAY_FILE_ASSET_COUNT':sum(a['replay_candidate'] is True for a in A),'INVENTORY_DOC':str(O/'01_DATA_ASSET_INVENTORY.md'),'INVENTORY_JSON':str(O/'data_asset_inventory.json'),'NEXT_PHASE':'PRD','NEXT_PHASE_STARTED':False,'TOP_5_DATA_GAPS':gaps,'TOP_5_PRD_CONSTRAINTS':constraints,'STATUS_COUNTS':dict(counts),'TIMESTAMP':timestamp}
inventory={'schema_version':'ShockPath_DATA_ASSET_INVENTORY_v1','phase':'PHASE1_DATA_ASSET_INVENTORY','timestamp':timestamp,'scope_version':F['freeze_version'],'source_root':str(R),'output_root':str(O),'software_root':str(S),'safety':{'read_only_source':True,'scientific_files_modified':False,'cfd_runs_started':0,'solver_imports_executed':0,'large_arrays_copied':False},'summary':summary,'identity':{'method':METHOD,'method_sha256':MH,'scope_freeze_sha256':F['scope_sha256'],'rules':['Path and shape are not method identity','Recorded hashes are checked rather than assumed','Inspection verifies metadata and selected existing checks, not all science','Figure7 manuscript transcriptions excluded','Historical source drift is recorded without repair']},'source_scan':{'all_file_count':len(j(O/'source_tree_before.json')),'excluded_dirs':['.venv','.git','__pycache__','.pytest_cache','.superpowers','.workbuddy','node_modules'],'selected_prefixes':'See build_inventory.py; selected canonical roots and named historical/context roots','unselected_files_are_not_claimed_audited':True},'modules':modules,'V1_DATA_SUPPORT_MATRIX':support,'SCIENTIFIC_SEMANTICS_MATRIX':sem,'DATA_DEPENDENCY_MAP':dependency,'REPLAY_CANDIDATES':replay,'LIVE_DEMO_CANDIDATES':live,'P0_BLOCKER_AUDIT':p0,'missing_assets':[a['asset_id'] for a in missing],'external_context':external,'time_series_asset_ids':[a['asset_id'] for a in timeassets],'assets':A}
save('data_asset_inventory.json',inventory)
with (O/'data_asset_inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
    cols=[k for k in A[0] if k not in ['inspection','hash_evidence']]+['inspection','hash_evidence'];w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader()
    for a in A:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in a.items()})
def table(head,rows):
    def c(v):return str(v).replace('|','∣').replace('\n','<br>')
    return '| '+' | '.join(head)+' |\n| '+' | '.join(['---']*len(head))+' |\n'+''.join('| '+' | '.join(c(x) for x in row)+' |\n' for row in rows)
def ref(p):return f'[`{p}`](<{R/p}>)'
doc=f'''# ShockPath — Phase 1 DATA ASSET INVENTORY

审计时间：{timestamp}（Asia/Shanghai）。冻结范围：`V1_SCOPE_FREEZE`。

## 1. Executive Summary

本阶段完成 inventory + evidence mapping，不开展PRD、UI/API、前后端、数据库或CFD。按用户最新指定，所有产物保存在 `{O}`，取代粘贴任务中的默认docs输出位置。科研证据根 `{R}` 全程只读；Phase0四份文件保持原hash。

**DATA_ASSET_INVENTORY=PASS** 表示盘点与缺口审计通过，不表示产品已实现或所有科研证据齐全。P0的数据支持结果为 **{summary['P0_SUPPORTED_COUNT']}项支持（含adapter）、{summary['P0_PARTIAL_COUNT']}项部分支持、0项整体阻塞**。Ledger与Cross-flow仍有明确的空间/时间功能缺口；V1可降级表达，不静默扩充或修改冻结范围。累计Cylinder heatmap及每步同步流场若被要求为强制验收功能，需先解决缺口/范围变更。

既有文件资产{len(A)-len(missing)}个，MISSING逻辑资产{len(missing)}项；一个文件是一项资产，NPZ成员逐个记录shape/dtype，冻结与工作副本可能分别计数。包含配置、科学定义、分析、图形和历史记录，**资产数不等于运行数或可发布数据数**。机器文件列出全部记录和精确路径；本报告突出权威入口与产品约束。

重要发现：Gate累计cell图真实、hash匹配且积分一致；谱68组合及Fig13的24×33真实时序完整；Case8每配置六帧流场且终态与J2B逐值一致。近期已有D_u累计空间场冻结（DIAGNOSTIC_RERUN）可用，本阶段没有重跑。Near1D五档ε图表源自论文抄录，应暂不作为产品数值来源。Cylinder `spatial_cumulative.npz` 是16角向累计箱+band标量，不是full spatial map。

## 2. Source Roots

{table(['Root','Role','Treatment'],[[str(R),'科研证据源','READ-ONLY'],[str(S),'软件主目录和Phase0镜像','只读核验本阶段；未创建软件工程'],[str(R/'ShockPath'),'Phase0原始冻结位置','未修改'],[str(O),'Phase1 inventory输出','仅新增盘点文档、索引、审计/冻结记录与只读检查脚本']])}

优先根：`experiments/entropy_budget_closure`、`experiments/gate_ablation/FREEZE`、`experiments/linear_perturbation_analysis/FREEZE`、J2B Case8、J2C-v2 Cylinder、J2D-v3 Case7、J3/J4/J12、corrected production、MUSCL freeze、外部baseline canonical/raw。历史版本只用于身份排除与追溯，不承接正式主线。

## 3. Scientific Identity Rules

最终方法 `{METHOD}` 的当前source SHA256为 `{MH}`，与要求的身份hash一致。A_u=(13.2,0)、B_u=(3.96,0)、C_u=(13.2,.396)、D_u=(3.96,.396)，是工作参数，不是全局最优。Gate Acoustic=.4、Pressure=.31018332312583474、Ungated=.03483470441226932属于另行冻结的matched gate协议，不能替换D_u=.396。

身份须以配置/来源/协议/hash联合确认。文件名、尺寸、`method_id='D_u'`字符串、论文图号都不足以证明方法一致。外部baseline的`original/proposed`行是历史内部架构，不替换最终A_u/B_u/D_u。源码hash漂移与冻结数值文件hash一致必须分别记录。

状态仅使用任务指定九类。`FROZEN_VERIFIED`表示至少一条既有freeze/result-hash记录与本次逐字节hash一致、格式可读；不等同重新证明全部科学结论。`VERIFIED_NOT_FROZEN`可表示明确字节相同的冻结副本或具体轻量审计通过但未找到上游逐文件冻结记录。Case8 checkpoint另行验证有限density/pressure、时间表和终态逐值相等，不宣称重算验证中间轨迹。`AVAILABLE_UNVERIFIED`默认不列入正式产品可用数据，图像只属figure-only。

## 4. Inventory Method

递归枚举{len(j(O/'source_tree_before.json'))}个文件（排除环境、cache、Git、Superpowers等目录），选取2329个相关文件逐项SHA256、文本/JSON和CSV检查。未选中的大量历史镜像保留在source_tree索引，不宣称逐项审计。NPY使用header；NPZ用ZIP流逐成员读取header，仅读取小标量和选定小型核验数组，未全量解压或复制大型数组。CSV流式获取header、rows、字段类型、时间/参数范围、首末行；不会执行科学实现。所有UNKNOWN显式保留，单位无SI映射不猜。

Phase0 manifest三条hash通过；method source hash通过。既有hash引用审计结果：{H['counts']}。hash引用数含不同manifest对同一文件的重复引用，不等于资产数。详见 `hash_verification.json`；function-level hash只记录为不可用whole-file验证。本阶段不修复任何hash或数据。

轻量核验见 `evidence_validation.json`：3 Gate map sum vs E_at均<1e-10；谱恰为17×4=68组合；Fig13 24条history各33点且时间递增；Case8 4×6 checkpoint时间/有限场及终态相等。外部四方法width和独立canonical表精确相等见 `external_context_validation.json`。

## 5. Module-by-module Inventory

'''
for mod in modules:
    doc+=f"### {mod['module_id']} {mod['name']}\n\nREQUIRED_ASSETS："+'；'.join(mod['REQUIRED_ASSETS'])+'。\n\n'
    doc+=table(['FOUND_ASSETS','Asset ID','Status','Readiness'],[[ref(byid[q]['relative_source_path']),q,byid[q]['status'],byid[q]['frontend_ready']] for q in mod['FOUND_ASSETS']])+'\n'
    doc+='MISSING_ASSETS：'+('、'.join(mod['MISSING_ASSETS']) or '核心已要求资产未发现缺项')+'。\n\nOPTIONAL_ASSETS：'+'；'.join(mod['OPTIONAL_ASSETS'])+'。\n\n'
doc+=f'''### A–I 实验专项核验

**A. Case8主线。** {ref(B+'/J2B_PROTOCOL_LOCK.json')}保存128×32、CFL=.05、T=.08、1912 steps及六快照时刻（0、.01598326359832636、.03200836820083682、.04799163179916318、.06401673640167364、.08）。A/B/C/D都有`final_state.npz`、1912×53的stage_weighted_history、六个native-face endpoint图；其中x-face32×129、y-face32×128。corrected production checkpoints有density/pressure32×128、primitive/conservative32×128×4、front/width32、17-mode谱，已做四组终态与hash-verified J2B逐值一致检查。stage history包含E_bg/E_aa/E_at、三stage dotE/max及scalar front积分，但不包含每步state或每stage空间场。shock width/front RMS/HF分别用已有detector/source定义。

{ref(P+'/rerun_provenance.md')}明确近期D_u数据是**既有诊断重跑**；canonical native-face NPZ及structured NPY已freeze。它不改变production状态；terminal bitwise match、E_at=.0027771079325925934、face积分绝对误差4.337e-18。x/y累计数组需dy/dx积分；derived cell average不能用sum作为E_at。只有终端累计map，没有map时间轴。

**B. Entropy-budget closure。** {ref(E+'/FREEZE/FREEZE_MANIFEST.json')}引用真实raw stage和step文件（不是仅summary）。B_u CFL=.05 zero-channel；D_u CFL=.2/.1/.05/.025，steps为3451/6901/13802/27603，T10、128²、周期一阶。stage_closure shape分别10353/20703/41406/82809×14，B_u41406×14；step_closure rows等于accepted steps、26字段。G、D_bg/D_aa/D_at/D_total、R_SD、eps_SD、R_decomp是stage级；S_n/S_np1/DeltaS与各E_*_step/R_time是step级。报告max eps_SD=3.7427525702529528e-15，B_u D_at=0；R(T)随D_u CFL细化趋近零，全局斜率2.9999942283876795。已有报告的数值解释与raw可追溯，不宣称精确全离散恒等式。closure实验未存空间state trajectory，不能用其他涡实验不同CFL的场假装同步。

**C. Gate ablation。** {ref(G+'/MANIFEST.md')}、calibration_snapshot15行qat_sweep、matched_qat、三组entropy/metrics/Pi_at全部在freeze。Pi_at是float64、32×128、TRAJECTORY_INTEGRATED；entropy.csv/metrics.csv为terminal summary，不能播放其时间轨迹。三组E_at相对匹配误差约1.5216%，不是严格相等。窗口cell中心、固定initial front±.08，前沿内份额读已有analysis而非硬编码；native-face J2窗口另记录。当前积分复核通过，不能二次乘dt/面积。

**D. Near1D Mach6/ε scan。** {ref('Paper/fig/fig_7/README.md')}明确五点E_at抄自DOCX，band百分比与A_D/A_B为约数；local_exponents来自这些印刷数值，global2.006015920不是本阶段核验的raw scan证据。所有fig7 numeric/rendered资产标记AVAILABLE_UNVERIFIED/figure-only/NOT_USABLE。全目录CSV header与路径检索未发现权威五档raw输出、method/config/hash或spatial Pi_at。Quirk单次弱扰动负对照单独列legacy；谱验证ε=1e-4/1e-5/1e-6也不是这五档非线性ε实验。

**E. MUSCL-MC。** {ref(M+'/experiment2_freeze/EXPERIMENT2_FREEZE_README.md')}确认一阶EC/PSD身份不变，primitive MUSCL-MC重构独立协议。Vortex64²/128²/256²，B/D各一组，CFL=.1、T10，6组终态density；Case8 128×32、CFL=.05、T.08，B/D两组终态density。raw CSV有rho L1、velocity L2、E_at、field difference frozen summary；Case8 width/RMS/HF/window fraction与max Pi_at只在summary，未存完整空间Pi_at。八组density可做终态比较；checkpoint/interruption/smoke不得替代final production。{ref('Figure8_local_run_archive/audit/fig8_data_audit.md')}纠正旧“B–D field difference随网格单调消失”的叙述：冻结数组difference实际不单调。不能将旧图稿趋势混入主线。

**F. Linear/Fourier。** {ref(L+'/experiment_report.md')}确认common zero-residual discrete shock，不使用Case8 tanh初态作linearization。base NPZ Ubar128×4、Ubar_2d32×128×4、x128、y32；谱CSV68×9；eigenvalues complex array4×17×512；left/right eigenvectors4×17×512×32（仅top32 vectors）；leading primitive profiles见逐member metadata。q_at四档、ell0..16完备；ell1/4/8/12存在。shock mask fixed x-cell58..66（pressure-jump5% max、邻cell扩一层）。leakage5.889e-16、operator-linearity6.062e-12、eigen residual<=5.389e-11、colored action3.203e-08等记录在frozen audit。production FD epsilon1e-8，旧1e-6扫描已替换。Jacobian/Fourier构建代码和audit存在，但serialized矩阵未找到。mode4/8 leading localization低，不应称“shock-localized”；最大alpha在mode16几乎不变，其他mode左右移均存在。

**G. Fig13。** 真实24 runs=4 modes×2 q_at×3 ε，全部33-point physical_time/modal_amplitude/log_modal_amplitude等8字段CSV存在。summary24×18包含sigma_LIN、sigma_RK3、sigma_CFD、relative discrepancy、fit0..32、R²、history_path。此次只读取和检查完整性；已有summary按ε分组最大relative discrepancy：{V['fig13']['per_epsilon_worst_relative_error']}（fraction，不是百分数）。min fit R²={V['fig13']['min_fit_r2']}。可播放真实投影幅值时间序列；没有24组full spatial CFD state轨迹，不能从eigenmode伪造实际field movie。

**H. Mach3 Cylinder。** {ref(C+'/J2C_V2_PROTOCOL_LOCK.json')}固定stretched O-grid nr32×ntheta128、r=.5..8、stretch3、T2、dt=.00020498103925386903、9757 steps。A/B/D各有final state、9757-step history、五endpoint face NPZ（0/2439/4878/7318/9757）。snapshot instant rate有空间数据；`spatial_cumulative.npz`仅bins17、channel_bg/aa/at/total各16与shock_at/J/Pt scalar。{ref('jcp_extension_v1/J2_entropy_diagnostics/J2C_S0_localization_semantics/analysis/localization_values.json')}明确既有固定band份额是**cumulative**，此前summary中的final-rate文字须按audit理解；数值约.007776872193，不据此补全空间map。E_at_int=.09142394966318078，primary budget interior-only；fixed A_u authoritative front radial ±.16与Case8不同。front widths B/D近检测器分辨下限，不能细分优劣。full-trajectory空间Pi_at正式MISSING，已存累计sector是可接受的最小替代。

**I. External flux context。** 四种指定通量Roe-HH/HLLE/HLLEMCC/Chandrashekar KEP-ES(Rus)在Case8 v2和Cylinder v1都有canonical width和完整raw终态/多个checkpoint，并非仅summary。raw路径是`raw/roe_hh`、`raw/hlle`、`raw/hllemcc`、`raw/chandrashekar_ec_ev_llf`。本次width与独立canonical表精确匹配；未经逐文件上游冻结核验的raw fields仍AVAILABLE_UNVERIFIED/NOT_USABLE，不能仅凭“full field存在”视为production-ready。图17审计中external与final internal采用两组分开来源，不使用original/proposed旧内组。不作universal flux排名。

## 6. V1_DATA_SUPPORT_MATRIX

{table(['P0/Module','Feature / Required data','Asset references','Status','Frontend readiness','P0 blocker'],[[x['p0_id']+'/'+x['module'],x['feature']+'：'+'；'.join(x['required_data']),', '.join(x['asset_ids']),x['status'],x['frontend_readiness'],'NO; limited features recorded' if x['status']=='PARTIALLY_SUPPORTED' else 'NO'] for x in support])}

精确各asset数据status列在JSON的asset_statuses；P0支持状态与单个asset状态不能混同。不存在“后端已可运行”的结论。

## 7. SCIENTIFIC_SEMANTICS_MATRIX

{table(['Metric ID / UI term','Definition and time/spatial scope','Units','Evidence / constraint'],[[x['metric_id']+' / '+x['label'],x['definition']+'；'+x['scope'],x['units'],ref(x['source'])+'；'+x['constraint']] for x in sem])}

## 8. DATA_DEPENDENCY_MAP

仅映射已存在流程，不在本阶段重新计算。

'''
for d in dependency:doc+='`'+' → '.join(d['chain'])+'`\n\nEvidence：'+', '.join(d['evidence'])+'。Missing：'+('; '.join(d['missing']) or 'none')+'。\n\n'
doc+='## 9. Replay Candidates\n\n'+table(['Experiment','Class','True temporal support','Constraint'],[[x['case'],x['classification'],x['time_support'],x['constraint']] for x in replay])+'\n'
doc+='## 10. Live Demo Candidates\n\n只基于已读源码/配置/规模/历史耗时初筛，不保证现场可运行。没有启动任何候选。\n\n'+table(['Candidate','Class','Reason/source'],[[x['case'],x['classification'],x['reason']+' '+ref(x['source'])] for x in live])+'\n'
doc+='## 11. P0 Blocker Audit\n\n'+table(['P0','Status','Specific gap or supported degradation'],[[x['p0_id']+' '+x['feature'],x['status'],x['reason']] for x in p0])+'\n'
doc+='## 12. Missing Assets\n\n'+table(['Asset ID','Required asset','Evidence / limitation','P0 impact'],[[a['asset_id'],a['semantic_meaning'],a['limitations'][0],a['p0_impact']] for a in missing])+'\n'
doc+='\nTOP_5_DATA_GAPS：\n\n'+''.join(f'{i+1}. {s}\n' for i,s in enumerate(gaps))+'\n'
doc+=f'''## 13. Legacy/Superseded Assets

LEGACY={counts['LEGACY']}；SUPERSEDED={counts['SUPERSEDED']}，验收LEGACY_COUNT合计{summary['LEGACY_COUNT']}。CSV/JSON逐文件列出，均NOT_USABLE。Case8 baseline v1、旧results flagship/Quirk、J2C失败formal、J2D旧formal/v2不得混进最终方法。MUSCL旧Figure8的趋势问题是图稿叙述被纠正，当前冻结MUSCL生产数组并非legacy。所有fig7图表属来源不足，而不伪称已冻结raw。

## 14. Risks

- 18条historical source-hash引用与current source不同（含多个manifest重复引用），涉及baseline_case7/cylinder production driver、Case7-v3 extension driver及channel observer；最终flux SHA不变。`hash_verification.json`保留expected/current/path，不能据旧hash承诺用当前source完全复现。未修改任何source或FREEZE。
- Metadata verification和部分sum/endpoint检查不能替代全部科学认证；科学认证采用既有报告，缺失字段UNKNOWN。尚未建立SI单位映射、数据分发许可与来源外复制授权清单。
- Snapshot时间不一定等于请求的round checkpoint time；使用NPZ实际time。stage与step不能混称；stage-weighted_cumulative不是fully-discrete entropy identity。
- Different masks/boundary scopes、高频定义及detector floor禁止统一百分比排名；同名Pi_at有不同measure conventions。
- Freeze与工作副本保留重复物理文件资产；正式loader需显式选canonical evidence，不按文件名字自动去重。Phase1只是metadata索引，未生成Web数据包。

## 15. Recommendations for PRD

本节只列数据约束与进入下一阶段的建议，不撰写PRD或设计页面/API。

TOP_5_PRD_CONSTRAINTS：

'''+''.join(f'{i+1}. {s}\n' for i,s in enumerate(constraints))+f'''
优先承接Gate冻结map、谱/validation、Case8六checkpoint及step ledger。缺项展示不可用；Cylinder采用累计sector和固定band scalar，累计heatmap在缺口解决前不作承诺。正式发布前检查adapter保留变量、坐标、时间、单位、mask、source/hash、诊断重跑标签，并只加载已确认身份的资产。P1/P2不得追加到P0。

## 16. OPEN_QUESTIONS

1. Near1D五档raw结果是否存在于本科研根之外？本根只有明确论文抄录来源，本阶段不访问其他盘猜补。
2. Cylinder full-trajectory空间map是否另有授权冻结资产？现有16箱与五instant maps不足以重构。任何新增CFD或科学后处理均留待另行任务。
3. Ledger在固定快照同步表达、Cross-flow在sector/band表达的降级是否可作为冻结P0最小闭环？若坚持dense spatial/累计Cylinder heatmap，缺口成为相应功能阻断，应按Phase0 change control处理。
4. 当前driver/observer source drift与freeze source版本如何由后续Reproducibility审计处理？使用exact archived copies前需逐项确认，不静默更新旧manifest。
5. 模型单位与SI尺度、数据许可/竞赛分发权限尚未确定；保持UNKNOWN，不把无量纲坐标任意写成m/s或Pa。
6. PSD与正熵产解释限于已认证fixed-interface分解；不要以图形/交互扩大到universal damping、高阶/3D或任意Mach鲁棒性。

## Acceptance Record

```text
'''+''.join(f'{k}={summary[k]}\n' for k in ['DATA_ASSET_INVENTORY','SCIENTIFIC_FILES_MODIFIED','CFD_RUNS_STARTED','ASSET_COUNT','FROZEN_VERIFIED_COUNT','LEGACY_COUNT','MISSING_ASSET_COUNT','P0_SUPPORTED_COUNT','P0_PARTIAL_COUNT','P0_BLOCKED_COUNT','TIME_SERIES_ASSET_COUNT','REPLAY_CANDIDATE_COUNT','LIVE_DEMO_CANDIDATE_COUNT','INVENTORY_DOC','INVENTORY_JSON','NEXT_PHASE'])+'''```

TIME_SERIES_ASSET_COUNT只计已有可用CSV时间序列文件（含工作/冻结副本），不把每个单帧NPZ算一条时间序列；6帧/5帧场组另列Replay。Replay候选数为7个实验家族；Live候选数为GOOD_CANDIDATE或POSSIBLE的3个初筛家族，不表示已经运行。NEXT_PHASE=PRD只是允许下一阶段，本阶段未开始。

完整逐asset字段/shape/header/hash/source、状态与模块关联见data_asset_inventory.json和CSV。DATA_INVENTORY_FREEZE.json只冻结本次盘点产物，不将未经核验的数据升级为科学冻结。
'''
(O/'01_DATA_ASSET_INVENTORY.md').write_text(doc,encoding='utf-8')
save('acceptance_summary.json',summary)
ch=f'''# ShockPath Phase 1 Changelog

## PHASE1_DATA_ASSET_INVENTORY — {timestamp}

- Phase0 V1_SCOPE_FREEZE confirmed; original scope/PROJECT_FREEZE/FREEZE_MANIFEST/CHANGELOG unchanged.
- User-requested Phase1 output directory: D:\\比赛\\数媒\\data.
- Read-only metadata, recorded-hash audit and lightweight evidence checks; no scientific source mutation, no CFD run.
- Inventory includes {len(A)-len(missing)} existing file assets and {len(missing)} explicit missing logical assets; P0 supported={summary['P0_SUPPORTED_COUNT']}, partial={summary['P0_PARTIAL_COUNT']}, blocked={summary['P0_BLOCKED_COUNT']}.
- This local Phase1 changelog records the new phase without editing the hash-frozen Phase0 CHANGELOG.md.
- Next phase PRD; not started.
'''
(O/'CHANGELOG.md').write_text(ch,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
