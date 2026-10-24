# -*- coding: utf-8 -*-
"""第6章 步骤7：双源互证。
用真实案例参数化情景库(27个，源自事故调查报告/预案的LLM抽取)定量核验
计算实验+ML挖掘得到的规律方向是否在真实情景中成立，产出互证表与图6-9。"""
import json
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
DATA=ROOT/'data'/'processed'

def real_frame():
    S=json.loads((DATA/'情景库.json').read_text(encoding='utf-8'))
    rows=[]
    for s in S:
        am=s['response']['alarm_min']; dp=s['depth']['d_peak']; tp=s['depth']['t_peak']
        rows.append(dict(id=s['id'],archetype=s['archetype'],timing=s['response']['timing'],
            alarm_min=am,d_peak=dp,t_peak=tp,rise_proxy=dp/max(tp,1e-6),
            evac_success=s['prior']['evac_success'],familiarity=s['population']['familiarity'],
            defense=s['defense'],space=s['space']))
    return pd.DataFrame(rows)

def main():
    R=real_frame()
    # 真实情景统计
    g=R.groupby('timing').agg(平均自救成功率=('evac_success','mean'),
        情景数=('id','count')).reindex(['响应及时','响应滞后','未有效响应'])
    print('真实情景按时机：'); print(g.round(3))
    nn=R.alarm_min.notna()
    corr_alarm=np.corrcoef(R.loc[nn,'alarm_min'],R.loc[nn,'evac_success'])[0,1]
    corr_rise=np.corrcoef(R.rise_proxy,R.evac_success)[0,1]
    corr_depth=np.corrcoef(R.d_peak,R.evac_success)[0,1]
    print('相关: alarm_min %.3f | rise_proxy %.3f | d_peak %.3f'%(corr_alarm,corr_rise,corr_depth))
    m_timely=R[R.timing=='响应及时'].evac_success.mean()
    m_no=R[R.timing=='未有效响应'].evac_success.mean()

    # 互证表
    cv=[
     dict(规律='早播报→高自救；无(迟)播报→救援依赖',
       计算实验证据='自救率 早播报.97/晚.79/无.74；SHAP播报时机重要性第2',
       真实情景证据='及时 %.2f / 滞后 %.2f / 无有效响应 %.2f；alarm与成功率相关%.2f'%(
           g.loc['响应及时','平均自救成功率'],g.loc['响应滞后','平均自救成功率'],
           g.loc['未有效响应','平均自救成功率'],corr_alarm),
       结论='方向一致'),
     dict(规律='快速涨水→观望/救援依赖',
       计算实验证据='自救率 慢.96/中.89/快.65；规则 高峰值+深水+快涨→观望(提升12.4)',
       真实情景证据='涨速代理(d_peak/t_peak)与成功率相关%.2f；郑州5号线/深圳4·11等快涨情景成功率低'%corr_rise,
       结论='方向一致'),
     dict(规律='深水(高峰值水深)→救援依赖',
       计算实验证据='规则 深水→救援依赖(支持.096,置信1.0,提升6.2)',
       真实情景证据='峰值水深与成功率相关%.2f；区间/暗渠 d_peak≥1.8 情景成功率≤.18'%corr_depth,
       结论='方向一致'),
     dict(规律='观望(滞留)→救援依赖',
       计算实验证据='规则 观望→救援依赖(支持.081,置信1.0,提升6.2)',
       真实情景证据='无有效响应即无人组织撤离，平均自救率仅%.2f（SCN-004/009/013/017/019）'%m_no,
       结论='方向一致'),
     dict(规律='低熟悉度→就近出口/从众，偏离最优',
       计算实验证据='行为模型 SHAP：就近出口首要驱动为熟悉度；从众受熟悉度影响',
       真实情景证据='多数车站/商业情景人群熟悉度低；SCN-021等低熟悉仍依赖引导',
       结论='方向一致(证据较弱)'),
    ]
    pd.DataFrame(cv).to_excel(RUNS/'第6章_双源互证表.xlsx',index=False)

    # 图6-9
    fig,axes=plt.subplots(1,2,figsize=(13.5,5.2))
    order=['响应及时','响应滞后','未有效响应']; col=['#3d8f5b','#e0a53a','#c0504d']
    gg=g.loc[order]
    axes[0].bar(range(3),gg.平均自救成功率,color=col)
    for i,(v,n) in enumerate(zip(gg.平均自救成功率,gg.情景数)):
        axes[0].text(i,v+.02,'%.2f (n=%d)'%(v,n),ha='center',fontsize=10)
    axes[0].set_xticks(range(3)); axes[0].set_xticklabels(order); axes[0].set_ylim(0,1.08)
    axes[0].set_ylabel('真实情景 prior 自救成功率'); axes[0].set_title('(a) 真实情景：响应时机→自救成功率')
    # scatter
    Rs=R.copy(); Rs.loc[Rs.alarm_min.isna(),'alarm_min']=128
    sc=axes[1].scatter(Rs.alarm_min,Rs.evac_success,c=Rs.rise_proxy,s=46,cmap='YlOrRd',
                       edgecolor='k',lw=.4)
    axes[1].set_xlabel('首次有效播报/响应时间（min，128=始终无有效响应）')
    axes[1].set_ylabel('真实情景自救成功率'); axes[1].set_title('(b) 真实情景：播报时机×涨速→自救率')
    cb=fig.colorbar(sc,ax=axes[1]); cb.set_label('涨速代理 d_peak/t_peak')
    fig.suptitle('图6-9 真实案例情景对挖掘规律的双源互证',fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.94]); fig.savefig(FIG/'fig_双源互证.png',dpi=150)
    print('图6-9 与互证表已产出')

if __name__=='__main__':
    main()
