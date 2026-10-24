# -*- coding: utf-8 -*-
"""任务8-②：水深四阶段参数化 depth(t)（梯形模型）+ 原型参数模板 + 图。"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']; plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; PROC=ROOT/'data'/'processed'; FIG=ROOT/'results'/'figures'

# 定性水深锚点（m）：(名称, 代表值)
ANCHORS=[('脚踝 0.10–0.15',0.12),('膝盖 0.40–0.50',0.45),('腰部 ~1.0',1.0),
         ('胸部 ~1.3',1.3),('没顶 >1.7',1.75)]

def depth_t(t,p):
    """梯形四阶段。p: d0,t_seep,t_peak,t_plat,t_end,d_peak"""
    d0,ts,tpk,tpl,te,dp=p
    t=np.asarray(t,float); out=np.zeros_like(t)
    rup=(dp-d0)/max(tpk-ts,1e-9); rdn=dp/max(te-(tpk+tpl),1e-9)
    s1=t<ts; out[s1]=d0*t[s1]/max(ts,1e-9)
    s2=(t>=ts)&(t<tpk); out[s2]=d0+rup*(t[s2]-ts)
    s3=(t>=tpk)&(t<tpk+tpl); out[s3]=dp
    s4=(t>=tpk+tpl)&(t<te); out[s4]=dp-rdn*(t[s4]-(tpk+tpl))
    out[t>=te]=0
    return out

# 原型模板: code,名称,d0,t_seep,t_peak,t_plat,t_end,dp低,dp基,dp高,标定案例,说明
TPL=[
 ('A1','地铁车站·暴雨倒灌',.03,5,25,120,300,.3,.6,1.0,'金安桥0.9/小寨','上涨以分钟计，峰值持续至抽排'),
 ('A2','地铁区间·洪水漫灌',.03,3,15,90,240,.6,1.2,1.8,'郑州5号线','列车迫停、水深可达胸/头，致死性高'),
 ('A3','地下车库·积水倒灌',.03,15,60,240,600,.2,.5,1.2,'龙领/回龙观1.0','演进较慢，业主常冒险挪车'),
 ('A4','地下商业·洪水涌入',.03,10,30,180,420,.3,.7,1.2,'济南银座','客流时段敏感，疏散窗口短'),
 ('A5','管线暗渠·暴洪',.05,2,10,60,180,1.0,2.0,4.0,'深圳4·11(水面1→4m)','满管承压，水深可超人高，特殊工况'),
 ('A6','施工隧道·突水突泥',.05,2,12,60,200,.5,1.2,2.0,'佛山2·7/石景山','掌子面突发、量大、撤离极短'),
 ('A7','有限空间·作业淹溺',.03,1,8,40,120,.4,.9,1.5,'新昌路管内1.32','水位突涨、盲目施救扩大伤亡'),
 ('A8','结构/管涌渗漏',.02,20,60,120,400,.2,.5,1.0,'金沙湖/中防万宝','起病缓、经通道持续渗入'),
 ('A9','台风伴生内涝',.03,10,45,300,700,.3,.7,1.3,'福州海葵/华浙','历时长、范围广、潮位顶托'),
 ('A10','管道爆裂(给水/消防)',.02,2,15,60,150,.1,.3,.6,'天潼路','清水、点源、关停后可控'),
]
cols=['code','原型名称','d0','t_seep','t_peak','t_plat','t_end','dp_低','dp_基准','dp_高','标定案例','说明']
df=pd.DataFrame(TPL,columns=cols)
df.to_excel(PROC/'水深参数化模板.xlsx',index=False)
js=[dict(zip(cols,row)) for row in TPL]
(PROC/'水深参数化模板.json').write_text(json.dumps(js,ensure_ascii=False,indent=2),encoding='utf-8')

# ---------- 图 ----------
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(13.5,5.2))
# 左：四阶段模型（示意性均衡参数，仅用于说明；真实模板见右图）
IL_d0,IL_ts,IL_tpk,IL_tpl,IL_te,IL_dp=.05,35,100,110,300,.6
p=[IL_d0,IL_ts,IL_tpk,IL_tpl,IL_te,IL_dp]
tt=np.linspace(0,IL_te,600); dd=depth_t(tt,p)
phcol=['#dbe9f6','#fde6d2','#f6d9d4','#e3ecdd']
bounds=[0,IL_ts,IL_tpk,IL_tpk+IL_tpl,IL_te]
names=['①进水/渗漏期','②上涨期','③峰值/淹没期','④退水/恢复期']
for i in range(4):
    ax1.axvspan(bounds[i],bounds[i+1],color=phcol[i],zorder=0)
    ax1.text((bounds[i]+bounds[i+1])/2,1.18,names[i],ha='center',fontsize=9.5)
ax1.plot(tt,dd,color='#1f4e79',lw=2.2,zorder=3)
for nm,v in ANCHORS:
    ax1.axhline(v,ls='--',lw=.9,color='#c0504d',zorder=1)
    ax1.text(IL_te+8,v,nm,va='center',fontsize=8.3,color='#a0302d')
for x,lab in [(IL_ts,'t_seep'),(IL_tpk,'t_peak'),(IL_tpk+IL_tpl,'t_peak+t_plat'),(IL_te,'t_end')]:
    ax1.axvline(x,ls=':',lw=.7,color='#888'); ax1.text(x,-.17,lab,ha='center',fontsize=7.6)
ax1.set(xlim=(-8,IL_te+105),ylim=(-.23,1.28),xlabel='时间 t（min，相对进水时刻）',ylabel='水深 depth(t)（m）',title='(a) 水深四阶段梯形参数化模型（示意）')
# 右：10原型基准曲线
cmap=plt.cm.tab10(np.linspace(0,1,len(df)))
for (_,r),c in zip(df.iterrows(),cmap):
    p=[r.d0,r.t_seep,r.t_peak,r.t_plat,r.t_end,r.dp_基准]
    tt=np.linspace(0,r.t_end,400)
    ax2.plot(tt,depth_t(tt,p),color=c,lw=1.6,label=f"{r.code} {r['原型名称']}")
ax2.set(xlim=(-5,720),xlabel='时间 t（min）',ylabel='水深（m）',title='(b) 10类情景原型的基准水深过程')
ax2.legend(fontsize=7.4,loc='upper right',framealpha=.9)
plt.tight_layout()
fig.savefig(FIG/'fig_水深四阶段.png',dpi=200,bbox_inches='tight'); plt.close()

# 说明书
(ROOT/'docs'/'水深参数化说明.md').write_text("""# 水深四阶段参数化说明（任务8）

## 1. 模型形式
以进水时刻为 t=0，水深过程 depth(t) 用**梯形四阶段**刻画，参数：
`d0`（初期渗流水深）、`t_seep`（进水/渗漏期结束）、`t_peak`（达到峰值）、
`t_plat`（峰值平台时长）、`t_end`（退水完成）、`d_peak`（峰值水深）。
- ① 进水/渗漏期 [0,t_seep]：0→d0 缓慢；
- ② 上涨期 [t_seep,t_peak]：以 r_up=(d_peak−d0)/(t_peak−t_seep) 线性上涨；
- ③ 峰值/淹没期 [t_peak,t_peak+t_plat]：维持 d_peak；
- ④ 退水/恢复期 [t_peak+t_plat,t_end]：以 r_down=d_peak/(t_end−t_peak−t_plat) 线性回落。

## 2. 定性—定量锚点（用于无实测资料时的参数标定）
脚踝 0.10–0.15m；膝盖 0.40–0.50m；腰部 ~1.0m；胸部 ~1.3m；没顶 >1.7m。
并与规范阈值衔接：深圳 SJG 162-2024 连通口设防高差 ≥0.50/0.30–0.50/≤0.30m 对应 3/2/1 级积水；
下穿隧道 1–15/15–27/>27cm 对应 低/中/高风险。

## 3. 原型模板
共 10 类（A1–A10，事件类型×空间类型），每类给出时间参数与 d_peak 低/基准/高三档，
基准值由有明确记载的案例标定（金安桥0.9、回龙观1.0、新昌路管内1.32、4·11水面1→4m 等）。
暗渠暴洪(A5)为满管承压特殊工况，水深可超人高；人员疏散意义下仅需关注至没顶(~1.7m)。

## 4. 使用
情景库（任务9）按原型取参数并在档位内受控变异，生成参数化情景；
机器可读 `水深参数化模板.json`，函数 `depth_t(t,p)` 供后续智能体计算实验直接调用。
""",encoding='utf-8')
print('原型模板',len(df),'类；已写 水深参数化模板.xlsx/.json、fig_水深四阶段.png、水深参数化说明.md')
