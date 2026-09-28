# -*- coding: utf-8 -*-
"""第5章 真实LLM分层抽检：按严重度从96配置中抽 k 个(温和→极端)，各跑1个真实LLM run，
与启发式(20重复)对比自救率方向/相关性/区间覆盖，产出 csv、对比表与图，供效度报告引用。"""
import argparse, json, time, importlib
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ('Microsoft YaHei','SimHei'):
    try: font_manager.findfont(f,fallback_to_default=False); plt.rcParams['font.sans-serif']=[f]; break
    except Exception: pass
plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel

def severity(cfg):
    d=cfg['depth_override']; alarm=cfg.get('alarm_min')
    alarm=120 if alarm is None else alarm
    rise=d['d_peak']/max(d['t_peak'],1)
    return rise*2 + d['d_peak'] + alarm/60.0

def main(k):
    configs=json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))
    order=sorted(configs,key=lambda c:severity(c['cfg']))
    idx=np.linspace(0,len(order)-1,k).round().astype(int)
    picks=[order[i] for i in idx]
    rows=[]
    for j,c in enumerate(picks,1):
        t0=time.time()
        m=EvacModel(seed=20240923,use_llm=True,tag=c['cid']+'-LLM',**c['cfg'])
        s=m.run(900)
        rows.append({'cid':c['cid'],'n':m.n,'severity':round(severity(c['cfg']),3),
            'llm_evac_rate':s['evac_rate'],'llm_rescue_dep':s['rescued']/m.n,
            'llm_deceased':s['deceased'],'elapsed_s':round(time.time()-t0,1)})
        print('[%d/%d] %s 自救%.3f 依赖%.3f 死亡%d (%.0fs)'%(
            j,k,c['cid'],s['evac_rate'],s['rescued']/m.n,s['deceased'],time.time()-t0),flush=True)
    llm=pd.DataFrame(rows)
    llm.to_csv(RUNS/'批量实验_LLM抽检.csv',index=False,encoding='utf-8-sig')

    # 与启发式对比
    cfgmean=pd.read_excel(RUNS/'批量实验_配置均值.xlsx')
    runlvl=pd.read_csv(RUNS/'批量实验_run级.csv')
    rng=runlvl.groupby('cid').agg(evac_min=('evac_rate','min'),evac_max=('evac_rate','max')).reset_index()
    cmp=llm.merge(cfgmean[['cid','evac_rate','rescue_dep']],on='cid').merge(rng,on='cid')
    cmp['in_range']=(cmp.llm_evac_rate>=cmp.evac_min-1e-9)&(cmp.llm_evac_rate<=cmp.evac_max+1e-9)
    cmp['abs_err']=(cmp.llm_evac_rate-cmp.evac_rate).abs()
    pearson=cmp.llm_evac_rate.corr(cmp.evac_rate,method='pearson')
    spearman=cmp.llm_evac_rate.corr(cmp.evac_rate,method='spearman')
    mae=cmp.abs_err.mean(); coverage=cmp.in_range.mean()
    deaths_match=(cmp.llm_deceased==0).all()
    cmp.to_excel(RUNS/'LLM抽检_一致性对比.xlsx',index=False)

    fig,ax=plt.subplots(figsize=(6.2,5.6))
    ax.scatter(cmp.evac_rate,cmp.llm_evac_rate,s=45,c='#2f6db0',alpha=.8,zorder=3)
    lims=[min(cmp.evac_rate.min(),cmp.llm_evac_rate.min())-.05,1.02]
    ax.plot(lims,lims,'--',c='gray',lw=1,zorder=1)
    for _,r in cmp.iterrows():
        ax.annotate(r.cid.replace('EXP-',''),(r.evac_rate,r.llm_evac_rate),
                    xytext=(4,3),textcoords='offset points',fontsize=7)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel('启发式引擎 自救撤离率（20重复均值）'); ax.set_ylabel('真实LLM 自救撤离率')
    ax.set_title('图5-8 真实LLM抽检与启发式结果一致性\nPearson r=%.2f，Spearman ρ=%.2f，区间覆盖%.0f%%，MAE=%.3f'%(
        pearson,spearman,coverage*100,mae))
    ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(FIG/'fig_LLM抽检一致性.png',dpi=150)
    print('\n==== 一致性 ====')
    print('Pearson %.3f；Spearman %.3f；MAE %.3f；区间覆盖 %.2f；死亡全0=%s'%(
        pearson,spearman,mae,coverage,deaths_match))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--k',type=int,default=16)
    main(ap.parse_args().k)
