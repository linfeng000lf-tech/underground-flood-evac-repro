# -*- coding: utf-8 -*-
"""图：积水中走行速度衰减与行为分级（a）；积水深度—处置动作阈值阶梯（b）。"""
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']; plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; FIG=ROOT/'results'/'figures'
fig,(a,b)=plt.subplots(1,2,figsize=(13.5,5.4))

# (a) 速度衰减 + 行为分级
h=np.linspace(0,1.5,600)
vflat=np.where(h<.70,1.0*(1-h/.70),0.0)
vstair=np.where(h<.30,.45*(1-h/.30),0.0)
bands=[(0,.10,'#e2efda','Ⅰ 正常'),( .10,.30,'#fff2cc','Ⅱ 缓慢'),
       (.30,.50,'#fce4d6','Ⅲ 移向安全口'),(.50,.70,'#f8cbad','Ⅳ 自救/待援'),(.70,1.5,'#d9d9d9','无法移动')]
for x0,x1,c,t in bands:
    a.axvspan(x0,x1,color=c,zorder=0)
    yt=.25 if x0>=.70 else 1.12
    a.text((x0+x1)/2,yt,t,ha='center',fontsize=8.4)
a.plot(h,vflat,color='#1f4e79',lw=2.3,label='平地走行 v0=1.0 m/s')
a.plot(h,vstair,color='#c55a11',lw=2.3,label='楼梯走行 v0=0.45 m/s')
for x,t in [(1.0,'儿童漂浮失稳 1.0'),(1.37,'成人漂浮失稳 1.37')]:
    a.axvline(x,ls='--',lw=1,color='#c00000')
    a.text(x,.62,t,rotation=90,va='center',ha='right',fontsize=8,color='#a0302d')
a.set(xlim=0,ylim=0, xlabel='积水深度 h（m）',ylabel='走行速度（m/s）',title='(a) 积水中走行速度衰减与疏散行为分级')
a.set_xlim(0,1.5); a.set_ylim(0,1.22); a.legend(fontsize=8.5,loc='upper right')

# (b) 处置动作阈值阶梯
edges=[0,.15,.30,.40,.60,1.0,1.4]
acts=['正常监控','预警提示\n涉水慢行','关闭出入口\n设置挡板','关闭车站\n组织疏散','区段停运\n强制撤离','全线停运\n全力救援']
cols=['#e2efda','#fff2cc','#fce4d6','#f4b183','#e06666','#990000']
xx=np.linspace(0,1.4,700); yy=np.zeros_like(xx)
for i in range(len(acts)): yy[(xx>=edges[i])&(xx<edges[i+1])]=i
b.step(xx,yy,where='post',color='#1f4e79',lw=1.8)
for i in range(len(acts)):
    b.fill_between([edges[i],edges[i+1]],0,i,step=None,color=cols[i],alpha=.45,zorder=0)
    b.text((edges[i]+edges[i+1])/2,i+.18,acts[i],ha='center',va='bottom',fontsize=8.2)
for x in edges[1:-1]:
    b.axvline(x,ls=':',lw=.7,color='#999'); b.text(x,-.55,f'{x:.2f}',ha='center',fontsize=7.6)
b.text(.7,-1.05,'行车专项：漫过扣件→限速25km/h；漫过轨面→禁止列车通过（合肥/国家指南）',fontsize=8,color='#444')
b.set(xlim=0,ylim=0,xlabel='人员可达处积水深度（m）',ylabel='处置动作级别',title='(b) 积水深度—处置动作阈值阶梯')
b.set_xlim(0,1.4); b.set_ylim(-1.2,6.2); b.set_yticks([])

plt.tight_layout(); fig.savefig(FIG/'fig_水中运动与危险.png',dpi=200,bbox_inches='tight'); plt.close()
print('已写 fig_水中运动与危险.png')
