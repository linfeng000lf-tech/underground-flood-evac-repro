# -*- coding: utf-8 -*-
"""第5章 步骤5：大规模计算实验矩阵设计。
8 个受控因子(表15/17)；全因子4374组合过大，用拉丁超立方(LHS)抽样降维；
映射为引擎参数，输出实验设计表(表5-2)与批量配置；估算运行规模与API成本。"""
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats.qmc import LatinHypercube
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'

# 因子: 名称 -> (水平列表, 引擎键, 水平→参数)
FACTORS={
 '进水位置': (['出入口','隧道','风亭'],'entry_override',{'出入口':'gate_A','隧道':'interval','风亭':'wind'}),
 '峰值水深m': ([.6,1.2,1.8],'d_peak',{.6:.6,1.2:1.2,1.8:1.8}),
 '积水速率': (['慢','中','快'],'t_peak',{'慢':90,'中':45,'快':20}),
 '人群密度': ([.5,1.2,2.0],'n',{.5:60,1.2:140,2.0:240}),
 '熟悉度比例': ([.2,.4,.6],'fam_frac',{.2:.2,.4:.4,.6:.6}),
 '播报时机': (['无','早','晚'],'alarm',{'无':None,'早':10,'晚':40}),
 '闸机管控': (['常开','人工'],'exit_width',{'常开':4.0,'人工':.8}),
 '救援到达min': ([20,35,50],'rescue',{20:20,35:35,50:50}),
}
HYDRO_BASE=dict(d0=.03,t_seep=5,t_plat=160,t_end=480)

def sample_design(N,seed):
    D=len(FACTORS); lvl_counts=[len(v[0]) for v in FACTORS.values()]
    lhs=LatinHypercube(d=D,seed=seed).random(N)
    idx=np.floor(lhs*np.array(lvl_counts)).astype(int)
    idx=np.clip(idx,0,np.array(lvl_counts)-1)
    # 去重(以水平索引元组)
    seen=set(); rows=[]
    for r in idx:
        t=tuple(r)
        if t in seen: continue
        seen.add(t); rows.append(r)
    return rows

def to_config(level_idx):
    names=list(FACTORS); setting={}; cfg=dict(sid='SCN-001')
    depth=dict(HYDRO_BASE)
    for ni,li in enumerate(level_idx):
        name=names[ni]; levels,key,mp=FACTORS[name]; lvl=levels[li]; setting[name]=lvl
        val=mp[lvl]
        if key=='d_peak': depth['d_peak']=val
        elif key=='t_peak': depth['t_peak']=val
        elif key=='alarm': cfg['alarm_min']=val
        elif key=='rescue': cfg['rescue_min']=val
        else: cfg[key]=val
    cfg['depth_override']=depth
    return setting,cfg

def main(N,R,seed,llm_subset):
    designs=sample_design(N,seed)
    recs=[]; configs=[]
    for i,li in enumerate(designs):
        setting,cfg=to_config(li); cid=f'EXP-{i+1:03d}'
        recs.append({'实验编号':cid,**setting}); configs.append({'cid':cid,'cfg':cfg})
    df=pd.DataFrame(recs)
    with pd.ExcelWriter(RUNS/'实验设计表.xlsx') as w:
        df.to_excel(w,sheet_name='实验矩阵',index=False)
        pd.DataFrame([{'因子':k,'水平':','.join(map(str,v[0]))} for k,v in FACTORS.items()]
            ).to_excel(w,sheet_name='因子水平',index=False)
    (RUNS/'批量配置.json').write_text(json.dumps(configs,ensure_ascii=False,indent=1),encoding='utf-8')
    ncfg=len(configs); total=ncfg*R
    print(f'LHS设计点 {ncfg}（全因子{int(np.prod([len(v[0]) for v in FACTORS.values()]))}）；'
          f'每点R={R} → 总运行 {total} 次',flush=True)
    # 成本估算：启发式离线0元；LLM每run约决策次数×单价
    est_calls_per_run=40  # 中等情景每run约40次决策调用(自适应间隔后)
    llm_runs=llm_subset
    print(f'建议：主体{total}次用启发式离线(0元)；真实LLM仅抽检 {llm_runs} 个run，'
          f'约 {llm_runs*est_calls_per_run} 次调用(DeepSeek约几元)。',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--N',type=int,default=96,help='LHS设计点数')
    ap.add_argument('--R',type=int,default=20,help='每点重复次数')
    ap.add_argument('--seed',type=int,default=20240923)
    ap.add_argument('--llm_subset',type=int,default=36)
    a=ap.parse_args(); main(a.N,a.R,a.seed,a.llm_subset)
