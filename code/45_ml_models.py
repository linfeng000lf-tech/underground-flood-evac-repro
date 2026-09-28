# -*- coding: utf-8 -*-
"""第6章 步骤5：行为选择与安全转移风险的机器学习建模。
两个目标：①二分类 self_evac(自救=1/救援依赖=0)；②多分类 behavior(4类)。
按情景 cid 分组留出(约20% cid)评估对"未见情景"的泛化，并做分组交叉验证；
对比 逻辑回归/随机森林/XGBoost；产出指标表、特征重要性与图6-4/6-5。"""
import json, importlib, warnings
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
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score,f1_score,roc_auc_score,average_precision_score,
    confusion_matrix,classification_report,roc_curve,precision_recall_curve)
import xgboost as xgb
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
NUM=['d_peak','rise_rate','alarm_min','exit_width','rescue_min','fam_frac','n_scenario']
CAT=['进水位置','积水速率','播报时机','闸机管控',
     '年龄','性别','角色','风险偏好','水灾经验','熟悉度','行动能力','结伴']

def preproc(scale):
    cats=[OneHotEncoder(handle_unknown='ignore')]
    nums=[StandardScaler()] if scale else []
    return ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),CAT),
                              ('num',Pipeline([('s',StandardScaler())]) if scale else 'passthrough',NUM)])
def models(ybinary):
    if ybinary is None: spw=1.0
    else: spw=int((ybinary==0).sum())/max(int((ybinary==1).sum()),1)
    return {
      '逻辑回归':(preproc(True),LogisticRegression(max_iter=2000,class_weight='balanced')),
      '随机森林':(preproc(False),RandomForestClassifier(n_estimators=300,min_samples_leaf=5,
                          class_weight='balanced',n_jobs=6,random_state=42)),
      'XGBoost':(preproc(False),xgb.XGBClassifier(n_estimators=350,max_depth=6,learning_rate=.06,
                          subsample=.9,colsample_bytree=.9,scale_pos_weight=spw,
                          eval_metric='logloss',n_jobs=6,random_state=42))}

def ohe_names(pre):
    names=pre.named_transformers_['cat'].get_feature_names_out(CAT).tolist()+NUM
    return names

def run_target(W,target,kind,multiclass=False):
    groups=W.cid.values
    gss=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42)
    tr,te=next(gss.split(W,groups=groups))
    Xdf=W[NUM+CAT]
    if multiclass:
        le=LabelEncoder(); y=le.fit_transform(W[target]); classes=le.classes_
    else:
        y=W[target].values; classes=np.array(['救援依赖','自救'])
    rows=[]; fitted={}
    for name,(pre,clf) in models(y if not multiclass else None).items():
        pipe=Pipeline([('pre',pre),('clf',clf)])
        pipe.fit(Xdf.iloc[tr],y[tr]); fitted[name]=pipe
        pred=pipe.predict(Xdf.iloc[te])
        r={'目标':kind,'模型':name,'测试cid数':len(np.unique(groups[te])),
           '准确率':round(accuracy_score(y[te],pred),4)}
        if not multiclass:
            proba=pipe.predict_proba(Xdf.iloc[te])[:,1]
            r.update({'F1':round(f1_score(y[te],pred),4),
                'ROC_AUC':round(roc_auc_score(y[te],proba),4),
                'PR_AUC':round(average_precision_score(y[te],proba),4)})
        else:
            r.update({'宏F1':round(f1_score(y[te],pred,average='macro'),4),
                '加权F1':round(f1_score(y[te],pred,average='weighted'),4)})
        rows.append(r)
    # 选最佳
    metric='宏F1' if multiclass else 'ROC_AUC'
    best=max(rows,key=lambda r:r[metric])['模型']
    # 分组交叉验证(训练cid, 5折) 仅最佳
    gkf=GroupKFold(n_splits=5)
    pre,clf=models(None if multiclass else y)[best]
    cv=cross_val_score(Pipeline([('pre',pre),('clf',clf)]),Xdf.iloc[tr],y[tr],
                       groups=groups[tr],cv=gkf,scoring='f1_macro' if multiclass else 'f1',n_jobs=1)
    for r in rows:
        if r['模型']==best: r['分组CV均值']=round(cv.mean(),4)
    return rows,fitted,best,(tr,te),y,classes

def main():
    W=pd.read_csv(RUNS/'第6章_建模宽表_个体.csv')
    allrows=[]
    # 二分类
    rowsB,fitB,bestB,splitB,yB,clsB=run_target(W,'self_evac','自救/救援依赖(二分类)')
    allrows+=rowsB
    # 多分类
    rowsM,fitM,bestM,splitM,yM,clsM=run_target(W,'behavior','行为选择(多分类)',multiclass=True)
    allrows+=rowsM
    pd.DataFrame(allrows).to_excel(RUNS/'第6章_ML指标.xlsx',index=False)
    print('二分类最佳:%s；多分类最佳:%s'%(bestB,bestM))
    for r in allrows: print(r)

    # ---- 图6-4 二分类：混淆矩阵 + ROC + PR ----
    tr,te=splitB; Xdf=W[NUM+CAT]; pipe=fitB[bestB]
    proba=pipe.predict_proba(Xdf.iloc[te])[:,1]; pred=pipe.predict(Xdf.iloc[te])
    fig,axes=plt.subplots(1,3,figsize=(15.4,4.6))
    cm=confusion_matrix(yB[te],pred)
    axes[0].imshow(cm,cmap='Blues')
    for i in range(2):
        for j in range(2): axes[0].text(j,i,cm[i,j],ha='center',va='center',fontsize=12)
    axes[0].set_xticks([0,1]); axes[0].set_xticklabels(['救援依赖','自救'])
    axes[0].set_yticks([0,1]); axes[0].set_yticklabels(['救援依赖','自救']); axes[0].set_title('(a) 混淆矩阵(%s)'%bestB)
    fpr,tpr,_=roc_curve(yB[te],proba); a=roc_auc_score(yB[te],proba)
    axes[1].plot(fpr,tpr,c='#2f6db0',label='AUC=%.3f'%a); axes[1].plot([0,1],[0,1],'--',c='gray')
    axes[1].set_xlabel('假阳性率'); axes[1].set_ylabel('真阳性率'); axes[1].set_title('(b) ROC曲线'); axes[1].legend()
    p,rc,_=precision_recall_curve(yB[te],proba); ap=average_precision_score(yB[te],proba)
    axes[2].plot(rc,p,c='#b0413e',label='AP=%.3f'%ap)
    axes[2].set_xlabel('召回率'); axes[2].set_ylabel('精确率'); axes[2].set_title('(c) PR曲线'); axes[2].legend()
    fig.suptitle('图6-4 自救/救援依赖风险预测模型（按未见情景留出）',fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.94]); fig.savefig(FIG/'fig_ML风险模型.png',dpi=150)

    # ---- 图6-5 多分类：混淆矩阵热力 + 每类报告 ----
    tr,te=splitM; pipe=fitM[bestM]; pred=pipe.predict(Xdf.iloc[te])
    cm=confusion_matrix(yM[te],pred,normalize='true')
    BHmap={'follow_guidance':'跟随引导','follow_crowd':'从众','nearest_exit':'就近出口','wait_and_see':'观望'}
    labs=[BHmap[c] for c in clsM]
    fig,axes=plt.subplots(1,2,figsize=(13,5.4))
    im=axes[0].imshow(cm,cmap='Blues',vmin=0,vmax=1)
    axes[0].set_xticks(range(4)); axes[0].set_xticklabels(labs,rotation=20)
    axes[0].set_yticks(range(4)); axes[0].set_yticklabels(labs)
    for i in range(4):
        for j in range(4): axes[0].text(j,i,f'{cm[i,j]:.2f}',ha='center',va='center',fontsize=9)
    axes[0].set_xlabel('预测'); axes[0].set_ylabel('实际'); axes[0].set_title('(a) 归一化混淆矩阵(%s)'%bestM)
    rep=classification_report(yM[te],pred,target_names=labs,output_dict=True)
    met=['precision','recall','f1-score']; x=np.arange(4); w=.25
    for k,m in enumerate(met):
        axes[1].bar(x+(k-1)*w,[rep[c][m] for c in labs],w,label=m)
    axes[1].set_xticks(x); axes[1].set_xticklabels(labs); axes[1].set_ylim(0,1.05)
    axes[1].set_title('(b) 各类 精确率/召回率/F1'); axes[1].legend()
    fig.suptitle('图6-5 行为选择多分类模型（按未见情景留出）',fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.94]); fig.savefig(FIG/'fig_ML行为模型.png',dpi=150)

    # 特征重要性（最佳XGB/RF）
    imps={}
    for tag,fit,best in (('风险',fitB,bestB),('行为',fitM,bestM)):
        pipe=fit[best]; clf=pipe.named_steps['clf']
        if hasattr(clf,'feature_importances_'):
            names=ohe_names(pipe.named_steps['pre'])
            imps[tag]=pd.DataFrame({'feature':names,'importance':clf.feature_importances_})
    with pd.ExcelWriter(RUNS/'第6章_特征重要性.xlsx') as w:
        for t,d in imps.items(): d.sort_values('importance',ascending=False).to_excel(w,sheet_name=t,index=False)
    print('图6-4/6-5 与特征重要性已产出')

if __name__=='__main__':
    main()
