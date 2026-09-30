"""Read-only metadata audit. Does not import solver or execute scientific code."""
import os,json,csv,re,hashlib,zipfile,math
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
ROOT=Path(r'D:\Paper\passage6'); OUT=Path(r'D:\比赛\数媒\data'); SCOPE=Path(r'D:\code_project\CFD_visiblesystem')
METHOD='cross_mode_ec_unified_v1'; MH='98776078f19fa4b31826e88e8851222f217210c3c2ae341d68aeb60aad3a27e0'
def readj(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
hashes={}
def sha(p):
    p=Path(p).resolve();k=str(p)
    if k not in hashes:
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
        hashes[k]=h.hexdigest()
    return hashes[k]
tree=readj(OUT/'source_tree_before.json')
prefixes=['experiments/','corrected_physics_reproduction_v1/','final_corrected_evidence_freeze_v1/','unified_corrected_method_v3/','jcp_extension_v1/J1_entropy_channel_theory/','jcp_extension_v1/J2_entropy_diagnostics/','jcp_extension_v1/J3_case8_parameter_continuation/','jcp_extension_v1/J4_P0_baseline_audit/','jcp_extension_v1/J12_scientific_closeout/','jcp_extension_v1/JCP_final_readiness_audit/','results/high_order_transfer/','baseline_production_case8_v2/','baseline_production_cylinder_v1/','baseline_production_case8_v1/','results/quirk_periodic_odd_even_v1/','results/flagship_cross_modal_case8_v1/','Figure8_local_run_archive/audit/','Paper/fig/fig_7/','Paper/fig/fig_8/','Paper/fig/fig_17/','Paper/fig/fig_14/Du_spatial_rerun/FREEZE/','freezes/PASSAGE6_PUBLICATION_SAFE_BASELINE_FREEZE_20260915/']
exts={'.json','.csv','.npy','.npz','.md','.txt','.sha256','.yaml','.yml','.py','.png','.svg','.pdf','.flag','.log'}
selected=[ROOT/f['path'] for f in tree if any(f['path'].startswith(x) for x in prefixes) and Path(f['path']).suffix.lower() in exts]
selected += [ROOT/'README.md',ROOT/'solver/fluxes/cross_mode_ec_unified_v1.py',ROOT/'solver/fluxes/unbounded_cross_mode.py',ROOT/'solver/experiments/gate_ablation.py',ROOT/'solver/experiments/postprocess_gate_ablation.py',ROOT/'solver/experiments/high_order_transfer.py',ROOT/'solver/cases/flagship_cross_modal_case8.py',ROOT/'solver/cases/isentropic_vortex.py',ROOT/'solver/diagnostics/flagship_cross_modal_case8.py',ROOT/'solver/diagnostics/cylinder.py']
selected=sorted(set(selected))
# Explicit recorded hash references only; resolution is retained and independently checked.
refs=defaultdict(list); checks=[]
def register(mp,path,expected,base=None,role='UNKNOWN'):
    if not isinstance(expected,str) or not re.fullmatch('[0-9a-fA-F]{64}',expected):return
    if not isinstance(path,str):return
    path=path.removeprefix('SOURCE:')
    if '.py:' in path:
        checks.append({'manifest':str(mp),'recorded_path':path,'expected_sha256':expected,'result':'UNRESOLVED_REFERENCE','reason':'Function-level hash is not a whole-file hash'});return
    q=Path(path.replace('\\','/'));bases=[base] if base else [mp.parent,ROOT]
    if not q.is_absolute() and not base:bases += list(mp.parents)[:5]
    candidates=[q] if q.is_absolute() else [b/q for b in bases if b]
    candidates=list(dict.fromkeys(p.resolve() for p in candidates))
    existing=[p for p in candidates if p.is_file()]
    matches=[p for p in existing if sha(p).lower()==expected.lower()]
    chosen=matches[0] if len(matches)==1 else (existing[0] if existing else candidates[0])
    state='MATCH' if matches else ('MISMATCH' if existing else 'MISSING')
    rec={'manifest':str(mp),'recorded_path':path,'resolved_path':str(chosen),'expected_sha256':expected.lower(),'actual_sha256':sha(chosen) if chosen.is_file() else 'UNKNOWN','result':state,'artifact_role':role,'matching_locations':list(map(str,matches))}
    checks.append(rec)
    if chosen.is_file():refs[str(chosen)].append(rec)
def walkrefs(obj,mp,base=None):
    if isinstance(obj,dict):
        path=next((obj[k] for k in ['absolute_path','relative_path_from_freeze','relative_path','path','source_path','file','file_path','artifact'] if isinstance(obj.get(k),str)),None)
        hv=next((obj[k] for k in ['sha256','source_sha256','hash','expected_sha256'] if isinstance(obj.get(k),str) and re.fullmatch('[a-fA-F0-9]{64}',obj[k])),None)
        if path and hv:register(mp,path,hv,base,obj.get('artifact_role',obj.get('category','UNKNOWN')))
        for k,v in obj.items():
            if isinstance(v,str) and re.fullmatch('[0-9a-fA-F]{64}',v) and ('/' in k or '\\' in k or k.endswith('.py')):register(mp,k,v,base)
            elif isinstance(v,(dict,list)):walkrefs(v,mp,base)
    elif isinstance(obj,list):
        for x in obj:walkrefs(x,mp,base)
controls=[p for p in selected if ('manifest' in p.name.lower() or 'hash' in p.name.lower() or p.name=='checksums.txt' or p.suffix=='.sha256')]
for mp in controls:
    try:
        base=None
        if mp.name=='EXPERIMENT2_FREEZE_MANIFEST.json':base=ROOT/'results/high_order_transfer'
        if mp.name=='result_hashes.csv':base=mp.parent.parent
        if mp.name=='failed_root_hashes.csv':
            base=ROOT/('jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal' if 'J2C_' in str(mp) else 'jcp_extension_v1/J2_entropy_diagnostics/J2D_case7_formal')
        if mp.name=='repaired_driver_hashes.csv':base=mp.parent.parent/'repaired_driver'
        if mp.suffix=='.json':walkrefs(readj(mp),mp,base)
        elif mp.suffix=='.csv':
            with mp.open(encoding='utf-8-sig',newline='') as f:
                for row in csv.DictReader(f):walkrefs(row,mp,base)
        else:
            for line in mp.read_text(encoding='utf-8-sig',errors='replace').splitlines():
                m=re.match(r'^([a-fA-F0-9]{64})\s+\*?(.+?)\s*$',line)
                if m:register(mp,m[2],m[1])
    except Exception as e:checks.append({'manifest':str(mp),'result':'PARSE_ERROR','error':str(e)})
phase0=readj(SCOPE/'PROJECT_FREEZE.json');phasechecks=[]
for row in readj(SCOPE/'FREEZE_MANIFEST.json')['files']:
    p=SCOPE/row['relative_path']; phasechecks.append({'path':str(p),'expected_sha256':row['sha256'],'actual_sha256':sha(p),'match':sha(p)==row['sha256']})
assert phase0['freeze_version']=='V1_SCOPE_FREEZE' and all(x['match'] for x in phasechecks)
assert sha(ROOT/'solver/fluxes/cross_mode_ec_unified_v1.py')==MH
dump('hash_verification.json',{'phase0':phasechecks,'method_hash_match':True,'recorded_hash_references':checks,'counts':dict(Counter(x['result'] for x in checks))})
print('SELECTED',len(selected),'HASH_CHECKS',dict(Counter(x['result'] for x in checks)),flush=True)
P8=readj(ROOT/'jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/J2B_PROTOCOL_LOCK.json')
PC=readj(ROOT/'jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2/J2C_V2_PROTOCOL_LOCK.json')
PL=readj(ROOT/'experiments/linear_perturbation_analysis/FREEZE/config.json')
EC=readj(ROOT/'experiments/entropy_budget_closure/config.json')
J2B='jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal'
J2C='jcp_extension_v1/J2_entropy_diagnostics/J2C_cylinder_formal_v2'
L='experiments/linear_perturbation_analysis/FREEZE'
GA='experiments/gate_ablation/FREEZE'
SP='Paper/fig/fig_14/Du_spatial_rerun/FREEZE'
def header(f):
    ver=np.lib.format.read_magic(f)
    shape,fortran,dtype=(np.lib.format.read_array_header_1_0(f) if ver==(1,0) else np.lib.format.read_array_header_2_0(f))
    return {'shape':list(shape),'dtype':str(dtype),'fortran_order':fortran,'object_dtype':bool(dtype.hasobject)}
def inspect(p):
    d={};s=p.suffix.lower()
    if s=='.npy':
        with p.open('rb') as f:d=header(f)
    elif s=='.npz':
        d['members']={}
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.endswith('.npy'):
                    with z.open(n) as f:d['members'][n[:-4]]=header(f)
        d['shape']={k:v['shape'] for k,v in d['members'].items()};d['dtype']={k:v['dtype'] for k,v in d['members'].items()}
        scalars=[k for k,v in d['members'].items() if v['shape']==[] and not v['object_dtype'] and k in ['time','step','accepted_steps','final_time']]
        if scalars:
            with np.load(p,allow_pickle=False) as z:d['scalars']={k:z[k].item() for k in scalars}
    elif s=='.csv':
        with p.open(encoding='utf-8-sig',newline='') as f:
            r=csv.DictReader(f);cols=r.fieldnames or [];cnt=0;first=None;last=None;ranges={};unique={};dt={k:'empty' for k in cols}
            for row in r:
                cnt+=1;first=first or row;last=row
                for k,v in row.items():
                    if k is None:continue
                    if k in ['time','physical_time','time_start','time_end','time_n','time_np1','t_stage_or_step_time','t','t_n','t_np1','stage_time','step','accepted_step','epsilon','eps','q_at','q_aa','mode','m','ell','CFL','cfl']:
                        try:
                            n=float(v)
                            if math.isfinite(n):
                                old=ranges.get(k,[n,n]);ranges[k]=[min(old[0],n),max(old[1],n)]
                                if k in ['epsilon','eps','q_at','q_aa','mode','m','ell','CFL','cfl'] and len(unique.setdefault(k,set()))<100:unique[k].add(n)
                        except (ValueError,TypeError):pass
                    if v is not None and v!='' and dt[k]!='string':
                        try:float(v);dt[k]='float64-compatible'
                        except (ValueError,TypeError):dt[k]='string'
        d={'columns':cols,'shape':[cnt,len(cols)],'dtype':dt,'first_row':first,'last_row':last,'numeric_ranges':ranges,'unique_values':{k:sorted(v) for k,v in unique.items()}}
    elif s=='.json':
        x=readj(p);d={'shape':{'top_level_type':type(x).__name__,'count':len(x) if hasattr(x,'__len__') else 1},'dtype':'JSON','keys':list(x) if isinstance(x,dict) else 'UNKNOWN'}
        if isinstance(x,dict) and p.stat().st_size<35000:d['metadata']=x
    return d
FIELDS='asset_id module case experiment method method_hash configuration q_aa q_at gate reconstruction grid CFL epsilon final_time variable semantic_meaning units data_granularity time_granularity spatial_granularity coordinate_system mask_definition data_format dtype shape file_size absolute_source_path relative_source_path sha256 freeze_status verification_status raw_or_derived production_or_analysis frontend_ready requires_postprocess replay_candidate live_demo_candidate scientific_notes limitations'.split()
assets=[]
for i,p in enumerate(selected):
    rel=p.relative_to(ROOT).as_posix();lo=rel.lower();s=p.suffix.lower();a={k:'UNKNOWN' for k in FIELDS}
    a.update(asset_id='asset_'+hashlib.sha256(rel.encode()).hexdigest()[:12],module=['07'],experiment=rel.split('/')[0],absolute_source_path=str(p),relative_source_path=rel,file_size=p.stat().st_size,sha256=sha(p),data_format=s.lstrip('.').upper(),frontend_ready='NOT_USABLE',requires_postprocess='UNKNOWN',replay_candidate=False,live_demo_candidate='UNKNOWN',time_granularity='STATIC',raw_or_derived='summary',production_or_analysis='analysis',scientific_notes=[],limitations=[],evidence_links=[],status='AVAILABLE_UNVERIFIED',freeze_status='UNKNOWN',verification_status='METADATA_INSPECTED_ONLY',frontend_ready_reason='Identity/semantics must be explicit before product use')
    try:a['inspection']=inspect(p);a['shape']=a['inspection'].get('shape','UNKNOWN');a['dtype']=a['inspection'].get('dtype','UNKNOWN')
    except Exception as e:a['inspection']={'error':str(e)};a['status']='PARTIAL';a['limitations'].append('Metadata parsing failed')
    rr=refs.get(str(p.resolve()),[]);a['hash_evidence']=rr
    matching=[x for x in rr if x['result']=='MATCH'];mismatch=[x for x in rr if x['result']=='MISMATCH']
    frozen=[x for x in matching if any(t in x['manifest'].lower() for t in ['freeze','result_hashes','checksums'])]
    if frozen:a.update(status='FROZEN_VERIFIED',freeze_status='RECORDED_HASH_MATCH',verification_status='SHA256_MATCH_AND_METADATA_INSPECTED')
    elif matching:a.update(status='VERIFIED_NOT_FROZEN',freeze_status='NO_FREEZE_MEMBERSHIP_PROVEN',verification_status='RECORDED_SHA256_MATCH_AND_METADATA_INSPECTED')
    if mismatch:a['limitations'].append('At least one historical hash reference mismatches; inspect hash_evidence')
    case8=J2B in rel or ('corrected_physics_reproduction_v1/case8/' in rel) or SP in rel or 'J3_case8_parameter_continuation' in rel
    cylinder=J2C in rel or 'corrected_physics_reproduction_v1/cylinder/' in rel
    if case8:
        a.update(case='Case8_Mach6',module=['02','03','06','07'],method=METHOD,method_hash=MH,grid={'nx':128,'ny':32},CFL=.05,final_time=.08,reconstruction='first-order / none',gate='Acoustic',coordinate_system={'x':[0,1],'y':[0,1],'array_axes':'[y,x,conservative_component]'},mask_definition=P8['front_window'],experiment=J2B,evidence_links=[J2B+'/J2B_PROTOCOL_LOCK.json',J2B+'/J2B_STATUS.json'])
    if cylinder:
        a.update(case='Mach3_Cylinder',module=['02','03','06','07'],method=METHOD,method_hash=MH,grid={'nr':32,'ntheta':128},CFL='UNKNOWN',final_time=2,reconstruction='first-order',gate='Acoustic',coordinate_system={'type':'stretched polar O-grid','r_inner':.5,'r_outer':8,'stretch':3,'array_axes':'inspect file members; Cartesian state on curvilinear cells'},mask_definition=PC['shock_localization_geometry'],experiment=J2C,evidence_links=[J2C+'/J2C_V2_PROTOCOL_LOCK.json',J2C+'/J2C_V2_STATUS.json'])
    if 'entropy_budget_closure' in rel:
        a.update(case='Case7_Isentropic_Vortex',module=['02','03','07'],experiment='experiments/entropy_budget_closure',method=METHOD,method_hash=MH,grid={'nx':128,'ny':128},final_time=10,reconstruction='first-order',gate='Acoustic',coordinate_system={'x':[0,10],'y':[0,10],'boundary':'periodic'},evidence_links=['experiments/entropy_budget_closure/FREEZE/FREEZE_MANIFEST.json','experiments/entropy_budget_closure/FREEZE/frozen_experiment_report.md'])
        m=re.search(r'(Bu|Du)_cfl_(\d+)',rel)
        if m:a['configuration']='B_u' if m[1]=='Bu' else 'D_u';a['CFL']=int(m[2])/10**len(m[2])
    if 'gate_ablation' in rel:
        a.update(case='Case8_Gate_Ablation',module=['02','04','07'],experiment='experiments/gate_ablation',method='cross_mode_ec_unified_v1 + recorded gate variant',method_hash=MH,q_aa=3.96,grid={'nx':128,'ny':32},CFL=.05,final_time=.08,reconstruction='first-order',coordinate_system={'x_i':'(i+1/2)/128','y_j':'(j+1/2)/32','array_axes':'[y,x]'},mask_definition='cell-center |x_i-(0.5+0.0125*sin(8*pi*y_j))|<=0.08; prescribed initial front',evidence_links=[GA+'/MANIFEST.md',GA+'/README.md',GA+'/VERIFICATION_REPORT.md'])
        for g,q in [('acoustic',.4),('pressure',.31018332312583474),('ungated',.03483470441226932)]:
            if g in p.name.lower() or re.search('/'+g+'/',lo):a['gate']=g.title();a['q_at']=q;a['configuration']='matched_'+g if 'results' in lo else 'UNKNOWN'
        if '/calibration/cache/' in lo:a['q_at']='UNKNOWN';a['production_or_analysis']='analysis';a['limitations'].append('Calibration cache is not a formal matched production endpoint')
    if 'linear_perturbation_analysis' in rel:
        a.update(case='Common_Mach6_Zero_Residual_Discrete_Shock',module=['02','05','07'],experiment='experiments/linear_perturbation_analysis',method=METHOD,method_hash=MH,grid=PL['mesh'],CFL=.05,q_aa=3.96,gate='Acoustic',reconstruction='first-order / none',coordinate_system=PL['mesh'],evidence_links=[L+'/method_identity.json',L+'/config.json',L+'/validity_gates.json',L+'/experiment_report.md'])
        m=re.search(r'm(\d+)_q(\d+)p(\d+)_eps([^/]+)\.csv',rel)
        if m:a.update(q_at=float(m[2]+'.'+m[3]),epsilon=float(m[4]),configuration={'mode':int(m[1]),'q_at':float(m[2]+'.'+m[3]),'epsilon':float(m[4])},time_granularity='PER_STEP',raw_or_derived='raw')
        a['mask_definition']='fixed base-state shock mask; see '+L+'/spectrum/shock_mask.json'
    if 'high_order_transfer' in rel:
        a.update(case='Case8_MUSCL' if '/case8/' in rel else 'Case7_MUSCL',module=['02','03','07'],experiment='results/high_order_transfer',method=METHOD,method_hash=MH,reconstruction='primitive-variable MUSCL, componentwise MC limiter',gate='Acoustic',q_aa=3.96,evidence_links=['results/high_order_transfer/experiment2_freeze/EXPERIMENT2_FREEZE_README.md','results/high_order_transfer/experiment2_freeze/EXPERIMENT2_FREEZE_MANIFEST.json'])
        if '/case8/' in rel:a.update(grid={'nx':128,'ny':32},CFL=.05,final_time=.08)
        elif '/vortex/' in rel:
            m=re.search(r'vortex_(64|128|256)_',rel)
            if m:a['grid']={'nx':int(m[1]),'ny':int(m[1])}
            a.update(CFL=.1,final_time=10,coordinate_system={'x':[0,10],'y':[0,10],'boundary':'periodic'})
        if any(t in lo for t in ['smoke','checkpoint_fresh','profile/']):a['production_or_analysis']='analysis';a['limitations'].append('Auxiliary/nonproduction record; do not substitute for eight final runs')
    for conf,qaa,qat in [('A_u',13.2,0),('B_u',3.96,0),('C_u',13.2,.396),('D_u',3.96,.396)]:
        if re.search(r'(?i)(?:/|_|\b)'+conf+r'(?:/|\.|_|\b)',rel) and a['method']==METHOD:a.update(configuration=conf,q_aa=qaa,q_at=qat)
    if 'baseline_production_case8_v2' in rel or 'baseline_production_cylinder_v1' in rel:
        a.update(case='Case8_external' if 'case8' in rel else 'Cylinder_external',module=['02','06','07'],experiment=rel.split('/')[0],method='UNKNOWN',method_hash='NOT_APPLICABLE',evidence_links=[rel.split('/')[0]+'/production_manifest.json','jcp_extension_v1/J4_P0_baseline_audit/BASELINE_EVIDENCE_REGISTRY.csv'])
        methods={'roe_hh':'Roe-HH','hlle':'HLLE','hllemcc':'HLLEMCC','chandrashekar':'Chandrashekar KEP-ES(Rus)','hllc':'HLLC','ausm':'AUSM+-up'}
        for token,label in methods.items():
            if token in lo:a['method']=label
        if '/original/' in lo or '/proposed/' in lo:a['status']='LEGACY';a['limitations'].append('Historical architecture internal row; not final A_u/B_u/D_u')
    legacy=any(t in rel for t in ['baseline_production_case8_v1/','results/flagship_cross_modal_case8_v1/','results/quirk_periodic_odd_even_v1/','J2C_cylinder_formal/','J2D_case7_formal/','J2D_case7_formal_v2/'])
    if legacy:a.update(status='SUPERSEDED' if 'v1/' in rel or 'J2D_' in rel or 'J2C_cylinder_formal/' in rel else 'LEGACY',method='UNKNOWN',method_hash='UNKNOWN');a['limitations'].append('Historical/superseded record; do not mix with final unified-method evidence')
    if 'Paper/fig/fig_7/' in rel:
        a.update(case='Near1D_Mach6_epsilon_scan_UNVERIFIED',module=['01','02','07'],experiment='Near1D perturbation scan',status='AVAILABLE_UNVERIFIED',raw_or_derived='figure-only',frontend_ready='NOT_USABLE',verification_status='PROVENANCE_IS_MANUSCRIPT_TRANSCRIPTION',evidence_links=['Paper/fig/fig_7/README.md'],limitations=['Five E_at values transcribed from manuscript; localization and B/D amplitude ratios approximate; no raw run identity/hash/protocol proven. Not production data.'])
    if s in {'.png','.svg','.pdf'}:a.update(raw_or_derived='figure-only',frontend_ready='NOT_USABLE',semantic_meaning='Rendered figure or document; never infer formal numeric data from pixels')
    elif s in {'.npy','.npz'}:
        a.update(raw_or_derived='raw',data_granularity='array/container',production_or_analysis='production' if a['case']!='UNKNOWN' else 'analysis')
        a['variable']=list(a['inspection'].get('members',{})) or p.stem
        a['spatial_granularity']='see members/shape; explicit semantic mapping below'
        if '/checkpoints/' in rel or '/snapshots/' in rel:a['time_granularity']='MULTI_SNAPSHOT';a['snapshot_time']=a['inspection'].get('scalars',{}).get('time','UNKNOWN')
        elif any(t in lo for t in ['final','terminal','density']):a['time_granularity']='TERMINAL'
        if 'spatial_cumulative' in rel:a.update(time_granularity='TRAJECTORY_INTEGRATED',raw_or_derived='derived',semantic_meaning='16 angular-bin channel accumulations plus scalar front-band integrals; NOT full spatial field',spatial_granularity='16 sectors + scalar fixed-region totals')
        if 'trajectory_integrated' in rel:a.update(time_granularity='TRAJECTORY_INTEGRATED',semantic_meaning='Existing diagnostic rerun: dt/RK-weighted native-face production; face measure still required for integral',raw_or_derived='derived')
        if 'trajectory_integrated_cell' in rel:a['limitations'].append('Arithmetic face-to-cell average for visualization; sum(cell) is not authoritative E_at')
        if p.name=='Pi_at.npy' and 'gate_ablation' in rel:a.update(time_granularity='TRAJECTORY_INTEGRATED',raw_or_derived='derived',semantic_meaning='Cumulative stage-weighted cell allocations INCLUDING face measure and time; sum(Pi_at)=E_at; do not multiply dx*dy or dt again',spatial_granularity='cell-centered [y,x]')
        if '/snapshots/native_faces_' in rel:a.update(semantic_meaning='Instantaneous endpoint native-face entropy production rates / gate / tangential opportunity; not saved RK-stage field',spatial_granularity='native faces')
        if 'spectrum/' in rel:a.update(raw_or_derived='derived',time_granularity='STATIC',spatial_granularity='Fourier block or x-profile (inspect members)',semantic_meaning='Discrete Fourier eigenvalue/eigenvector or leading primitive mode profile on common base state')
    elif s=='.csv':
        a.update(variable=a['inspection'].get('columns',[]),data_granularity='table',semantic_meaning='Columns as recorded in source; consult cited scientific definition')
        if p.name=='stage_closure.csv':a.update(time_granularity='PER_STAGE',raw_or_derived='raw',semantic_meaning='Actual FV RHS entropy contraction G(U), observer D(U), channels and semi-discrete residual for each RK stage')
        elif p.name in ['step_closure.csv','stage_weighted_history.csv','entropy_budget_rerun.csv']:a.update(time_granularity='PER_STEP',raw_or_derived='raw',semantic_meaning='One accepted-step record; RK-weighted channel increments/cumulative integrals; stage-weighted history is not per-stage raw log')
        elif any(k in a['inspection'].get('numeric_ranges',{}) for k in ['time','t','t_n','t_np1']) and a['inspection'].get('shape',[0])[0]>1:a['time_granularity']='PER_STEP' if '/cfd_validation/runs/' in rel else 'MULTI_SNAPSHOT'
    if a['method']!='UNKNOWN' and a['status'] not in ['LEGACY','SUPERSEDED','PARTIAL'] and s in ['.csv','.json','.npz','.npy','.yaml'] and 'fig_7/' not in rel:
        a['frontend_ready']='ADAPTER_REQUIRED';a['frontend_ready_reason']='Requires typed schema, coordinate/field semantics and evidence-preserving conversion; no API/web packet created';a['requires_postprocess']=False;a['replay_candidate']=a['case']!='UNKNOWN'
        if s in ['.csv','.json'] and a['time_granularity']=='STATIC':a['frontend_ready']='SUMMARY_ONLY';a['frontend_ready_reason']='Supports configuration, numeric table/card or evidence view; no flow time slider'
        if s in ['.npz','.npy'] and ('state' in lo or '/checkpoints/' in lo):a['frontend_ready']='POSTPROCESS_REQUIRED';a['requires_postprocess']=True;a['frontend_ready_reason']='Conservative state requires existing Euler primitive-variable diagnostic protocol; metadata/coordinates must be preserved'
    if s in ['.py','.md','.txt','.sha256','.flag','.log'] and 'fig_7/' not in rel and a['status'] not in ['LEGACY','SUPERSEDED']:a['frontend_ready']='SUMMARY_ONLY';a['frontend_ready_reason']='Read-only definition/provenance/report/log; not numeric field input'
    if a['status'] in ['LEGACY','SUPERSEDED']:a.update(frontend_ready='NOT_USABLE',replay_candidate=False)
    if a['semantic_meaning']=='UNKNOWN':a['semantic_meaning']='Definition/configuration/provenance evidence; content must be read with its experiment context'
    if a['method']==METHOD and a['units']=='UNKNOWN':a['limitations'].append('Physical SI unit conversion is not established; units remain UNKNOWN unless explicit in semantic matrix')
    if '/cfd_validation/runs/' in rel:a['final_time']=a['inspection'].get('numeric_ranges',{}).get('physical_time',[None,'UNKNOWN'])[-1]
    if a['production_or_analysis']=='analysis' and any(t in lo for t in ['smoke','checkpoint_fresh','profile/','/calibration/cache/','/logs/preflight']):a.update(frontend_ready='NOT_USABLE',replay_candidate=False)
    assets.append(a)
    if i%500==0:print('INSPECTED',i,flush=True)
dump('inventory_inspected.json',assets)
print('STATUS',dict(Counter(a['status'] for a in assets)))
for fragment in ['corrected_physics_reproduction_v1/case8/05_case8_D_u/checkpoints/step_000382','Cylinder','spatial_cumulative','spectral_summary','fig_7/source_data']:
    found=[a for a in assets if fragment in a['relative_source_path']]
    for a in found[:2]:print('EXAMPLE',a['relative_source_path'],a['shape'],a['status'],a.get('inspection',{}).get('numeric_ranges',{}))
