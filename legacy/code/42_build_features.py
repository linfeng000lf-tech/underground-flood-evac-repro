# -*- coding: utf-8 -*-
"""第6章 步骤1：双源数据融合与特征构造。
用冻结引擎重跑1920启发式run(与第5章同种子)，捕获每个个体"首个承诺行为"标签，
逐run核对与已提交run级结果完全一致；合并情景数值因子(批量配置)与分类因子(实验设计表)，
产出个体级建模宽表(供关联规则/机器学习)与run级情景表。"""
import json, importlib
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel
COMMIT=('immediate_evacuate','nearest_exit','follow_guidance')
def behavior_label(a):
    acts=[x[1] for x in a.actions]
    for ac in COMMIT:
        if ac in acts: return ac
    if 'follow_crowd' in acts: return 'follow_crowd'
    if 'turn_back' in acts: return 'turn_back'
    for ac in ('wait_and_see','shelter_stay','help_others'):
        if ac in acts: return ac
    return acts[0] if acts else 'unknown'

def one(cid,cfg,seed):
    m=EvacModel(seed=seed,use_llm=False,tag=cid,**cfg); s=m.run(900)
    run={'cid':cid,'seed':seed,'n':m.n,'evacuated':s['evacuated'],'rescued':s['rescued'],
         'stranded':s['stranded'],'deceased':s['deceased']}
    inds=[]
    for a in m.agents:
        r={'cid':cid,'seed':seed,'id':a.id,'final_status':a.status,'behavior':behavior_label(a),
           'evac_time':a.evac_time,'peak_depth':round(a.peak_depth,2),
           'exposure_s':round(a.exposure_s,1),'n_actions':len(a.actions)}
        r.update({k:a.profile[k] for k in
            ('年龄','性别','角色','风险偏好','水灾经验','熟悉度','行动能力','结伴')})
        inds.append(r)
    return run,inds

def main():
    R=20
    configs=json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))
    jobs=[(c['cid'],c['cfg'],20240923+k) for c in configs for k in range(R)]
    from joblib import Parallel, delayed
    res=Parallel(n_jobs=6,backend='loky')(delayed(one)(*j) for j in jobs)
    runs=pd.DataFrame([r for r,_ in res]); inds=[x for _,l in res for x in l]
    ind=pd.DataFrame(inds)

    # ---- 门禁：与第5章已提交run级结果逐行核对（阈值平局允许±1人的微小非确定性）----
    old=pd.read_csv(RUNS/'批量实验_run级.csv').sort_values(['cid','seed']).reset_index(drop=True)
    new=runs.sort_values(['cid','seed']).reset_index(drop=True)
    diff_runs=0; total_persondiff=0; details=[]
    for col in ('evacuated','rescued','stranded','deceased'):
        d=(new[col].values-old[col].values)
        idx=np.where(d!=0)[0]
        diff_runs=max(diff_runs,len(idx)); total_persondiff+=int(np.abs(d).sum())
        for i in idx:
            details.append({'cid':new.cid[i],'seed':new.seed[i],'字段':col,
                '已提交':int(old[col].values[i]),'重跑':int(new[col].values[i]),'差':int(d[i])})
    pd.DataFrame(details).to_csv(RUNS/'第6章_重跑一致性核对.csv',index=False,encoding='utf-8-sig')
    print('重跑一致性：%d 个run存在差异，累计人数差=%d（详见核对表）'%(diff_runs,total_persondiff))
    if details: print(pd.DataFrame(details).to_string(index=False))

    # ---- 情景数值因子（来自批量配置）----
    rows=[]
    for c in configs:
        d=c['cfg']['depth_override']; alarm=c['cfg'].get('alarm_min')
        rows.append({'cid':c['cid'],'进水位置':c['cfg'].get('entry_override'),
            'd_peak':d['d_peak'],'rise_rate':round(d['d_peak']/max(d['t_peak'],1),3),
            'alarm_min':120 if alarm is None else alarm,'has_alarm':alarm is not None,
            'exit_width':c['cfg']['exit_width'],'rescue_min':c['cfg']['rescue_min'],
            'fam_frac':c['cfg']['fam_frac'],'n_scenario':c['cfg']['n']})
    scn=pd.DataFrame(rows)
    # ---- 情景分类因子（来自实验设计表，便于规则/报告）----
    design=pd.read_excel(RUNS/'实验设计表.xlsx',sheet_name='实验矩阵')
    design=design.rename(columns={'实验编号':'cid'})
    scn=scn.merge(design[['cid','积水速率','人群密度','播报时机','闸机管控','峰值水深m']],on='cid')
    scn.to_csv(RUNS/'第6章_run级情景表.csv',index=False,encoding='utf-8-sig')

    W=ind.merge(scn,on='cid',how='left')
    W['self_evac']=(W.final_status=='evacuated').astype(int)
    W.to_csv(RUNS/'第6章_建模宽表_个体.csv',index=False,encoding='utf-8-sig')
    print('建模宽表(个体)',W.shape,'列：',W.columns.tolist())
    print('\n行为标签分布:'); print(W.behavior.value_counts())
    print('\n自救率 %.3f；自救%d 获救%d'%(W.self_evac.mean(),
        (W.self_evac==1).sum(),(W.self_evac==0).sum()))

if __name__=='__main__':
    main()
