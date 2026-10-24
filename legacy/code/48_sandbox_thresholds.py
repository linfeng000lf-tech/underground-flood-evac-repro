# -*- coding: utf-8 -*-
"""第6章 步骤8：干预沙盘与阈值建议（离散因子边际化，避免连续网格伪边界）。
以自救/救援依赖 XGB 模型为沙盘，对两个可控杠杆(播报时机 早10/晚40/无120 ×
积水速率 慢/中/快)评估，其余因子(峰值水深d_peak、出口、救援、画像等)按样本分布
边际化，得到模型3×3干预矩阵并与1920个真实批量run经验pivot对照；产出图6-10、阈值表。"""
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
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
import xgboost as xgb
m45=importlib.import_module('45_ml_models'); NUM=m45.NUM; CAT=m45.CAT
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
RISE={'慢':.014,'中':.025,'快':.061}; ALARM={'早':10,'晚':40,'无':120}

def main():
    W=pd.read_csv(RUNS/'第6章_建模宽表_个体.csv')
    gss=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42)
    tr,_=next(gss.split(W,groups=W.cid.values))
    # 沙盘用未加权、概率校准的XGB（类别平衡模型仅用于45的判别指标，其概率整体偏低）
    pre=m45.preproc(False)
    clf=xgb.XGBClassifier(n_estimators=350,max_depth=6,learning_rate=.06,subsample=.9,
        colsample_bytree=.9,scale_pos_weight=1,eval_metric='logloss',n_jobs=6,random_state=42)
    pipe=Pipeline([('pre',pre),('clf',clf)]); pipe.fit(W[NUM+CAT].iloc[tr],W.self_evac.values[tr])

    bands=['慢','中','快']; timings=['早','晚','无']
    W=W.assign(p=pipe.predict_proba(W[NUM+CAT])[:,1])
    model=W.pivot_table(index='积水速率',columns='播报时机',values='p').reindex(bands)[timings]

    run=pd.read_csv(RUNS/'批量实验_run级.csv').groupby('cid',as_index=False).evac_rate.mean()
    fac=pd.read_csv(RUNS/'第6章_run级情景表.csv')
    piv=run.merge(fac,on='cid').pivot_table(index='积水速率',columns='播报时机',values='evac_rate').reindex(bands)[timings]
    print('模型3×3:'); print(model.round(2)); print('经验pivot:'); print(piv.round(2))
    print('模型-经验 最大偏差 %.3f'%(model.values-piv.values).__abs__().max())

    # 阈值/决策规则
    rules=[]
    for rb in bands:
        for target in [.9,.8]:
            ok=[tb for tb in timings if piv.loc[rb,tb]>=target]
            if ok:
                latest=ok[-1]
                rec=('最迟应在进水征兆后%d分钟内完成播报'%ALARM[latest] if latest!='无'
                     else '不依赖播报亦可达标（仍建议尽早播报）')
                rules.append({'积水档位':rb,'目标自救率':'≥%d'%(target*100),
                    '可行播报':('、'.join(ok)),'推荐':rec})
            else:
                rules.append({'积水档位':rb,'目标自救率':'≥%d'%(target*100),
                    '可行播报':'无','推荐':'播报无法达标→停运/封堵并预置救援'})
    rules=pd.DataFrame(rules)
    print(rules.to_string())

    fig,ax=plt.subplots(figsize=(9.2,6.2))
    cc=ax.imshow(piv.values,cmap='RdYlGn',vmin=.4,vmax=1.0,aspect='auto')
    for i in range(3):
        for j in range(3):
            ax.text(j,i,'经验%.2f\n模型%.2f'%(piv.values[i,j],model.values[i,j]),
                    ha='center',va='center',fontsize=10)
    ax.set_xticks(range(3)); ax.set_xticklabels(['早播报(≤10min)','晚播报(~40min)','无播报(120min)'])
    ax.set_yticks(range(3)); ax.set_yticklabels(['慢速涨水','中速涨水','快速涨水'])
    cb=fig.colorbar(cc,ax=ax); cb.set_label('自救率')
    ax.set_title('图6-10 干预沙盘：播报时机×积水速率→自救率（经验 vs 模型）')
    fig.tight_layout(); fig.savefig(FIG/'fig_干预沙盘阈值.png',dpi=150)

    with pd.ExcelWriter(RUNS/'第6章_干预阈值.xlsx') as w:
        piv.round(3).to_excel(w,sheet_name='经验矩阵')
        model.round(3).to_excel(w,sheet_name='模型矩阵')
        rules.to_excel(w,sheet_name='决策规则',index=False)
    print('图6-10 与阈值表已产出')

if __name__=='__main__':
    main()
