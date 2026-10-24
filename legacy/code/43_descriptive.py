# -*- coding: utf-8 -*-
"""第6章 步骤2：描述性统计与可视化。
图6-1 行为/结果构成与疏散时间分布；图6-2 不同情景与个体因素下的自救率、行为构成；
产出描述性统计表。"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ('Microsoft YaHei','SimHei'):
    try: font_manager.findfont(f,fallback_to_default=False); plt.rcParams['font.sans-serif']=[f]; break
    except Exception: pass
plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
BLUE='#2f6db0'; COLORS=['#2f6db0','#e08a2b','#4c9f5a','#b0413e','#7a63a8','#5aa6a6']
BH={'follow_guidance':'跟随引导','follow_crowd':'从众','nearest_exit':'就近出口','wait_and_see':'观望'}

def main():
    W=pd.read_csv(RUNS/'第6章_建模宽表_个体.csv')
    # ---- 图6-1 ----
    fig,axes=plt.subplots(1,3,figsize=(15,4.4))
    order=['follow_guidance','follow_crowd','nearest_exit','wait_and_see']
    bc=W.behavior.value_counts()
    axes[0].bar([BH[x] for x in order],[bc.get(x,0) for x in order],color=BLUE)
    axes[0].set_title('(a) 首个承诺行为构成'); axes[0].set_ylabel('人数')
    for i,x in enumerate(order):
        axes[0].text(i,bc.get(x,0),f'{bc.get(x,0)/len(W):.0%}',ha='center',va='bottom',fontsize=9)
    sc=W.self_evac.value_counts()
    axes[1].bar(['自救撤离','救援依赖'],[sc.get(1,0),sc.get(0,0)],color=['#4c9f5a','#e08a2b'])
    axes[1].set_title('(b) 最终结果构成'); axes[1].set_ylabel('人数')
    for i,k in enumerate((1,0)):
        axes[1].text(i,sc.get(k,0),f'{sc.get(k,0)/len(W):.1%}',ha='center',va='bottom',fontsize=9)
    et=W.loc[W.final_status=='evacuated','evac_time']
    axes[2].hist(et,bins=30,color=BLUE,alpha=.85)
    axes[2].axvline(et.median(),c='red',ls='--',lw=1.2,label='中位数%.1f min'%et.median())
    axes[2].set_title('(c) 自救撤离时间分布'); axes[2].set_xlabel('撤离时间(min)'); axes[2].set_ylabel('人数'); axes[2].legend()
    fig.suptitle('图6-1 行为与结果的总体分布',fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.95]); fig.savefig(FIG/'fig_描述性_总体构成.png',dpi=150)

    # ---- 图6-2 ----
    fig,axes=plt.subplots(2,2,figsize=(12,8.2))
    def rate_bar(ax,col,order_l,title):
        g=W.groupby(col).self_evac.mean().reindex(order_l)
        bars=ax.bar(range(len(g)),g.values,color=BLUE)
        ax.set_xticks(range(len(g))); ax.set_xticklabels(order_l,rotation=0)
        ax.set_ylim(0,1.05); ax.set_ylabel('自救撤离率'); ax.set_title(title)
        for b,v in zip(bars,g.values): ax.text(b.get_x()+b.get_width()/2,v+1e-3,f'{v:.2f}',ha='center',fontsize=8)
    rate_bar(axes[0,0],'播报时机',['早','晚','无'],'(a) 播报时机 → 自救率')
    rate_bar(axes[0,1],'积水速率',['慢','中','快'],'(b) 积水速率 → 自救率')
    rate_bar(axes[1,0],'熟悉度',['高','低'],'(c) 个体熟悉度 → 自救率')
    # 行为构成随播报（堆叠）
    ax=axes[1,1]
    tab=pd.crosstab(W.播报时机,W.behavior,normalize='index').reindex(['早','晚','无'])[order].fillna(0)
    bottom=np.zeros(len(tab))
    for j,k in enumerate(order):
        ax.bar(range(len(tab)),tab[k].values,bottom=bottom,color=COLORS[j],label=BH[k]); bottom+=tab[k].values
    ax.set_xticks(range(len(tab))); ax.set_xticklabels(['早','晚','无'])
    ax.set_ylim(0,1.02); ax.set_ylabel('行为比例'); ax.set_title('(d) 播报时机 → 行为构成'); ax.legend(fontsize=8,ncol=2)
    fig.suptitle('图6-2 情景/个体因素与自救率、行为选择的关系',fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.96]); fig.savefig(FIG/'fig_描述性_因素关系.png',dpi=150)

    # ---- 描述性统计表 ----
    rows=[]
    for col,ol in [('播报时机',['早','晚','无']),('积水速率',['慢','中','快']),
                   ('峰值水深m',sorted(W.d_peak.unique())),('熟悉度',['高','中','低']),
                   ('行动能力',['正常','受限']),('角色',sorted(W.角色.unique()))]:
        for lvl in ol:
            sub=W[W[col]==lvl]
            if len(sub)==0: continue
            rows.append({'因素':col,'水平':lvl,'人数':len(sub),
                '自救率':round(sub.self_evac.mean(),3),
                '撤离时间中位':round(sub.loc[sub.final_status=='evacuated','evac_time'].median(),2)})
    pd.DataFrame(rows).to_excel(RUNS/'第6章_描述性统计.xlsx',index=False)
    print('图6-1/6-2 与描述性统计表已产出')
    print('自救率 总体%.3f；撤离时间中位 %.2f min'%(W.self_evac.mean(),
        W.loc[W.final_status=='evacuated','evac_time'].median()))

if __name__=='__main__':
    main()
