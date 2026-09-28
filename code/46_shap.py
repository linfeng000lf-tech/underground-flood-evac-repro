# -*- coding: utf-8 -*-
"""第6章 步骤6：可解释性（XGBoost 原生 TreeSHAP 贡献值，规避 shap 与 xgb3.2 解析冲突）。
产出：图6-6 风险因子全局重要性(归并原始变量)、图6-7 蜂群图+关键因子边际方向、
图6-8 各行为类别因子重要性；并落盘重要性表。"""
import importlib, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ('Microsoft YaHei','SimHei'):
    try: font_manager.findfont(f,fallback_to_default=False); plt.rcParams['font.sans-serif']=[f]; break
    except Exception: pass
plt.rcParams['axes.unicode_minus']=False
import xgboost as xgb
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
m45=importlib.import_module('45_ml_models'); NUM=m45.NUM; CAT=m45.CAT
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
ZH={'d_peak':'峰值水深','rise_rate':'积水速率','alarm_min':'播报时机','exit_width':'出口宽度',
    'rescue_min':'救援到达(分)','fam_frac':'高熟悉比例','n_scenario':'人群规模',
    '进水位置':'进水位置','积水速率':'积水速率','播报时机':'播报时机','闸机管控':'闸机管控',
    '年龄':'年龄','性别':'性别','角色':'角色','风险偏好':'风险偏好','水灾经验':'水灾经验',
    '熟悉度':'熟悉度','行动能力':'行动能力','结伴':'结伴'}
MERGE={'播报时机':'alarm_min','积水速率':'rise_rate'}  # 合并同一因子的数值/类别编码
def group_of(n):
    g=n if n in NUM else n.split('_')[0]
    return MERGE.get(g,g)
def short(n):
    if n in NUM: return ZH.get(n,n)
    g=n.split('_')[0]; return '%s=%s'%(ZH.get(g,g),n[len(g)+1:])
def native_sv(clf,X):
    M=clf.get_booster().predict(xgb.DMatrix(np.asarray(X,dtype=float)),pred_contribs=True)
    if M.ndim==2: return M[:,:-1]
    return np.transpose(M[:,:,:-1],(0,2,1))   # (n,f,c)
def fit_pipe(W,y):
    pre=m45.preproc(False); _,clf=m45.models(None)['XGBoost']
    p=Pipeline([('pre',pre),('clf',clf)]); p.fit(W[NUM+CAT],y); return p

def factor_beeswarm(ax,Fsv,fac_keys,raw,K=12):
    """按归并因子绘制标准蜂群图：一个因子一行，颜色编码取值（蓝低→红高）。"""
    imp=np.abs(Fsv).mean(axis=0)
    order=np.argsort(imp)[::-1][:K][::-1]
    cmap=plt.cm.coolwarm; rng=np.random.default_rng(0)
    for row,ci in enumerate(order):
        g=fac_keys[ci]
        if g in NUM:
            fv=raw[g].astype(float).values
            norm=(fv-fv.min())/(fv.max()-fv.min()+1e-9)
            idx=rng.choice(len(fv),min(900,len(fv)),replace=False)
        else:
            codes=pd.Categorical(raw[g]).codes
            k=codes.max()+1; norm=codes/(k-1) if k>1 else np.zeros_like(codes,dtype=float)
            pick=[]
            for lv in range(k):
                m=np.where(codes==lv)[0]
                pick.append(rng.choice(m,min(220,len(m)),replace=False))
            idx=np.concatenate(pick)
        yj=row+rng.uniform(-.28,.28,len(idx))
        ax.scatter(Fsv[idx,ci],yj,s=7,alpha=.5,c=cmap(norm[idx]),edgecolors='none')
    ax.set_yticks(range(K)); ax.set_yticklabels([ZH.get(fac_keys[j],fac_keys[j]) for j in order],fontsize=9)
    lo,hi=np.quantile(Fsv[:,order],[.01,.99]); ax.set_xlim(lo*1.15,hi*1.15)
    ax.axvline(0,c='gray',ls='--',lw=.7); ax.set_xlabel('SHAP值（对自救概率的影响）')

def main():
    W=pd.read_csv(RUNS/'第6章_建模宽表_个体.csv')
    gss=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42)
    tr,te=next(gss.split(W,groups=W.cid.values))
    sample=np.random.default_rng(42).choice(te,min(2500,len(te)),replace=False)

    # 二分类风险
    pb=fit_pipe(W.iloc[tr],W.self_evac.values[tr])
    names=m45.ohe_names(pb.named_steps['pre'])
    Xe=np.asarray(pb.named_steps['pre'].transform(W[NUM+CAT].iloc[sample]),dtype=float)
    svb=native_sv(pb.named_steps['clf'],Xe)
    grp=[group_of(n) for n in names]
    gimp=pd.Series(np.abs(svb).mean(axis=0)).groupby(grp).sum().sort_values()
    fac_keys=list(dict.fromkeys(grp))
    Fsv=np.column_stack([svb[:,np.array(grp)==g].sum(axis=1) for g in fac_keys])
    raw=W[NUM+CAT].iloc[sample].reset_index(drop=True)
    pd.DataFrame({'因子':[ZH.get(g,g) for g in gimp.index],'重要性':gimp.values}
        ).to_excel(RUNS/'第6章_SHAP_风险因子.xlsx',index=False)
    fig,ax=plt.subplots(figsize=(9,6))
    ax.barh(range(len(gimp)),gimp.values,color='#2f6db0')
    ax.set_yticks(range(len(gimp))); ax.set_yticklabels([ZH.get(g,g) for g in gimp.index])
    ax.set_xlabel('平均|SHAP值|（对自救概率的贡献）')
    ax.set_title('图6-6 自救/救援依赖的关键驱动因子（SHAP全局重要性）')
    fig.tight_layout(); fig.savefig(FIG/'fig_SHAP风险重要性.png',dpi=200)

    fig=plt.figure(figsize=(15.5,6.0))
    ax1=fig.add_subplot(1,3,1); factor_beeswarm(ax1,Fsv,fac_keys,raw); ax1.set_title('(a) SHAP蜂群图')
    def dep(ax,feat,title):
        idx=names.index(feat); x=Xe[:,idx]; y=svb[:,idx]
        ax.scatter(x,y,s=8,alpha=.3,color='#2f6db0')
        bins=np.quantile(x,np.linspace(0,1,9)); bx=np.digitize(x,bins); out=[]
        for b in np.unique(bx):
            m=bx==b
            if m.sum()>10: out.append((x[m].mean(),y[m].mean()))
        if out:
            xx,yy=zip(*out); ax.plot(xx,yy,color='#b0413e',lw=2)
        ax.axhline(0,c='gray',ls='--',lw=.8)
        ax.set_xlabel(ZH.get(feat,feat)); ax.set_ylabel('SHAP值'); ax.set_title(title)
    ax2=fig.add_subplot(1,3,2); dep(ax2,'alarm_min','(b) 播报时机边际作用')
    ax3=fig.add_subplot(1,3,3); dep(ax3,'rise_rate','(c) 积水速率边际作用')
    fig.suptitle('图6-7 风险因子的作用方向与强度',fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.94]); fig.savefig(FIG/'fig_SHAP蜂群与依赖.png',dpi=200)

    # 多分类行为
    le=LabelEncoder().fit(W.behavior); ym=le.transform(W.behavior)
    pm=fit_pipe(W.iloc[tr],ym[tr])
    namesm=m45.ohe_names(pm.named_steps['pre'])
    Xem=np.asarray(pm.named_steps['pre'].transform(W[NUM+CAT].iloc[sample]),dtype=float)
    svm=native_sv(pm.named_steps['clf'],Xem)
    if svm.ndim==2: svm=svm[:,:,None]
    grpm=[group_of(n) for n in namesm]
    BHmap={'follow_guidance':'跟随引导','follow_crowd':'从众','nearest_exit':'就近出口','wait_and_see':'观望'}
    cls=[BHmap[c] for c in le.classes_]
    Gs=[]
    for c in range(svm.shape[2]):
        Gs.append(pd.Series(np.abs(svm[:,:,c]).mean(axis=0)).groupby(grpm).sum().rename(cls[c]))
    G=pd.concat(Gs,axis=1).fillna(0); G.insert(0,'因子',[ZH.get(g,g) for g in G.index])
    G.to_excel(RUNS/'第6章_SHAP_行为因子.xlsx',index=False)
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    for ax,c in zip(axes.flat,range(svm.shape[2])):
        s=G.set_index('因子').iloc[:,c].sort_values().tail(10)
        ax.barh(range(len(s)),s.values,color='#7a63a8')
        ax.set_yticks(range(len(s))); ax.set_yticklabels(s.index,fontsize=8)
        ax.set_title(cls[c],fontsize=11); ax.set_xlabel('平均|SHAP|')
    fig.suptitle('图6-8 各行为类别的关键驱动因子（SHAP）',fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.96]); fig.savefig(FIG/'fig_SHAP行为重要性.png',dpi=200)
    print('图6-6/6-7/6-8 已产出')
    print('风险Top5:',[ZH.get(g,g) for g in gimp.index[::-1][:5]])

if __name__=='__main__':
    main()
