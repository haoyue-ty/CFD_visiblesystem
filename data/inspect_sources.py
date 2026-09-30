import os,json,hashlib,csv,sys
from pathlib import Path
ROOT=Path(r'D:\Paper\passage6')
OUT=Path(r'D:\比赛\数媒\data')
SKIP={'.venv','.git','__pycache__','.pytest_cache','.superpowers','.workbuddy','node_modules'}
files=[]
for base,dirs,names in os.walk(ROOT):
    dirs[:]=[d for d in dirs if d not in SKIP]
    for n in names:
        p=Path(base)/n;s=p.stat()
        files.append({'path':p.relative_to(ROOT).as_posix(),'size':s.st_size,'mtime_ns':s.st_mtime_ns})
(OUT/'source_tree_before.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
print('files',len(files),'bytes',sum(x['size'] for x in files))
for f in files:
    p=f['path'];l=p.lower()
    if any(t in l for t in ['near_','near-','epsilon','perturbation_scan','high_order_transfer','fig_14/du_spatial']) and p.endswith(('.md','.json','.csv','.npz','.npy')):
        print(p,f['size'])
