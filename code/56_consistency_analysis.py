# -*- coding: utf-8 -*-
"""阶段1A分析：合并分片真实LLM复现结果(DeepSeek+千问)与缓存，产出三张一致性表 + 跨厂商包络图。
表1 困难情景排序(均值±重复区间, Spearman及bootstrap区间, MAE, 区间覆盖) 启发式 vs 各真实引擎；
表2 关键关联规则方向(深水+快涨→迟滞；迟滞/深水→救援依赖) 三引擎对比；
表3 在各引擎个体数据上分别重训XGB，比较主导因子Top-N与AUC。另统计真实API调用与token。"""
import json, os, importlib, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; CACHE=ROOT/'results'/'cache'
FIG=ROOT/'results'/'figures'; sys.path.insert(0,str(ROOT/'code'))
REALS=['deepseek','qwen']

def load_provider(provider,nshards=4,ind=False):
    fs=[RUNS/f'真实LLM复现_{"ind" if ind else "runs"}_{provider}_shard{i}.csv' for i in range(nshards)]
    d=pd.concat([pd.read_csv(f) for f in fs if f.exists()],ignore_index=True)
    d=d.copy(); d['engine']=d['engine'].map({'heur':'heur','llm':provider})
    return d

def merge_all(nshards=4, include_qwen=True):
    runs=load_provider('deepseek',nshards)          # 含 heur + deepseek
    ind=load_provider('deepseek',nshards,ind=True)
    qf=RUNS/'真实LLM复现_runs_qwen_shard0.csv'
    if include_qwen and qf.exists():
        runs=pd.concat([runs,load_provider('qwen',nshards)],ignore_index=True)
        ind=pd.concat([ind,load_provider('qwen',nshards,ind=True)],ignore_index=True)
    scn=pd.read_csv(RUNS/'第6章_run级情景表.csv')
    ind=ind.merge(scn,on='cid',how='left')
    ind['self_evac']=(ind.final_status=='evacuated').astype(int)
    return runs,ind

def merge_caches(nshards=4):
    g=CACHE/'llm_cache.json'; G=json.loads(g.read_text(encoding='utf-8')) if g.exists() else {}; n0=len(G)
    for prov in ('deepseek','qwen'):
        for i in range(nshards):
            p=CACHE/f'llm_cache_{prov}_shard{i}.json'
            if p.exists(): G.update(json.loads(p.read_text(encoding='utf-8')))
    g.write_text(json.dumps(G,ensure_ascii=False),encoding='utf-8')
    print('合并缓存：%d → %d 条'%(n0,len(G)))

def cid_means(runs,eng):
    d=runs[runs.engine==eng].groupby('cid').agg(mean=('evac_rate','mean'),
        lo=('evac_rate','min'),hi=('evac_rate','max'))
    return d

def table1(runs):
    H=cid_means(runs,'heur'); cids=sorted(H.index)
    hv=H.loc[cids,'mean'].values
    rows=[]; summ=[]
    for eng in REALS:
        if runs.engine.min()==eng and not (runs.engine==eng).any(): continue
        if not (runs.engine==eng).any(): continue
        R=cid_means(runs,eng)
        cc=[c for c in cids if c in R.index]
        hx=H.loc[cc,'mean'].values; rx=R.loc[cc,'mean'].values
        rho=spearmanr(hx,rx).statistic
        rng=np.random.default_rng(0); bs=[]
        for _ in range(2000):
            ix=rng.integers(0,len(cc),len(cc)); bs.append(spearmanr(hx[ix],rx[ix]).statistic)
        ci=np.nanpercentile(bs,[2.5,97.5])
        cover=np.mean([R.loc[c,'mean']>=H.loc[c,'lo']-1e-9 and R.loc[c,'mean']<=H.loc[c,'hi']+1e-9
                       for c in cc])
        summ.append({'真实引擎':eng,'Spearman':round(rho,3),
            'Spearman_CI':f'[{ci[0]:.2f},{ci[1]:.2f}]','MAE':round(np.mean(np.abs(hx-rx)),3),
            '落入启发式区间比例':round(cover,3)})
        for c in cc:
            rows.append({'cid':c,'引擎':eng,'启发式均值':round(H.loc[c,'mean'],3),
                '真实均值':round(R.loc[c,'mean'],3),
                '真实区间':f"{R.loc[c,'lo']:.2f}–{R.loc[c,'hi']:.2f}",'差':round(abs(H.loc[c,'mean']-R.loc[c,'mean']),3)})
    pd.DataFrame(rows).to_csv(RUNS/'真实LLM_表1_排序一致性.csv',index=False,encoding='utf-8-sig')
    s1=pd.DataFrame(summ); s1.to_csv(RUNS/'真实LLM_表1_汇总.csv',index=False,encoding='utf-8-sig')
    return s1

def table2(ind):
    q=ind.d_peak.quantile(.75); rq=ind.rise_rate.quantile(.75)
    deep=(ind.d_peak>=q)&(ind.rise_rate>=rq)
    engines=['heur']+[e for e in REALS if (ind.engine==e).any()]
    rows=[]
    for eng in engines:
        m=ind.engine==eng
        wd=(ind[m&deep].behavior=='wait_and_see').mean(); wo=(ind[m&~deep].behavior=='wait_and_see').mean()
        w=ind[m&(ind.behavior=='wait_and_see')]
        dw=('N/A' if len(w)==0 else round(1-(w.final_status=='evacuated').mean(),3))
        dm=ind[m&deep]
        rows.append({'引擎':eng,'迟滞率_深水快涨':round(wd,3),'迟滞率_其他':round(wo,3),
            '救援依赖_迟滞者':dw,'救援依赖_深水快涨':round(1-(dm.final_status=='evacuated').mean(),3)})
    t2=pd.DataFrame(rows); t2.to_csv(RUNS/'真实LLM_表2_规则方向.csv',index=False,encoding='utf-8-sig')
    return t2

def table3(ind):
    import xgboost as xgb
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import roc_auc_score
    NUM=['d_peak','rise_rate','alarm_min','exit_width','rescue_min','fam_frac','n_scenario']
    CAT=['进水位置','积水速率','播报时机','闸机管控','年龄','性别','角色','风险偏好',
         '水灾经验','熟悉度','行动能力','结伴']
    engines=['heur']+[e for e in REALS if (ind.engine==e).any()]
    rows=[]; tops={}
    for eng in engines:
        W=ind[ind.engine==eng].reset_index(drop=True)
        X=pd.get_dummies(W[NUM+CAT],columns=CAT,dummy_na=False)
        y=(W.final_status=='evacuated').astype(int).values; groups=W.cid.values
        aucs=[]; nf=0
        for tr,te in GroupKFold(5).split(X,groups=groups):
            if len(np.unique(y[te]))<2: continue
            nf+=1; spw=int((y[tr]==0).sum())/max(int((y[tr]==1).sum()),1)
            clf=xgb.XGBClassifier(n_estimators=300,max_depth=6,learning_rate=.07,subsample=.9,
                colsample_bytree=.9,scale_pos_weight=spw,eval_metric='logloss',n_jobs=4,random_state=42)
            clf.fit(X.iloc[tr],y[tr]); aucs.append(roc_auc_score(y[te],clf.predict_proba(X.iloc[te])[:,1]))
        clf=xgb.XGBClassifier(n_estimators=300,max_depth=6,learning_rate=.07,subsample=.9,
            colsample_bytree=.9,eval_metric='logloss',n_jobs=4,random_state=42); clf.fit(X,y)
        imp=pd.Series(clf.feature_importances_,index=X.columns); fac={}
        for f,v in imp.items():
            base=next((n for n in NUM if f==n or f.startswith(n+'_')),f.split('_')[0]); fac[base]=fac.get(base,0)+v
        tops[eng]=pd.Series(fac).sort_values(ascending=False)
        rows.append({'引擎':eng,'依赖占比':round(1-y.mean(),3),'有效AUC折':f'{nf}/5',
            'AUC_CV':(round(np.mean(aucs),3) if aucs else '不可估'),
            'Top5因子':', '.join(tops[eng].head(5).index)})
    t3=pd.DataFrame(rows); t3.to_csv(RUNS/'真实LLM_表3_ML主因子.csv',index=False,encoding='utf-8-sig')
    return t3

def cost(provider,nshards=4):
    tot=pt=ct=0
    pre='' if provider=='deepseek' else provider+'_'
    for i in range(nshards):
        p=RUNS/f'llm_calls_{pre}shard{i}.jsonl'
        if not p.exists(): continue
        for line in p.read_text(encoding='utf-8').splitlines():
            r=json.loads(line)
            if not r.get('cached') and r.get('status')=='ok' and 'total_tokens' in r:
                tot+=1; pt+=r.get('prompt_tokens') or 0; ct+=r.get('completion_tokens') or 0
    return {'provider':provider,'真实调用':tot,'prompt_tok':pt,'completion_tok':ct}

def fig(runs):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    H=cid_means(runs,'heur'); cids=sorted(H.index,key=lambda c:H.loc[c,'mean'])
    present=[e for e in REALS if (runs.engine==e).any()]
    x=np.arange(len(cids)); w=.8/(len(present)+1)
    fig,ax=plt.subplots(figsize=(14,5.4))
    ax.bar(x-w*len(present)/2,H.loc[cids,'mean'].values,w,color='#9db4cc',label='启发式代理')
    colors={'deepseek':'#d98c5f','qwen':'#6fae8f'}
    for k,eng in enumerate(present):
        R=cid_means(runs,eng)
        ax.bar(x+w*(k+.5-len(present)/2),[R.loc[c,'mean'] if c in R.index else np.nan for c in cids],
            w,color=colors[eng],label={'deepseek':'真实LLM(DeepSeek)','qwen':'真实LLM(千问)'}[eng])
    ax.set_xticks(x); ax.set_xticklabels(cids,rotation=70,fontsize=7.3)
    ax.set_ylabel('自救撤离率'); ax.set_ylim(0,1.08); ax.legend(ncol=3)
    ax.set_title('图5-8 分层配置下启发式代理与跨厂商真实LLM自救率（DeepSeek、千问均6重复，均值）')
    fig.tight_layout(); fig.savefig(FIG/'fig_真实LLM复现.png',dpi=200); plt.close()
    print('已写 fig_真实LLM复现.png')

def main():
    iq=not bool(os.environ.get('SKIP_QWEN'))
    runs,ind=merge_all(include_qwen=iq); print('run级',runs.shape,'个体级',ind.shape,'引擎',runs.engine.unique())
    s1=table1(runs); print('\n表1\n',s1.to_string(index=False))
    t2=table2(ind); print('\n表2\n',t2.to_string(index=False))
    t3=table3(ind); print('\n表3\n',t3.to_string(index=False))
    print('\n成本',[cost(p) for p in ['deepseek']+[e for e in REALS if e!='deepseek']])
    fig(runs); merge_caches()

if __name__=='__main__':
    main()
