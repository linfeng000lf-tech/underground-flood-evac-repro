# -*- coding: utf-8 -*-
"""第5章 步骤6：大规模计算实验批量运行与落盘。
读取 批量配置.json，每配置 R 个种子(启发式离线、joblib并行)；
产出 run 级结果与个体级"带标签行为大数据"(供第6章)；--llm 可对抽检子集串行跑真实LLM。"""
import argparse, json, importlib
from pathlib import Path
import numpy as np, pandas as pd
from tqdm import tqdm
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel

def single_run(cid,cfg,seed,use_llm):
    m=EvacModel(seed=seed,use_llm=use_llm,tag=cid,**cfg)
    s=m.run(900)
    run_row={'cid':cid,'seed':seed,'n':m.n,
      'evacuated':s['evacuated'],'rescued':s['rescued'],'stranded':s['stranded'],
      'deceased':s['deceased'],'survive_rate':s['survive_rate'],'evac_rate':s['evac_rate'],
      'mean_exposure_s':s['mean_exposure_s']}
    inds=[]
    for a in m.agents:
        row={'cid':cid,'seed':seed,'id':a.id,'final_status':a.status,
             'evac_time':a.evac_time,'peak_depth':round(a.peak_depth,2),
             'exposure_s':round(a.exposure_s,1),'n_actions':len(a.actions)}
        row.update({k:a.profile[k] for k in
            ('年龄','性别','角色','风险偏好','水灾经验','熟悉度','行动能力','结伴')})
        inds.append(row)
    return run_row,inds

def main(R,n_jobs,limit,llm_runs):
    configs=json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))
    if limit: configs=configs[:limit]
    jobs=[(c['cid'],c['cfg'],20240923+k,False) for c in configs for k in range(R)]
    run_rows=[]; ind_rows=[]
    try:
        from joblib import Parallel, delayed
        results=Parallel(n_jobs=n_jobs,backend='loky',verbose=0)(
            delayed(single_run)(*j) for j in tqdm(jobs,desc='批量实验'))
    except Exception:
        results=[single_run(*j) for j in tqdm(jobs,desc='批量实验(串行)')]
    for rr,inds in results:
        run_rows.append(rr); ind_rows.extend(inds)
    pd.DataFrame(run_rows).to_csv(RUNS/'批量实验_run级.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(ind_rows).to_csv(RUNS/'批量实验_个体级.csv',index=False,encoding='utf-8-sig')
    print(f'完成 {len(run_rows)} 个run，个体记录 {len(ind_rows)} 条',flush=True)
    df=pd.DataFrame(run_rows)
    print('存活率 均值%.3f 范围[%.2f,%.2f]；死亡run占比 %.2f'%(
        df.survive_rate.mean(),df.survive_rate.min(),df.survive_rate.max(),
        (df.deceased>0).mean()),flush=True)
    if llm_runs>0:
        run_llm_subset(configs,llm_runs)

def run_llm_subset(configs,k_runs):
    """小样本真实LLM抽检(串行，遵守限流)，用于核对启发式主体结论方向。"""
    rr=[]
    for c in tqdm(configs[:k_runs],desc='LLM抽检'):
        row,_=single_run(c['cid']+'-LLM',c['cfg'],20240923,True); rr.append(row)
    pd.DataFrame(rr).to_csv(RUNS/'批量实验_LLM抽检.csv',index=False,encoding='utf-8-sig')
    print(f'LLM抽检 {len(rr)} 个run完成',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--R',type=int,default=20)
    ap.add_argument('--n_jobs',type=int,default=6)
    ap.add_argument('--limit',type=int,default=0)
    ap.add_argument('--llm_runs',type=int,default=0)
    a=ap.parse_args()
    main(a.R,a.n_jobs,a.limit,a.llm_runs)
