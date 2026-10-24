# -*- coding: utf-8 -*-
"""第5章 步骤1：典型案例回放校准。
真实里程碑(相对首次进水, min) vs 仿真里程碑；输出对照表、图5-1。"""
import json, argparse, importlib
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel

# 真实参照（据案例资料；milestones=(事件,相对min)）
REF={
 '郑州地铁5号线 7·20':{
   'sid':'SCN-004','rescue':60,
   'milestones':[('涝水涌入隧道',0),('列车迫停',47),('线网停运',64),('疏散被迫中断',97),('上报集团',168)],
   'survive':(953,967),'note':'无及时报警/组织广播，乘客自行疏散、后期靠救援'},
 '北京金安桥站 7·18':{
   'sid':'SCN-001','rescue':None,
   'milestones':[('积水进站',0),('车站封闭公告',28),('消防到场',50),('排涝完成',260)],
   'survive':(None,None),'note':'站内积水没踝、乘客蹚水，封闭后引导出站，无伤亡'},
}

def sim_milestones(m):
    rows=m.step_rows; n=m.n
    def t_at(frac):
        for r in rows:
            done=r['evacuated']+r['rescued']
            if done>=frac*n: return r['t_min']
        return np.nan
    t_start=np.nan
    for r in rows:
        if (r['evacuated']+r['rescued']+r['stranded']+r['deceased'])>0:
            t_start=r['t_min']; break
    return [('开始有人离开',t_start),('50%撤离',t_at(.5)),('90%撤离',t_at(.9))]

def run_one(name,cfg,n,use_llm,seed):
    m=EvacModel(cfg['sid'],n=n,use_llm=use_llm,rescue_min=cfg['rescue'],seed=seed,tag='calib')
    m.run(360)
    sm=sim_milestones(m); r=m.summary()
    return m,r,sm

def draw(records):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(1,len(records),figsize=(13,4.6),squeeze=False)
    for ax,(name,cfg,r,sm) in zip(axes[0],records):
        for lab,t in cfg['milestones']:
            ax.scatter(t,1,color='#c0392b',zorder=3,s=34)
            ax.annotate(lab,(t,1),xytext=(t,1.18),ha='center',fontsize=7.4,rotation=30)
        for lab,t in sm:
            ax.scatter(t,0,color='#2e5e8c',zorder=3,s=34,marker='s')
            ax.annotate(lab,(t,0),xytext=(t,-.22),ha='center',fontsize=7.4,color='#2e5e8c')
        ax.axhline(1,color='#e6b3aa',lw=.8); ax.axhline(0,color='#a9c2dc',lw=.8)
        ax.set_ylim(-.6,1.7); ax.set_yticks([0,1]); ax.set_yticklabels(['仿真','真实'])
        ax.set_title(f'{name}\n存活率 仿真{r["survive_rate"]}',fontsize=9.5)
    fig.suptitle('图5-1 典型案例回放：真实 vs 仿真关键时间线',fontsize=13,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,.93]); fig.savefig(FIG/'fig_案例回放.png',dpi=200,bbox_inches='tight'); plt.close()
    print('已写 fig_案例回放.png')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--n',type=int,default=60)
    ap.add_argument('--llm',action='store_true'); ap.add_argument('--seed',type=int,default=20240923)
    a=ap.parse_args(); recs=[]
    for name,cfg in REF.items():
        m,r,sm=run_one(name,cfg,a.n,a.llm,a.seed); recs.append((name,cfg,r,sm))
        print('\n===',name,'(',cfg["sid"],') 真实:',cfg['note'])
        print(' 真实里程碑:',[(l,round(t,1)) for l,t in cfg['milestones']])
        print(' 仿真里程碑:',[(l,None if pd.isna(t) else round(t,1)) for l,t in sm])
        print(' 仿真结果:',{k:r[k] for k in ['evacuated','rescued','stranded','deceased','survive_rate']})
        m.save()
    pd.DataFrame([{'案例':n,'情景':c['sid'],'仿真存活':r['survive_rate'],
        '仿真受困':r['stranded'],'仿真致死风险':r['deceased']} for n,c,r,_ in recs]
        ).to_excel(RUNS/'校准对照表.xlsx',index=False)
    draw(recs)
