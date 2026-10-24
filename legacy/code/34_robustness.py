# -*- coding: utf-8 -*-
"""第5章 步骤4：多模型/参数稳健性与敏感性分析。
稳健性：更换 dt、决策间隔、随机种子，结论方向是否稳定；
敏感性：关键参数 OAT 低/高对【自救撤离率】的影响 → 龙卷风图(图5-4)；存活率在极端才变化，一并记录。"""
import argparse, importlib
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel

# 基准：快涨深水、报警偏晚、救援中等——自救撤离率处于敏感中段
BASE=dict(sid='SCN-001',rescue_min=45,alarm_min=30,
          depth_override=dict(d0=.03,t_seep=3,t_peak=25,t_plat=160,t_end=480,d_peak=1.3))
def hydro(dpk,tpk=25):
    return dict(depth_override=dict(d0=.03,t_seep=3,t_peak=tpk,t_plat=160,t_end=480,d_peak=dpk))
FACTORS={  # 因子: (低配置, 高配置)
 '峰值水深': (hydro(.6),hydro(1.8)),
 '报警时机': (dict(alarm_min=10),dict(alarm_min=60)),
 '人群规模': (dict(n=60),dict(n=240)),
 '熟悉度':   (dict(fam_level='high'),dict(fam_level='low')),
 '救援到达': (dict(rescue_min=20),dict(rescue_min=55)),
 '出口宽度': (dict(exit_width=1.0),dict(exit_width=4.0)),
 '积水速率': (hydro(1.3,tpk=70),hydro(1.3,tpk=15)),
 '决策间隔': (dict(decision_interval=1),dict(decision_interval=8)),
}

def run_out(seed,cfg,R):
    ev=[]; sv=[]
    for k in range(R):
        m=EvacModel(seed=seed+k,tag='sens',**cfg); m.run(900); s=m.summary()
        ev.append(s['evac_rate']); sv.append(s['survive_rate'])
    return float(np.median(ev)),float(np.median(sv))

def main(R):
    be,bs=run_out(20240923,BASE,R); rows=[]
    for fac,(lo,hi) in FACTORS.items():
        el,_=run_out(20240923,{**BASE,**lo},R); eh,_=run_out(20240923,{**BASE,**hi},R)
        _,sl=run_out(20240923,{**BASE,**lo},R); _,sh=run_out(20240923,{**BASE,**hi},R)
        rows.append({'因子':fac,'低自救率':round(el,3),'高自救率':round(eh,3),
                     '极差':round(abs(eh-el),3),'低存活率':round(sl,3),'高存活率':round(sh,3),
                     '低-基准':round(el-be,3),'高-基准':round(eh-be,3)})
        print(f'{fac}: 自救 低{el:.2f} 高{eh:.2f} 极差{abs(eh-el):.2f} | 存活 {sl:.2f}/{sh:.2f}',flush=True)
    pd.DataFrame(rows).to_excel(RUNS/'敏感性分析.xlsx',index=False)
    robustness(R); draw(rows,be)

def robustness(R):
    cfgs={'基准':dict(),'dt=5s':dict(dt_s=5),'dt=20s':dict(dt_s=20),
          '决策间隔=1':dict(decision_interval=1),'决策间隔=8':dict(decision_interval=8)}
    rows=[]
    for cname,extra in cfgs.items():
        ev=[]; sv=[]
        for k in range(R):
            m=EvacModel(seed=3050000+k,tag='rob',**{**BASE,**extra}); m.run(900); s=m.summary()
            ev.append(s['evac_rate']); sv.append(s['survive_rate'])
        rows.append({'配置':cname,'自救率中位数':round(float(np.median(ev)),3),
                     '自救率5%':round(float(np.percentile(ev,5)),3),'自救率95%':round(float(np.percentile(ev,95)),3),
                     '存活率中位数':round(float(np.median(sv)),3)})
        print(f'稳健性 {cname}: 自救{np.median(ev):.3f} 存活{np.median(sv):.3f}',flush=True)
    pd.DataFrame(rows).to_excel(RUNS/'稳健性分析.xlsx',index=False)

def draw(rows,base):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    rows=sorted(rows,key=lambda r:r['极差'])
    fig,ax=plt.subplots(figsize=(9.5,5)); y=np.arange(len(rows))
    for yi,r in zip(y,rows):
        ax.barh(yi,r['高-基准'],left=base,color='#d98c7a',height=.6)
        ax.barh(yi,r['低-基准'],left=base,color='#7fa8d0',height=.6)
    ax.axvline(base,color='#333',lw=1.2,ls='--')
    ax.text(base,len(rows)+.15,f'基准 {base:.2f}',ha='center',fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels([r['因子'] for r in rows])
    ax.set_xlabel('自救撤离率'); ax.set_xlim(0,1.02)
    ax.set_title('图5-4 参数敏感性龙卷风图（蓝=低水平，红=高水平）',fontsize=12.5,fontweight='bold')
    fig.tight_layout(); fig.savefig(FIG/'fig_敏感性.png',dpi=200,bbox_inches='tight'); plt.close()
    print('已写 fig_敏感性.png')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--R',type=int,default=12); a=ap.parse_args()
    main(a.R)
