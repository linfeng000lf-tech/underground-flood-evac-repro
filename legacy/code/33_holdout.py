# -*- coding: utf-8 -*-
"""第5章 步骤3：留出案例外推验证。
校准仅用金安桥/郑州；对未参与校准的真实案例(金沙湖/神舟路/福州/上海)做盲预测，
对比文档化的存活率、死亡数与首次撤离时间；区间覆盖 + 误差；图5-3。"""
import argparse, importlib
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel

# 神舟路为情景库外案例：在建出入口挡水墙突然倒塌(进水口gate、快涨)，+10min启动预案
SHENZHOU=dict(depth_override=dict(d0=.02,t_seep=2,t_peak=20,t_plat=120,t_end=360,d_peak=.60),
              alarm_min=10)
HOLDOUTS={
 '金沙湖站5·18管涌': dict(sid='SCN-021',exit_width=4.0,rescue_min=60,alarm_min=5,
    actual=dict(survive=1.00,deceased=0,t_first=5)),
 '神舟路站挡水墙倒塌': dict(sid='SCN-001',rescue_min=60,**SHENZHOU,
    actual=dict(survive=1.00,deceased=0,t_first=10)),
 '福州地铁台风海葵': dict(sid='SCN-025',rescue_min=60,
    actual=dict(survive=1.00,deceased=0,t_first=5)),
 '上海天潼路消防管爆裂': dict(sid='SCN-026',rescue_min=60,
    actual=dict(survive=1.00,deceased=0,t_first=0)),
}

def first_evac(m):
    for r in m.step_rows:
        if r['evacuated']>=1: return r['t_min']
    return np.nan

def run_case(name,cfg,R,use_llm):
    actual=cfg.pop('actual'); sid=cfg.pop('sid')
    surv=[]; dec=[]; tf=[]
    for k in range(R):
        m=EvacModel(sid,seed=20240923+k,use_llm=use_llm,tag='holdout',**cfg)
        m.run(900); s=m.summary()
        surv.append(s['survive_rate']); dec.append(s['deceased']/m.n); tf.append(first_evac(m))
    return name,actual,surv,dec,tf

def cover(actual,arr):
    lo,hi=np.percentile(arr,[5,95]); return lo<=actual<=hi,round(lo,2),round(hi,2)

def main(R,use_llm):
    rows=[]; pred={}
    for name,cfg in HOLDOUTS.items():
        nm,actual,surv,dec,tf=run_case(name,cfg,R,use_llm); pred[nm]=(actual,surv,dec,tf)
        cs,lo,hi=cover(actual['survive'],surv); ct,lot,hit=cover(actual['t_first'],tf)
        mae_t=float(np.nanmedian(np.abs(np.array(tf)-actual['t_first'])))
        rows.append({'案例':nm,'实际存活率':actual['survive'],'预测存活率中位数':round(float(np.median(surv)),3),
          '存活率90%区间':f'[{lo},{hi}]','存活率覆盖':cs,
          '实际首次撤离(min)':actual['t_first'],'预测首次撤离中位数':round(float(np.nanmedian(tf)),1),
          '首次撤离90%区间':f'[{lot},{hit}]','时间覆盖':ct,'时间|误差|中位数':round(mae_t,1),
          '预测死亡数(均)':round(float(np.mean(dec)),3),'实际死亡数':actual['deceased']})
        print(f'{nm}: 存活{np.median(surv):.2f}(实{actual["survive"]}) '
              f'首撤{np.nanmedian(tf):.1f}(实{actual["t_first"]}) 死亡{np.mean(dec):.2f}',flush=True)
    pd.DataFrame(rows).to_excel(RUNS/'留出验证.xlsx',index=False)
    # 分类指标：死亡全部应为0（安全案例特异性）
    all_dec=np.concatenate([pred[n][2] for n in pred])
    spec=float(np.mean(all_dec==0))
    print(f'安全案例死亡=0 特异性 {spec:.2f}；时间覆盖 {sum(r["时间覆盖"] for r in rows)}/{len(rows)}；'
          f'存活率覆盖 {sum(r["存活率覆盖"] for r in rows)}/{len(rows)}',flush=True)
    draw(pred)

def draw(pred):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(1,2,figsize=(11,4.6))
    # 左：首次撤离时间 预测vs实际
    ax=axes[0]
    for nm,(actual,surv,dec,tf) in pred.items():
        med=np.nanmedian(tf); lo,hi=np.nanpercentile(tf,[25,75])
        ax.errorbar(actual['t_first'],med,yerr=[[med-lo],[hi-med]],fmt='o',ms=8,
                    color='#2c6fbb',ecolor='#9bb8d6',capsize=4)
    lim=[0,max([actual['t_first'] for actual,*_ in pred.values()]+
                [np.nanmedian(pred[n][3]) for n in pred])+5]
    ax.plot(lim,lim,'--',color='#c0392b',lw=1.2,label='y=x 理想线')
    ax.set_xlim(lim); ax.set_ylim(lim); ax.set_xlabel('文档化首次撤离时间 (min)')
    ax.set_ylabel('模型预测首次撤离时间 (min)'); ax.set_title('首次撤离时间 预测 vs 实际',fontsize=11); ax.legend()
    # 右：存活率 预测分布 vs 实际
    ax=axes[1]; names=list(pred)
    x=np.arange(len(names))
    med=[np.median(pred[n][1]) for n in names]
    lo=[np.percentile(pred[n][1],5) for n in names]; hi=[np.percentile(pred[n][1],95) for n in names]
    act=[pred[n][0]['survive'] for n in names]
    ax.errorbar(x,med,yerr=[np.array(med)-np.array(lo),np.array(hi)-np.array(med)],
                fmt='s',ms=8,color='#2c6fbb',ecolor='#9bb8d6',capsize=4,label='预测(90%区间)')
    ax.scatter(x,act,marker='*',s=160,color='#c0392b',label='实际',zorder=5)
    ax.set_xticks(x); ax.set_xticklabels([n.replace('站','\n站') for n in names],fontsize=8)
    ax.set_ylim(.6,1.05); ax.set_ylabel('存活率'); ax.set_title('存活率 预测 vs 实际',fontsize=11); ax.legend()
    fig.suptitle('图5-3 留出案例外推验证（未参与校准的真实案例）',fontsize=13,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,.93]); fig.savefig(FIG/'fig_留出验证.png',dpi=200,bbox_inches='tight'); plt.close()
    print('已写 fig_留出验证.png')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--R',type=int,default=20)
    ap.add_argument('--llm',action='store_true'); a=ap.parse_args()
    main(a.R,a.llm)
