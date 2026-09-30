import json,csv,hashlib,math
from pathlib import Path
import numpy as np
R=Path(r'D:\Paper\passage6');O=Path(r'D:\比赛\数媒\data')
def rows(p):
    with (R/p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
G='experiments/gate_ablation/FREEZE';L='experiments/linear_perturbation_analysis/FREEZE'
checks={}
gs=rows(G+'/gate_ablation_analysis.csv');gm=[]
for x in gs:
    a=np.load(R/G/'results_snapshot'/x['Gate']/'Pi_at.npy',mmap_mode='r',allow_pickle=False)
    err=abs(float(a.sum())-float(x['E_at']))
    gm.append({'gate':x['Gate'],'shape':list(a.shape),'finite':bool(np.isfinite(a).all()),'nonnegative':bool((a>=0).all()),'sum_vs_E_at_abs_error':err,'pass':err<1e-10,'recorded_window_fraction':float(x['R_front'])})
checks['gate_allocation']=gm
sp=rows(L+'/spectrum/spectral_summary.csv'); combos={(int(x['m']),float(x['q_at'])) for x in sp}
checks['spectrum']={'rows':len(sp),'unique_combinations':len(combos),'modes':sorted({m for m,q in combos}),'q_at':sorted({q for m,q in combos}),'coverage_pass':combos=={(m,q) for m in range(17) for q in [0,.132,.264,.396]}}
vs=rows(L+'/cfd_validation/validation_summary.csv');hist=[];worst={}
for x in vs:
    pp=L+'/cfd_validation/'+x['history_path'];rr=rows(pp)
    ts=[float(z['physical_time']) for z in rr]
    hist.append({'path':pp,'rows':len(rr),'time_range':[min(ts),max(ts)],'strictly_increasing':all(y>x for x,y in zip(ts,ts[1:])),'fit_window':[int(x['fit_start_step']),int(x['fit_end_step'])],'fit_points':int(x['fit_points']),'pass':len(rr)==33 and int(x['fit_points'])==33})
    eps=x['epsilon'];worst[eps]=max(worst.get(eps,0),float(x['relative_discrepancy_CFD_RK3']))
checks['fig13']={'summary_rows':len(vs),'planned_combinations':24,'histories':hist,'per_epsilon_worst_relative_error':worst,'min_fit_r2':min(float(x['fit_r2']) for x in vs),'pass':len(vs)==24 and all(x['pass'] and x['strictly_increasing'] for x in hist)}
checks['case8_flow_snapshots']=[]
for conf,run in [('A_u','03_case8_A_u'),('B_u','04_case8_B_u'),('C_u','06_case8_C_u'),('D_u','05_case8_D_u')]:
    root=R/'corrected_physics_reproduction_v1/case8'/run;series=[]
    for p in sorted((root/'checkpoints').glob('*.npz')):
        with np.load(p,allow_pickle=False) as z:
            series.append({'path':str(p.relative_to(R)),'time':float(z['time']),'step':int(z['step']),'density_shape':list(z['density'].shape),'finite_density_pressure':bool(np.isfinite(z['density']).all() and np.isfinite(z['pressure']).all())})
    with np.load(root/'checkpoints/step_001912.npz',allow_pickle=False) as z, np.load(R/'jcp_extension_v1/J2_entropy_diagnostics/J2B_case8_formal/runs'/('case8_'+conf)/'final_state.npz',allow_pickle=False) as w:
        final_equal=bool(np.array_equal(z['conservative_state'],w['state']))
    checks['case8_flow_snapshots'].append({'configuration':conf,'snapshots':series,'endpoint_equals_hash_verified_J2B_state':final_equal,'temporal_resolution':'6 snapshots; no per-step flow field','scientific_verification_scope':'finite density/pressure, exact endpoint state and protocol timestamps only; no CFD recalculation'})
checks['method_source_hash']=hashlib.sha256((R/'solver/fluxes/cross_mode_ec_unified_v1.py').read_bytes()).hexdigest()
checks['CFD_RUNS_STARTED']=0
(O/'evidence_validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'gate_pass':all(x['pass'] for x in gm),'spectral_coverage':checks['spectrum'],'fig13_runs':len(vs),'fig13_pass':checks['fig13']['pass'],'fig13_worst':worst,'case8_snapshot_counts':[len(x['snapshots']) for x in checks['case8_flow_snapshots']],'case8_endpoint_equal':all(x['endpoint_equals_hash_verified_J2B_state'] for x in checks['case8_flow_snapshots'])},ensure_ascii=False))
