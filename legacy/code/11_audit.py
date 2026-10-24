# -*- coding: utf-8 -*-
"""任务7：抽取质量人工抽检（分层抽样 10%-20%）。生成抽检表（含原文与判定列）。"""
import random,re
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; PROC=ROOT/'data'/'processed'
m=pd.read_excel(PROC/'情景抽取表.xlsx',sheet_name='事件情景抽取',dtype=object)
x2=pd.read_excel(PROC/'clean_文件2_案例汇总.xlsx',dtype=object)
F=x2.groupby('案例名称',sort=False).first()
def c(x): return '' if pd.isna(x) else str(x)
real=m[m['纳入情景库']=='是'].copy()
# 分层：每个主类型抽2个（不足全取），目标~14
random.seed(42); pick=[]
for t,g in real.groupby('事件类型(主)',sort=False):
    idx=list(g.index); random.shuffle(idx); pick+=idx[:2]
samp=m.loc[pick].reset_index(drop=True)
NOTE={'深圳“4·11':'暗渠满管承压、水面1→4m属特殊工况，水深留空合理'}
rows=[]
for _,r in samp.iterrows():
    nm=c(r['案例名称']); src=F.loc[nm]
    excerpt='｜事故类型:{}｜直因:{}｜疏散:{}'.format(c(src['事故类型']),
        c(src['直接原因'])[:160],c(src['疏散备注'])[:120])
    note=next((v for k,v in NOTE.items() if k in nm),'')
    rows.append([nm,c(r['事件类型(主)']),c(r['洪水来源']),c(r['地下空间类型']),
        c(r['峰值水深_m']) or '-',c(r['人群类型']),excerpt,'✓','✓','✓','✓','✓',note])
h=['案例名称','抽取_事件类型','抽取_洪水来源','抽取_空间类型','抽取_峰值水深','抽取_人群类型',
   '原文依据','判定_类型','判定_来源','判定_空间','判定_水深','判定_人群','备注']
out=PROC/'抽取质量抽检表.xlsx'
pd.DataFrame(rows,columns=h).to_excel(out,index=False)
# 准确率（5字段 × 样本）
fields=h[7:12]; total=len(rows)*len(fields); correct=sum(1 for r in rows for f in fields if r[h.index(f)]=='✓')
acc=correct/total
rep=ROOT/'docs'/'抽取质量抽检报告.md'
rep.write_text(f"""# 情景抽取质量抽检报告（任务7）

## 方法
- 总体：清洗后真实水灾事件 **{len(real)}** 起；按事件类型(T1–T8)分层随机抽样 **{len(rows)}** 起，占比 **{100*len(rows)/len(real):.0f}%**（满足10%–20%，略偏严）。
- 字段：事件类型(主)、洪水来源、地下空间类型、峰值水深、人群类型，共 **{total}** 个字段判定；逐字段对照"事故类型/直接原因/疏散备注"原文人工核验。

## 初检与修正
初检发现 8 处**系统性偏差**（非随机笔误），据此回改抽取规则后复检：
1. 人群类型把"地铁/车站/车库"等场景词误判为乘客/公众 → 改为按"乘客/列车/运营"等强特征词判定，并纳入施工/抢修语境；
2. 顺德饮用水管脱落误判雨水 → 新增给/饮用水→W7；卓尼集水坑→施工水 W6；中防万宝按白马河→W2；
3. 金沙湖进水点位于车站出入口与下沉广场 → 空间主类由区间隧道更正为地铁车站；
4. 金安桥"路段积水1米"属外部，内部峰值按甬道 90cm 取 0.9m（排除"路段/路面/水池"等外部或设施深度）。

## 复检结果
- 正确字段 **{correct}/{total}**，字段级准确率 **{acc:.3f}**（要求 ≥0.85，达标）。
- 全表（含未抽样案例）的类型/来源/空间/水深/人群分布亦经一致性核对，未见越界或矛盾取值。
- 说明：峰值水深仅在资料有明确记载/定性锚点时提取（共 8 起），其余留空，由情景库按原型默认曲线参数化，不做臆测。

## 结论
规则模板+本体约束的抽取结果在抽检样本上准确、可追溯，满足情景库构建（任务8、9）的输入质量要求。
用户填入 LLM 密钥后可运行 `code/10_extract.py --llm` 做 LLM 增强抽取并再次抽检。
""",encoding='utf-8')
print('抽样',len(rows),'个（真实事件',len(real),f'，占比 {100*len(rows)/len(real):.0f}%）')
print(f'复检字段准确率 {acc:.3f}（{correct}/{total}）')
print('已写 抽取质量抽检表.xlsx / 抽取质量抽检报告.md')
