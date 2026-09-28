# -*- coding: utf-8 -*-
"""任务9图：情景链（时间演化）与情景树（分支推演）。"""
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']; plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; FIG=ROOT/'results'/'figures'
fig,(ax,ax2)=plt.subplots(2,1,figsize=(13.5,10.2))

def box(ax,x,y,w,h,text,fc,fs=9.5,tc='#1a1a1a'):
    b=FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.02,rounding_size=0.08',
        fc=fc,ec='#7a7a7a',lw=1.1); ax.add_patch(b)
    ax.text(x,y,text,ha='center',va='center',fontsize=fs,color=tc,wrap=True)
def arrow(ax,x1,y1,x2,y2,rad=0,color='#666'):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=13,
        lw=1.1,color=color,shrinkA=20,shrinkB=20,connectionstyle=f'arc3,rad={rad}'))

# ---------- (a) 情景链 ----------
ax.set_xlim(0,17); ax.set_ylim(2,8.6); ax.axis('off')
stages=[('诱因\n气象水文/风险源\nME·RS','#dbe9f6'),('进水\n水灾事件 T1–T8\nEV','#fde6d2'),
 ('蔓延\n地下空间·洪水水体\nUS·FW','#d9ece0'),('峰值淹没\ndepth(t) 四阶段\nFW','#d9ece0'),
 ('疏散·处置\n人群·行为·响应\nPP·AC·ER·RA','#e8e0f0'),('后果\n伤亡/损失\nOC','#f6d9d4')]
xs=[1.6,4.2,6.8,9.4,12.0,14.6]; w=2.3
for (t,fc),x in zip(stages,xs): box(ax,x,6,w,1.5,t,fc,fs=9.3)
for i in range(len(xs)-1): arrow(ax,xs[i]+w/2,6,xs[i+1]-w/2,6)
ax.text(8.5,8.1,'(a) 情景链：城市地下空间水灾时间演化',ha='center',fontsize=13,fontweight='bold')
ax.text(8.5,3.6,'本体关系：诱发 → 导致/发生于 → 淹没/蔓延 → 演化为 → 响应/执行/实施 → 导致',
        ha='center',fontsize=9.5,color='#444')
ax.text(8.5,2.9,'每阶段均为本体实例；时间轴由 depth(t) 与响应时序参数共同驱动',
        ha='center',fontsize=9,color='#666')

# ---------- (b) 情景树（以A1地铁车站暴雨倒灌为例）----------
ax2.set_xlim(0,17); ax2.set_ylim(1,10.2); ax2.axis('off')
box(ax2,8.5,9.4,4.2,.9,'水灾情景（以 A1 地铁车站·暴雨倒灌为例）','#fde6d2',fs=10.5)
# L1 设防/排水综合能力
l1=[(2.9,'能力充足\n设防达标·排水充分','#d9ece0'),(8.5,'能力一般\n设防薄弱·排水一般','#fdf0d9'),
    (14.1,'能力失效\n设防失效·排水失效','#f6d9d4')]
for x,t,fc in l1: box(ax2,x,7.4,3.4,1.0,t,fc,fs=9.2)
for x,_,_ in l1: arrow(ax2,8.5,8.95,x,7.9,rad=0.12 if x<8.5 else -0.12)
# L2 响应时机
l2=[(1.5,'及时',2.9),(4.3,'滞后',2.9),(7.1,'及时',8.5),(9.9,'滞后',8.5),
    (12.7,'滞后',14.1),(15.3,'未响应',14.1)]
for x,t,parent in l2: box(ax2,x,5.0,1.9,.7,t,'#e8e0f0',fs=9)
for x,_,parent in l2: arrow(ax2,parent,6.9,x,5.35,rad=0)
# L3 风险叶
leaf=[(1.5,'低','#cfe8cf'),(4.3,'中','#fde3bd'),(7.1,'中','#fde3bd'),(9.9,'高','#f4c3bd',),
      (12.7,'高','#f4c3bd'),(15.3,'高(致死)','#ecaaa2')]
for x,t,fc in leaf:
    box(ax2,x,2.6,2.0,.85,t,fc,fs=9.3); arrow(ax2,x,4.65,x,3.05)
ax2.text(8.5,1.35,'叶节点 = 先验风险带（低/中/高）；情景库对每个原型×分支组合实例化为参数化情景',
         ha='center',fontsize=9.3,color='#444')
ax2.text(8.5,10.0,'(b) 情景树：关键不确定变量分支推演',ha='center',fontsize=13,fontweight='bold')

plt.tight_layout(); fig.savefig(FIG/'fig_情景链树.png',dpi=200,bbox_inches='tight'); plt.close()
print('已写 fig_情景链树.png')
