# -*- coding: utf-8 -*-
"""阶段1A：真实LLM分层复现（解决"大规模实验名实不符"）。
从96配置按严重度分层抽 K 个(必含 EXP-095/096/001)，每配置 R 重复，
同场景/同种子/同原始人群下分别跑 启发式(use_llm=False) 与 真实LLM(use_llm=True)。
分片并行(--shard/--nshards)，各分片独立缓存(从全局缓存拷贝)，支持断点续跑。
产出：run级与个体级分片CSV（56合并并做三张一致性表）。"""
import os, json, time, argparse, importlib, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; CACHE=ROOT/'results'/'cache'
sys.path.insert(0,str(ROOT/'code'))
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
def severity(cfg):
    d=cfg['depth_override']; alarm=cfg.get('alarm_min'); alarm=120 if alarm is None else alarm
    rise=d['d_peak']/max(d['t_peak'],1)
    return rise*2 + d['d_peak'] + alarm/60.0
def pick_configs(K):
    cs=json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))
    order=sorted(cs,key=lambda c:severity(c['cfg']))
    idx=np.linspace(0,len(order)-1,K).round().astype(int)
    picks=[order[i]['cid'] for i in idx]
    for must in ('EXP-095','EXP-096','EXP-001'):
        if must not in picks: picks.append(must)
    return [c for c in cs if c['cid'] in picks], picks

def setup_shard_cache(provider,shard):
    import llm_utils
    sc=CACHE/f'llm_cache_{provider}_shard{shard}.json'
    if not sc.exists():
        g=CACHE/'llm_cache.json'
        sc.write_text(g.read_text(encoding='utf-8') if g.exists() else '{}',encoding='utf-8')
    def _paths():
        return sc, RUNS/f'llm_calls_{provider}_shard{shard}.jsonl'
    llm_utils._paths=_paths
    return sc

def run_pair(cfg,cid,seed,use_llm):
    m=EvacModel(seed=seed,use_llm=use_llm,tag=f'{cid}-{"LLM" if use_llm else "HEU"}',**cfg)
    s=m.run(900)
    run={'cid':cid,'seed':seed,'engine':'llm' if use_llm else 'heur',
         'n':m.n,'evacuated':s['evacuated'],'rescued':s['rescued'],
         'stranded':s['stranded'],'deceased':s['deceased'],
         'evac_rate':round(s['evacuated']/m.n,4),'rescue_dep':round(s['rescued']/m.n,4)}
    inds=[]
    for a in m.agents:
        r={'cid':cid,'seed':seed,'engine':run['engine'],'id':a.id,
           'final_status':a.status,'behavior':behavior_label(a),
           'peak_depth':round(a.peak_depth,2),'exposure_s':round(a.exposure_s,1)}
        r.update({k:a.profile[k] for k in
            ('年龄','性别','角色','风险偏好','水灾经验','熟悉度','行动能力','结伴')})
        inds.append(r)
    return run,inds

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--K',type=int,default=24); ap.add_argument('--R',type=int,default=6)
    ap.add_argument('--shard',type=int,default=0); ap.add_argument('--nshards',type=int,default=4)
    ap.add_argument('--provider',default='deepseek',choices=['deepseek','qwen'])
    ap.add_argument('--llm_only',action='store_true')
    a=ap.parse_args()
    os.environ['LLM_PROVIDER']='backup' if a.provider=='qwen' else ''
    setup_shard_cache(a.provider,a.shard)
    cs,picks=pick_configs(a.K)
    cids=[c['cid'] for c in cs]; cids=sorted(cids,key=lambda x:int(x.split('-')[1]))
    mine=cids[a.shard::a.nshards]
    cfgmap={c['cid']:c['cfg'] for c in cs}
    runf=RUNS/f'真实LLM复现_runs_{a.provider}_shard{a.shard}.csv'
    indf=RUNS/f'真实LLM复现_ind_{a.provider}_shard{a.shard}.csv'
    done=set()
    if runf.exists():
        old=pd.read_csv(runf); done=set(zip(old.cid,old.seed,old.engine))
    run_rows=[]; ind_rows=[]
    seeds=[20241001+k for k in range(a.R)]
    pairs=(True,) if a.llm_only else (False,True)
    for cid in mine:
        for seed in seeds:
            for use_llm in pairs:
                eng='llm' if use_llm else 'heur'
                if (cid,seed,eng) in done: continue
                t0=time.time(); r,inds=run_pair(cfgmap[cid],cid,seed,use_llm)
                run_rows.append(r); ind_rows.extend(inds)
                print('shard%d %s %s s%d %s 自救%.3f 依赖%.3f 死%d (%.0fs)'%(
                    a.shard,a.provider,cid,seed,eng,r['evac_rate'],r['rescue_dep'],r['deceased'],
                    time.time()-t0),flush=True)
        if run_rows:
            pd.DataFrame(run_rows).to_csv(runf,mode='a',index=False,header=not runf.exists(),
                encoding='utf-8-sig')
            pd.DataFrame(ind_rows).to_csv(indf,mode='a',index=False,header=not indf.exists(),
                encoding='utf-8-sig')
            run_rows=[]; ind_rows=[]
    print('shard%d %s done: %s'%(a.shard,a.provider,mine))

if __name__=='__main__':
    main()
