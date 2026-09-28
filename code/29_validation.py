# -*- coding: utf-8 -*-
"""第4章 实验设置科学性验证（离线启发式，不调用LLM、不花钱）。
控制变量的五类证据：
 A 峰值水深剂量反应（报警=0，控制响应，隔离物理严重性）；
 B 报警时机（固定.93m，无报警时风险正常化）；
 C 人群规模（C1轻度看通行时间/容量，C2严重看存活率）；
 D 多种子稳健性（三个受控、结局有序的条件×12种子）；
 E 机制开关（无报警，检验从众/熟悉度的独立作用）。
输出 results/runs/validation_*.xlsx 与 results/figures/fig_科学性_*.png。"""
import importlib
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']; plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
EvacModel=importlib.import_module('26_mesa_engine').EvacModel

def run_one(sid='SCN-001',n=120,steps=420,seed=11,depth_override=None,
             alarm_min='UNSET',herding=True,fam_level=None):
    m=EvacModel(sid,n=n,seed=seed,depth_override=depth_override,alarm_min=alarm_min,
                herding=herding,fam_level=fam_level,tag='validation')
    m.run(steps); r=m.summary(); et=r['evac_times']
    return {'evac_rate':r['evac_rate'],'survive_rate':r['survive_rate'],
            'stranded_frac':round(r['stranded']/m.n,3),
            'deceased_frac':round(r['deceased']/m.n,3),
            'mean_evac_min':round(float(np.mean(et)),2) if et else None}

def agg(rows,key):
    v=[r[key] for r in rows if r[key] is not None]
    return (round(float(np.mean(v)),3),round(float(np.std(v)),3)) if v else (None,None)

SEEDS=(11,22,33)

# ---- A 剂量反应（立即 vs 延迟报警）----
def exp_dose():
    dps=[.15,.29,.40,.50,.58,.70,.93,1.13,1.37,1.60,1.89]; out=[]
    dseeds=(11,22,33,44,55,66,77,88,99,111)
    for d in dps:
        early=[run_one('SCN-001',seed=s,depth_override={'d_peak':d},alarm_min=0) for s in dseeds]
        late=[run_one('SCN-001',seed=s,depth_override={'d_peak':d},alarm_min=25) for s in dseeds]
        e0,_=agg(early,'survive_rate'); el,_=agg(late,'survive_rate')
        dl,_=agg(late,'deceased_frac')
        out.append({'d_peak':d,'survive_alarm0':e0,'survive_alarm25':el,'deceased_alarm25':dl})
    df=pd.DataFrame(out); df.to_excel(RUNS/'validation_dose.xlsx',index=False)
    fig,ax=plt.subplots(figsize=(8.4,5))
    ax.plot(df.d_peak,df.survive_alarm0,'-o',color='#2e9e44',label='存活率(报警0min)')
    ax.plot(df.d_peak,df.survive_alarm25,'-^',color='#2e6fb2',label='存活率(报警25min)')
    ax.plot(df.d_peak,df.deceased_alarm25,'-s',color='#c0392b',label='死亡占比(报警25min)')
    for x,t in [(.30,'出口关闭.30'),(.70,'平地限.70'),(1.37,'失稳1.37')]:
        ax.axvline(x,ls='--',color='#bbb',lw=1); ax.text(x,.97,t,rotation=90,fontsize=7.5,va='top')
    ax.set_xlabel('峰值水深 d_peak (m)'); ax.set_ylabel('比例'); ax.set_ylim(-.03,1.05)
    ax.set_title('图A 峰值水深—结局 剂量反应（响应时机的交互）'); ax.legend()
    fig.tight_layout(); fig.savefig(FIG/'fig_科学性_剂量反应.png',dpi=170); plt.close()
    return df

# ---- B 报警时机（固定.93m）----
def exp_alarm():
    alarms=[0,5,10,15,25,'NONE']; out=[]
    for a in alarms:
        rows=[run_one('SCN-003',seed=s,alarm_min=(None if a=='NONE' else a)) for s in SEEDS]
        sm,_=agg(rows,'survive_rate'); em,_=agg(rows,'evac_rate')
        out.append({'alarm_x':(40 if a=='NONE' else a),'alarm_min':str(a),
                    'survive_rate':sm,'evac_rate':em})
    df=pd.DataFrame(out); df.to_excel(RUNS/'validation_alarm.xlsx',index=False)
    fig,ax=plt.subplots(figsize=(8,5)); x=df.alarm_x
    ax.plot(x,df.survive_rate,'-o',color='#2e9e44',label='存活率')
    ax.plot(x,df.evac_rate,'-^',color='#2e6fb2',label='撤离率')
    ax.set_xticks(list(x)); ax.set_xticklabels([0,5,10,15,25,'无'])
    ax.set_xlabel('报警时刻 (min)'); ax.set_ylabel('比例'); ax.set_ylim(-.03,1.05)
    ax.set_title('图B 报警时机—结局（峰值.93m）'); ax.legend()
    fig.tight_layout(); fig.savefig(FIG/'fig_科学性_报警时机.png',dpi=170); plt.close()
    return df

# ---- C 人群规模 ----
def exp_population():
    ns=[20,60,120,200,300,400]; t=[]; s=[]
    for n in ns:
        mild=[run_one('SCN-002',n=n,steps=600,seed=sd) for sd in SEEDS]
        sev=[run_one('SCN-003',n=n,steps=600,seed=sd,alarm_min=12) for sd in SEEDS]
        tm,_=agg(mild,'mean_evac_min'); sm,_=agg(sev,'survive_rate')
        t.append({'n':n,'mean_evac_min':tm}); s.append({'n':n,'survive_rate':sm})
    dt=pd.DataFrame(t); ds=pd.DataFrame(s)
    dt.to_excel(RUNS/'validation_population_time.xlsx',index=False)
    ds.to_excel(RUNS/'validation_population_survive.xlsx',index=False)
    fig,axes=plt.subplots(1,2,figsize=(13,4.6))
    axes[0].plot(dt.n,dt.mean_evac_min,'-o',color='#e08a2e')
    axes[0].set_xlabel('站内人数 n'); axes[0].set_ylabel('平均撤离时间 (min)')
    axes[0].set_title('图C1 人群规模—通行时间（轻度.29m，立即报警）')
    axes[1].plot(ds.n,ds.survive_rate,'-o',color='#c0392b')
    axes[1].set_xlabel('站内人数 n'); axes[1].set_ylabel('存活率')
    axes[1].set_ylim(-.03,1.05); axes[1].set_title('图C2 人群规模—存活率（.93m，报警12min）')
    fig.tight_layout(); fig.savefig(FIG/'fig_科学性_人群规模.png',dpi=170); plt.close()
    return dt,ds

# ---- D 多种子稳健性（受控、结局有序）----
def exp_robust(seeds=tuple(range(1,13))):
    conds=[('轻度 (.29m,报警0)',{'depth_override':{'d_peak':.29},'alarm_min':0}),
           ('中度 (.93m,报警15)',{'depth_override':{'d_peak':.93},'alarm_min':15}),
           ('严重 (.93m,报警25)',{'depth_override':{'d_peak':.93},'alarm_min':25})]
    box=[]; summ=[]
    for nm,kw in conds:
        rows=[run_one('SCN-001',seed=s,**kw) for s in seeds]
        v=[r['survive_rate'] for r in rows]; box.append(v)
        summ.append({'condition':nm,'mean':round(np.mean(v),3),'sd':round(np.std(v),3),
                     'min':min(v),'max':max(v)})
    pd.DataFrame(summ).to_excel(RUNS/'validation_robustness.xlsx',index=False)
    fig,ax=plt.subplots(figsize=(9,5))
    bp=ax.boxplot(box,tick_labels=[c[0] for c in conds],patch_artist=True,widths=.55)
    for patch,c in zip(bp['boxes'],['#bfe3c8','#f6e0b8','#f3c6bd']): patch.set_facecolor(c)
    ax.set_ylabel('存活率'); ax.set_ylim(-.03,1.05)
    ax.set_title('图D 12个随机种子下存活率分布（稳健性）')
    plt.setp(ax.get_xticklabels(),fontsize=8.5)
    fig.tight_layout(); fig.savefig(FIG/'fig_科学性_稳健性.png',dpi=170); plt.close()
    return pd.DataFrame(summ)

# ---- E 机制开关（无报警）----
def exp_mechanism():
    cfgs=[('基准(从众开)','UNSET',True,None),('关闭从众','UNSET',False,None),
          ('熟悉度高','UNSET',True,'high'),('熟悉度低','UNSET',True,'low')]
    out=[]
    for nm,al,hd,fl in cfgs:
        rows=[run_one('SCN-003',seed=s,alarm_min=None,herding=hd,fam_level=fl) for s in SEEDS]
        sm,_=agg(rows,'survive_rate'); em,_=agg(rows,'evac_rate')
        out.append({'config':nm,'survive_rate':sm,'evac_rate':em})
    df=pd.DataFrame(out); df.to_excel(RUNS/'validation_mechanism.xlsx',index=False)
    fig,ax=plt.subplots(figsize=(8.6,5)); x=np.arange(len(df)); w=.38
    ax.bar(x-w/2,df.survive_rate,w,label='存活率',color='#2e9e44')
    ax.bar(x+w/2,df.evac_rate,w,label='撤离率',color='#2e6fb2')
    ax.set_xticks(x); ax.set_xticklabels(df.config,fontsize=8.5)
    ax.set_ylim(0,1.05); ax.set_title('图E 机制开关—结局（.93m，无报警）'); ax.legend()
    fig.tight_layout(); fig.savefig(FIG/'fig_科学性_机制开关.png',dpi=170); plt.close()
    return df

if __name__=='__main__':
    print('A...'); da=exp_dose()
    print('B...'); db=exp_alarm()
    print('C...'); dct,dcs=exp_population()
    print('D...'); dr=exp_robust()
    print('E...'); de=exp_mechanism()
    print('\nA 剂量反应:\n',da.to_string(index=False))
    print('\nB 报警时机:\n',db[['alarm_min','survive_rate','evac_rate']].to_string(index=False))
    print('\nC1 通行时间:\n',dct.to_string(index=False))
    print('\nC2 存活率:\n',dcs.to_string(index=False))
    print('\nD 稳健性:\n',dr.to_string(index=False))
    print('\nE 机制:\n',de.to_string(index=False))
    print('\n科学性验证完成。')
