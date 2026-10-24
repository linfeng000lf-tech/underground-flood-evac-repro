# -*- coding: utf-8 -*-
"""第5章 跨模型复现：在相同16个分层配置上用千问(qwen-plus)真实LLM各跑1个run，
与启发式(20重复均值/区间)、DeepSeek结果做三向对比，检验安全结论是否依赖单一模型。
须在导入引擎前设置 LLM_PROVIDER=backup。产出 csv/xlsx 与 图5-9。"""
import os
os.environ['LLM_PROVIDER']='backup'   # 切换到 .env 的 BACKUP（千问）
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
    d=cfg['depth_override']; alarm=cfg.get('alarm_min'); alarm=120 if alarm is None else alarm
    rise=d['d_peak']/max(d['t_peak'],1)
    return rise*2 + d['d_peak'] + alarm/60.0

def main(k, force=False):
    out_csv=RUNS/'批量实验_千问抽检.csv'
    configs=json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))
    order=sorted(configs,key=lambda c:severity(c['cfg']))
    idx=np.linspace(0,len(order)-1,k).round().astype(int)
    picks=[order[i] for i in idx]
    if out_csv.exists() and not force:
        qw=pd.read_csv(out_csv)
    else:
        rows=[]
        for j,c in enumerate(picks,1):
            t0=time.time()
            m=EvacModel(seed=20240923,use_llm=True,tag=c['cid']+'-QW',**c['cfg'])
            s=m.run(900)
            rows.append({'cid':c['cid'],'n':m.n,'severity':round(severity(c['cfg']),3),
                'qw_evac_rate':s['evac_rate'],'qw_rescue_dep':s['rescued']/m.n,
                'qw_deceased':s['deceased'],'elapsed_s':round(time.time()-t0,1)})
            print('[%d/%d] %s 自救%.3f 依赖%.3f 死亡%d (%.0fs)'%(
                j,k,c['cid'],s['evac_rate'],s['rescued']/m.n,s['deceased'],time.time()-t0),flush=True)
        qw=pd.DataFrame(rows); qw.to_csv(out_csv,index=False,encoding='utf-8-sig')

    cfgmean=pd.read_excel(RUNS/'批量实验_配置均值.xlsx')
    runlvl=pd.read_csv(RUNS/'批量实验_run级.csv')
    ds=pd.read_csv(RUNS/'批量实验_LLM抽检.csv')
    rng=runlvl.groupby('cid').agg(heu_min=('evac_rate','min'),heu_max=('evac_rate','max')).reset_index()
    C=(qw.merge(cfgmean[['cid','evac_rate']].rename(columns={'evac_rate':'heu_evac_rate'}),on='cid')
         .merge(ds[['cid','llm_evac_rate','llm_deceased']],on='cid').merge(rng,on='cid'))
    C['ds_in_range']=(C.llm_evac_rate>=C.heu_min-1e-9)&(C.llm_evac_rate<=C.heu_max+1e-9)
    C['qw_in_range']=(C.qw_evac_rate>=C.heu_min-1e-9)&(C.qw_evac_rate<=C.heu_max+1e-9)
    def sp(a,b): return C[a].corr(C[b],method='spearman')
    stats={
      'spearman_heu_ds':round(sp('heu_evac_rate','llm_evac_rate'),3),
      'spearman_heu_qw':round(sp('heu_evac_rate','qw_evac_rate'),3),
      'spearman_ds_qw':round(sp('llm_evac_rate','qw_evac_rate'),3),
      'mae_heu_ds':round((C.heu_evac_rate-C.llm_evac_rate).abs().mean(),3),
      'mae_heu_qw':round((C.heu_evac_rate-C.qw_evac_rate).abs().mean(),3),
      'mae_ds_qw':round((C.llm_evac_rate-C.qw_evac_rate).abs().mean(),3),
      'all_deaths_zero':bool((C.qw_deceased==0).all() and (C.llm_deceased==0).all()),
      'ds_range_coverage':round(C.ds_in_range.mean(),2),'qw_range_coverage':round(C.qw_in_range.mean(),2)}
    C.to_excel(RUNS/'跨模型_三向对比.xlsx',index=False)

    fig=plt.figure(figsize=(13,5.2))
    ax=fig.add_subplot(1,2,1)
    ax.scatter(C.heu_evac_rate,C.llm_evac_rate,s=40,c='#b0413e',alpha=.85,label='DeepSeek',zorder=3)
    ax.scatter(C.heu_evac_rate,C.qw_evac_rate,s=40,c='#2f6db0',alpha=.85,marker='^',label='千问Qwen',zorder=3)
    lims=[min(C.heu_evac_rate.min(),C.llm_evac_rate.min(),C.qw_evac_rate.min())-.05,1.02]
    ax.plot(lims,lims,'--',c='gray',lw=1)
    ax.set_xlim(lims); ax.set_ylim(lims); ax.grid(alpha=.2)
    ax.set_xlabel('启发式引擎 自救撤离率（20重复均值）'); ax.set_ylabel('真实LLM 自救撤离率')
    ax.set_title('(a) 跨模型一致性\nρ(启发,DeepSeek)=%.2f  ρ(启发,千问)=%.2f  ρ(DeepSeek,千问)=%.2f'%(
        stats['spearman_heu_ds'],stats['spearman_heu_qw'],stats['spearman_ds_qw']))
    ax.legend()
    ax2=fig.add_subplot(1,2,2)
    tail=C.nsmallest(6,'heu_evac_rate').sort_values('heu_evac_rate')
    x=np.arange(len(tail)); w=.26
    ax2.bar(x-w,tail.heu_evac_rate,w,label='启发式',color='#8a8f98')
    ax2.bar(x,tail.llm_evac_rate,w,label='DeepSeek',color='#b0413e')
    ax2.bar(x+w,tail.qw_evac_rate,w,label='千问Qwen',color='#2f6db0')
    ax2.set_xticks(x); ax2.set_xticklabels([t.replace('EXP-','') for t in tail.cid],fontsize=8)
    ax2.set_ylim(0,1.05); ax2.set_ylabel('自救撤离率'); ax2.grid(axis='y',alpha=.2)
    ax2.set_title('(b) 最严重6配置的三引擎对比'); ax2.legend(fontsize=9)
    fig.suptitle('图5-9 跨模型复现：DeepSeek 与 千问Qwen 的三角验证',fontsize=13)
    fig.tight_layout(rect=[0,0,1,0.93]); fig.savefig(FIG/'fig_跨模型复现.png',dpi=200)
    print('\n==== 三向对比 ===='); print(json.dumps(stats,ensure_ascii=False,indent=1))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--k',type=int,default=16)
    ap.add_argument('--force',action='store_true')
    main(ap.parse_args().k,ap.parse_args().force)
