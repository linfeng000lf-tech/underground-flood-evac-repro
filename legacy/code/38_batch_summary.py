# -*- coding: utf-8 -*-
"""第5章 步骤6补充：大规模计算实验结果汇总（RQ3）。
合并 run 级结果与实验矩阵因子，产出结果分布、因子主效应与关键交互热图。"""
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
FACTORS=['进水位置','峰值水深m','积水速率','人群密度','熟悉度比例','播报时机','闸机管控','救援到达min']

def main():
    run=pd.read_csv(RUNS/'批量实验_run级.csv')
    design=pd.read_excel(RUNS/'实验设计表.xlsx',sheet_name='实验矩阵').rename(columns={'实验编号':'cid'})
    df=run.merge(design,on='cid',how='left')
    df['rescue_dep']=df['rescued']/df['n']
    # 按 cid 聚合（每配置 R 重复的均值）
    agg=df.groupby('cid').agg(survive_rate=('survive_rate','mean'),
        evac_rate=('evac_rate','mean'),rescue_dep=('rescue_dep','mean')).reset_index()
    agg=agg.merge(design,on='cid')
    agg.to_excel(RUNS/'批量实验_配置均值.xlsx',index=False)
    # 因子主效应
    me=[]
    for f in FACTORS:
        for lvl,g in agg.groupby(f):
            me.append({'因子':f,'水平':lvl,'安全率':g.survive_rate.mean(),
                       '自救率':g.evac_rate.mean(),'救援依赖':g.rescue_dep.mean()})
    pd.DataFrame(me).to_excel(RUNS/'批量实验_因子主效应.xlsx',index=False)
    draw_dist(agg); draw_effects(me); draw_inter(agg)
    print('安全率 均值%.3f；救援依赖率 均值%.3f'%(agg.survive_rate.mean(),agg.rescue_dep.mean()))

def draw_dist(agg):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(1,3,figsize=(13,3.8))
    for ax,col,t in zip(axes,['survive_rate','evac_rate','rescue_dep'],
                         ['安全率(自救+救援)','自救撤离率','救援依赖率(需救援比例)']):
        ax.hist(agg[col],bins=24,color='#5b8fc0',edgecolor='white')
        ax.set_title(t,fontsize=11); ax.set_xlabel('比例'); ax.set_ylabel('配置数')
    fig.suptitle('图5-5 大规模计算实验结果分布（96配置×20重复）',fontsize=13,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,.92]); fig.savefig(FIG/'fig_批量结果分布.png',dpi=200,bbox_inches='tight'); plt.close()

def draw_effects(me):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    me=pd.DataFrame(me)
    fig,axes=plt.subplots(2,4,figsize=(15,6.5))
    for ax,f in zip(axes.flat,FACTORS):
        g=me[me['因子']==f].sort_values('水平')
        x=np.arange(len(g))
        ax.bar(x-.2,g['安全率'],width=.4,color='#d98c7a',label='安全率')
        ax.bar(x+.2,g['自救率'],width=.4,color='#7fa8d0',label='自救率')
        ax.set_xticks(x); ax.set_xticklabels(g['水平'],fontsize=8,rotation=20)
        ax.set_ylim(0,1.05); ax.set_title(f,fontsize=10)
    axes[0,0].legend(fontsize=8)
    fig.suptitle('图5-6 各因子对安全率/自救率的主效应',fontsize=13,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,.94]); fig.savefig(FIG/'fig_因子主效应.png',dpi=200,bbox_inches='tight'); plt.close()

def draw_inter(agg):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    piv=agg.pivot_table(index='峰值水深m',columns='播报时机',values='evac_rate',aggfunc='mean')
    cols=[c for c in ['无','早','晚'] if c in piv.columns]; piv=piv[cols]
    fig,ax=plt.subplots(figsize=(6.5,4.6))
    im=ax.imshow(piv.values,cmap='RdYlGn',aspect='auto',vmin=.4,vmax=1)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols)
    ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax.text(j,i,f'{piv.values[i,j]:.2f}',ha='center',va='center',fontsize=10)
    ax.set_xlabel('播报时机'); ax.set_ylabel('峰值水深 (m)')
    ax.set_title('图5-7 峰值水深×播报时机 对自救撤离率的交互',fontsize=12,fontweight='bold')
    fig.colorbar(im,ax=ax,shrink=.8); fig.tight_layout()
    fig.savefig(FIG/'fig_交互_水深播报.png',dpi=200,bbox_inches='tight'); plt.close()

if __name__=='__main__':
    main()
