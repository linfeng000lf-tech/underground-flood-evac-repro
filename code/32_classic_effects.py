# -*- coding: utf-8 -*-
"""第5章 步骤2：经典人群行为效应复现。
四类受控对照(各 R 个种子)：播报/从众/熟悉出口/瓶颈；Mann-Whitney U + 效应量；图5-2。"""
import argparse, importlib
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel

SLOW=dict(depth_override=dict(d0=.02,t_seep=5,t_peak=45,t_plat=180,t_end=360,d_peak=.50))
EFFECTS={
 '播报效应':dict(metric='t50',base=dict(),
   groups=[('无播报',dict(broadcast_override=False)),('即时播报',dict(broadcast_override=True))]),
 '从众效应':dict(metric='t50',base={**SLOW,'broadcast_override':False},
   groups=[('独立决策',dict(herding=False)),('允许从众',dict(herding=True))]),
 '熟悉出口效应':dict(metric='t50',base={**SLOW,'broadcast_override':False},
   groups=[('低熟悉',dict(fam_level='low')),('高熟悉',dict(fam_level='high'))]),
 '瓶颈效应':dict(metric='t90',base=dict(broadcast_override=True,start_override='platform'),
   groups=[('窄门/人工放行',dict(exit_width=.6)),('闸机常开',dict(exit_width=4.0))]),
}

def t_frac(m,frac):
    n=m.n
    for r in m.step_rows:
        if r['evacuated']+r['rescued']>=frac*n: return r['t_min']
    return np.nan

def run_cfg(seed,use_llm,cfg):
    m=EvacModel('SCN-001',seed=seed,use_llm=use_llm,tag='effect',**cfg)
    m.run(900); s=m.summary()
    return {'t50':t_frac(m,.5),'t90':t_frac(m,.9),'evac_rate':s['evac_rate']}

def main(R,use_llm):
    from scipy.stats import mannwhitneyu
    rows=[]; data={}
    for eff,spec in EFFECTS.items():
        vals={}
        for glab,gkw in spec['groups']:
            cfg={**spec['base'],**gkw}
            vals[glab]=[run_cfg(20240923+k,use_llm,cfg)[spec['metric']] for k in range(R)]
        (g1,g2)=[g for g,_ in spec['groups']]
        x=pd.Series(vals[g1]).dropna().values; y=pd.Series(vals[g2]).dropna().values
        U,p=mannwhitneyu(x,y,alternative='two-sided'); rbc=1-2*U/(len(x)*len(y))
        data[eff]=(vals,[g for g,_ in spec['groups']])
        rows.append({'效应':eff,'指标':spec['metric'],
          '组1标签':g1,'组1中位数':round(float(np.median(x)),1),
          '组2标签':g2,'组2中位数':round(float(np.median(y)),1),
          'U':round(float(U),1),'p值':round(float(p),6),'效应量r':round(abs(float(rbc)),3),'n':min(len(x),len(y))})
        print(f'{eff}: {g1}={np.median(x):.1f}  {g2}={np.median(y):.1f}  p={p:.5f} r={abs(rbc):.2f}',flush=True)
    pd.DataFrame(rows).to_excel(RUNS/'经典效应检验.xlsx',index=False)
    import json as _json
    (RUNS/'经典效应原始.json').write_text(_json.dumps(
        {eff:{'labs':labs,'vals':vals} for eff,(vals,labs) in data.items()},
        ensure_ascii=False,default=lambda o:None),encoding='utf-8')
    draw(data)

def draw(data):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    rng=np.random.default_rng(7)
    fig,axes=plt.subplots(1,4,figsize=(15,4.4))
    for ax,(eff,(vals,labs)) in zip(axes,data.items()):
        clean=[pd.Series(vals[g]).dropna().tolist() for g in labs]
        bp=ax.boxplot(clean,tick_labels=labs,patch_artist=True,widths=.5,
                      medianprops=dict(color='#c0392b',lw=1.6),showfliers=False)
        for patch,c in zip(bp['boxes'],['#f3c6b8','#b9d0e6']): patch.set_facecolor(c); patch.set_alpha(.8)
        for i,arr in enumerate(clean,start=1):
            jit=rng.normal(i,.05,len(arr))
            ax.scatter(jit,arr,s=10,color='#34495e',alpha=.55,zorder=3)
        ax.set_title(eff,fontsize=11); ax.tick_params(axis='x',labelsize=8.5,rotation=15)
        ax.set_ylabel('撤离时间 (min)',fontsize=8.5)
    fig.suptitle('图5-2 经典人群疏散行为效应复现（各30次重复；箱线+抖动点）',fontsize=13,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,.93]); fig.savefig(FIG/'fig_经典效应.png',dpi=200,bbox_inches='tight'); plt.close()
    print('已写 fig_经典效应.png')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--R',type=int,default=30)
    ap.add_argument('--llm',action='store_true'); a=ap.parse_args()
    main(a.R,a.llm)
