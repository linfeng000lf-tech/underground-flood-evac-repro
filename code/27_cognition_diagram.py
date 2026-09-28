# -*- coding: utf-8 -*-
"""第4章 图4-2：认知驱动的疏散智能体认知架构（感知—评估—应对—行动）。"""
from pathlib import Path
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']; plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; FIG=ROOT/'results'/'figures'

fig,ax=plt.subplots(figsize=(13,6.4)); ax.axis('off'); ax.set_xlim(0,13); ax.set_ylim(0,8)
blocks=[
 ('① 感知','本节点/邻居水深\n出口开闭·广播\n标识·周围人群动作','有限理性：局部、不确定信息',1.0,'#dbe9f6'),
 ('② 评估','威胁评估：水深/上涨\n应对资源：知识·经验·熟悉度\n社会线索：他人反应','保护动机理论 PMT',4.2,'#fde6d2'),
 ('③ 应对','动作白名单：\n立即撤离·就近出口·跟随引导\n从众·观望·折返·互助·避险','社会影响 + 损失厌恶',7.4,'#e8e0f0'),
 ('④ 行动','规则层可达性裁决\n涉水移动·瓶颈排队\n到达出口/受困','决策/运动解耦',10.6,'#d9ece0'),
]
for t,body,th,x,fc in blocks:
    ax.add_patch(FancyBboxPatch((x,3.6),2.6,2.5,boxstyle='round,pad=.03',fc=fc,ec='#7a8791',lw=1.3))
    ax.text(x+1.3,5.75,t,ha='center',fontsize=12.5,fontweight='bold')
    ax.text(x+1.3,4.75,body,ha='center',va='center',fontsize=8.6)
    ax.text(x+1.3,3.15,th,ha='center',fontsize=8.3,style='italic',color='#445')
for x in (3.6,6.8,10.0):
    ax.add_patch(FancyArrowPatch((x,4.85),(x+.6,4.85),arrowstyle='-|>',mutation_scale=15,color='#555'))

# 输入
ax.text(1.0,6.55,'环境/情景输入',ha='left',fontsize=9,color='#356')
# 知识库与画像（贯穿评估/应对）
ax.add_patch(FancyBboxPatch((4.0,6.7),6.2,.7,boxstyle='round,pad=.02',fc='#fff4d6',ec='#c9a84a'))
ax.text(7.1,7.05,'异质人群画像 + RAG知识库（显性规范/阈值 + 隐性行为倾向）',ha='center',fontsize=9)
ax.add_patch(FancyArrowPatch((7.1,6.7),(7.1,6.1),arrowstyle='-|>',mutation_scale=12,color='#b08d2a'))

# 反馈闭环
ax.add_patch(FancyArrowPatch((11.9,3.6),(11.9,1.5),arrowstyle='-',color='#888'))
ax.add_patch(FancyArrowPatch((11.9,1.5),(2.3,1.5),arrowstyle='-',color='#888'))
ax.add_patch(FancyArrowPatch((2.3,1.5),(2.3,3.6),arrowstyle='-|>',mutation_scale=14,color='#888'))
ax.text(7.1,1.2,'环境反馈：位置/水深变化进入下一时刻感知（闭环）',ha='center',fontsize=9,color='#666')

ax.text(6.5,7.9,'图4-2 认知驱动的疏散智能体认知架构',ha='center',fontsize=14,fontweight='bold')
fig.savefig(FIG/'fig_认知架构.png',dpi=200,bbox_inches='tight'); plt.close()
print('已写 fig_认知架构.png')
