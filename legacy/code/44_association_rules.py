# -*- coding: utf-8 -*-
"""第6章 步骤3：关联规则挖掘。
对个体宽表离散化为"交易"，Apriori 挖频繁项集并生成关联规则，
筛选 RHS 为行为/结果的高提升度规则，分"情景→行为/情景→结果/行为→结果"三类，
产出全量规则、精选规则表与图6-3。"""
from pathlib import Path
import warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore',category=FutureWarning,message='.*DataFrameGroupBy.apply.*')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ('Microsoft YaHei','SimHei'):
    try: font_manager.findfont(f,fallback_to_default=False); plt.rcParams['font.sans-serif']=[f]; break
    except Exception: pass
plt.rcParams['axes.unicode_minus']=False
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
BH={'follow_guidance':'跟随引导','follow_crowd':'从众','nearest_exit':'就近出口','wait_and_see':'观望'}
ENTRY={'gate_A':'出入口','interval':'隧道','wind':'风亭'}

def build_transactions(W):
    depth=pd.cut(W.peak_depth,[-1,.05,.30,.70,99],labels=['水深=干','水深=浅','水深=中','水深=深'])
    peak=pd.cut(W.d_peak,[0,.8,1.4,99],labels=['峰值=低','峰值=中','峰值=高'])
    T=[]
    for i in range(len(W)):
        r=W.iloc[i]
        items=[str(depth.iloc[i]),str(peak.iloc[i]),
               '播报=%s'%r.播报时机,'速率=%s'%r.积水速率,'进水=%s'%ENTRY.get(r.进水位置,r.进水位置),
               '熟悉=%s'%r.熟悉度,'行动=%s'%r.行动能力,
               '行为=%s'%BH[r.behavior],
               '结果=自救' if r.self_evac==1 else '结果=获救']
        T.append(items)
    return T

def strat_sample(g,per=500):
    if len(g)<=per: return g
    alloc=(g.behavior.value_counts(normalize=True)*per).round().astype(int)
    parts=[]
    for b,nb in alloc.items():
        h=g[g.behavior==b]
        parts.append(h.sample(n=min(len(h),max(2,nb)),random_state=42))
    return pd.concat(parts)

def main():
    W0=pd.read_csv(RUNS/'第6章_建模宽表_个体.csv')
    # 分层抽样(情景特征在cid内重复)：每cid约500条、按行为比例，支持度估计仍稳定
    W=pd.concat([strat_sample(g) for _,g in W0.groupby('cid')],ignore_index=True)
    print('用于规则挖掘的抽样交易数:',len(W))
    T=build_transactions(W)
    import time
    te=TransactionEncoder(); X=te.fit_transform(T)
    Xdf=pd.DataFrame(X,columns=te.columns_)
    t0=time.time(); freq=fpgrowth(Xdf,min_support=.03,use_colnames=True,max_len=4)
    print('频繁项集 %d 个（%.1fs）'%(len(freq),time.time()-t0),flush=True)
    t0=time.time(); rules=association_rules(freq,metric='lift',min_threshold=1.1)
    print('生成规则 %d 条（%.1fs）'%(len(rules),time.time()-t0),flush=True)
    rules=rules[rules.consequents.map(lambda s:len(s)==1)].copy()
    rhs=rules.consequents.map(lambda s:list(s)[0])
    rules['RHS']=rhs
    rules=rules[rhs.str.startswith(('行为=','结果='))].copy()
    def typ(r):
        ante=' '.join(r.antecedents)
        if r.RHS.startswith('行为='): return '情景→行为'
        return '行为→结果' if '行为=' in ante else '情景→结果'
    rules['类型']=rules.apply(typ,axis=1)
    rules['前件']=rules.antecedents.map(lambda s:' 且 '.join(sorted(s)))
    rules['后件']=rules.RHS
    out=rules[['类型','前件','后件','support','confidence','lift','leverage','conviction']].rename(
        columns={'support':'支持度','confidence':'置信度','lift':'提升度','leverage':'杠杆率','conviction':'确信度'})
    out=out.sort_values(['类型','提升度','置信度'],ascending=[True,False,False])
    out.to_csv(RUNS/'第6章_关联规则_全量.csv',index=False,encoding='utf-8-sig')
    # 精选：每类按提升度取前12（要求置信度≥.5）
    sel=(out[out.置信度>=.5].groupby('类型',group_keys=False)
         .apply(lambda g:g.sort_values('提升度',ascending=False).head(12)).reset_index(drop=True))
    sel.to_excel(RUNS/'第6章_关联规则_精选.xlsx',index=False)
    print('规则总数%d；精选%d'%(len(out),len(sel)))
    for t,g in sel.groupby('类型'):
        print('\n##',t)
        for _,r in g.head(6).iterrows():
            print('  IF %s THEN %s | 支持%.3f 置信%.2f 提升%.2f'%(r.前件,r.后件,r.支持度,r.置信度,r.提升度))

    # ---- 图6-3：最强"情景→行为/结果"规律（水平条，条长=提升度，色=置信度）----
    TOK={'播报=无':'无播报','播报=晚':'晚播报','速率=快':'快速涨水','速率=中':'中速涨水',
         '峰值=高':'高峰值水深','峰值=中':'中峰值水深','峰值=低':'低峰值水深',
         '水深=深':'深水','水深=中':'中水','进水=隧道':'隧道进水','进水=风亭':'风亭进水',
         '进水=出入口':'出入口进水','熟悉=低':'低熟悉度','熟悉=高':'高熟悉度',
         '行动=正常':'行动正常','行动=受限':'行动受限','行为=观望':'观望'}
    RHSL={'结果=获救':'救援依赖','结果=自救':'自救撤离','行为=观望':'观望',
          '行为=从众':'从众','行为=就近出口':'就近出口','行为=跟随引导':'跟随引导'}
    def sentence(r):
        ante='+'.join(TOK.get(t,t) for t in r.前件.split(' 且 '))
        return '%s → %s'%(ante,RHSL.get(r.后件,r.后件))
    sel_law=sel[~sel.前件.str.contains('结果=')]  # 前件不得含未来结果，保证因果方向
    picks=[]
    for t in ('情景→行为','情景→结果','行为→结果'):
        g=sel_law[sel_law.类型==t].sort_values('提升度',ascending=False).head(4)
        picks.append(g)
    P=pd.concat(picks).drop_duplicates(subset=['前件','后件']).sort_values('提升度')
    P=P.assign(lab=[sentence(r) for _,r in P.iterrows()])
    fig,ax=plt.subplots(figsize=(10.5,6.6))
    norm=plt.Normalize(P.置信度.min(),1.0)
    cmap=plt.cm.YlOrRd
    bars=ax.barh(range(len(P)),P.提升度,color=cmap(norm(P.置信度)),edgecolor='k',lw=.4)
    ax.set_yticks(range(len(P))); ax.set_yticklabels(P.lab,fontsize=9)
    for b,(_,r) in zip(bars,P.iterrows()):
        ax.text(b.get_width()+.12,b.get_y()+b.get_height()/2,
                '提升%.1f·置信%.2f'%(r.提升度,r.置信度),va='center',fontsize=8)
    ax.set_xlabel('提升度 lift'); ax.set_xlim(0,P.提升度.max()+2.4)
    ax.set_title('图6-3 关联规则挖掘得到的核心"情景—行为—结果"规律')
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=ax,pad=.012)
    cb.set_label('置信度 confidence')
    fig.tight_layout(); fig.savefig(FIG/'fig_关联规则.png',dpi=150)

if __name__=='__main__':
    main()
