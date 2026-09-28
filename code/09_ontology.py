# -*- coding: utf-8 -*-
"""
任务6：水灾情景本体设计（类—属性—关系）。
输出：data/knowledge/情景本体.json、docs/情景本体设计.md、results/figures/fig_情景本体.png
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False

ROOT=Path(__file__).resolve().parents[1]
KNOW=ROOT/'data'/'knowledge'; DOCS=ROOT/'docs'; FIG=ROOT/'results'/'figures'
for d in (KNOW,DOCS,FIG): d.mkdir(parents=True,exist_ok=True)

# ============ 类 ============
# code:(中文名, 英文, 层, 定义)
CLASSES={
 'SC':('水灾情景','FloodScenario','情景','对一次地下空间水灾演化全过程的参数化抽象，是情景库的基本单元'),
 'EV':('水灾事件','FloodEvent','事件','在特定时空发生、具有明确诱因与类型的真实或推演水灾发生事实'),
 'ME':('气象水文环境','MeteorologicalEnvironment','环境','降雨、台风、河道/潮汐水位、预警信号等外部致灾背景'),
 'RS':('致因/风险源','RiskSource','致因','直接/间接导致进水的环境、设施、行为、决策与管理因素'),
 'US':('地下空间','UndergroundSpace','空间','发生水灾的地下建构筑物及其几何与设防属性'),
 'FC':('设施构件','FacilityComponent','空间','出入口、风井、管片、封堵/挡水构件、排水与监测设备'),
 'FW':('洪水水体','Floodwater','水体','进入地下空间的水，以四阶段 depth(t)、流速、含砂率等刻画'),
 'PP':('人群','Population','人员','乘客、作业人员、业主/公众、救援人员等疏散主体'),
 'AC':('疏散行为','EvacuationAction','人员','人群在感知—决策—行动各阶段的逃生行为表现'),
 'ER':('应急响应','EmergencyResponse','响应','政府/企业按级别启动的应急组织与指挥活动'),
 'RA':('处置措施','ResponseAction','响应','封堵、抽排、停运、疏散引导等具体处置动作及时序'),
 'OC':('后果','Outcome','结果','伤亡、直接经济损失、运营中断、疏散成败等结果'),
 'KN':('知识','Knowledge','知识','指导处置与疏散的显性/隐性（含正向）知识'),
}
# ============ 属性（code,名称,数据类型,单位/取值,说明）============
ATTRS={
 'SC':[('sc_id','情景编号','string','SCN-###','主键'),('sc_name','情景名称','string','—',''),
       ('archetype','情景原型','enum','见受控词表',''),('scenario_tree','情景树路径','string','—','分支编码组合'),
       ('prob_band','发生可能性带','enum','低/中/高','基于历史频次')],
 'EV':[('event_time','事件时间','datetime','—',''),('event_type','事件类型(受控)','enum','T1–T8','归并后'),
       ('grade','事故等级','enum','一般/较大/重大/特别重大/不适用/未明确',''),
       ('confidence','推断置信度','enum','明确记载/推断/存疑/不适用','')],
 'ME':[('rainfall','降雨强度','float','mm/h 或 mm/过程',''),('warning','气象预警信号','enum','蓝/黄/橙/红/黑',''),
       ('river_level','河道/潮位状态','enum','常水位/警戒/保证/超保证',''),('typhoon','台风','string','—','可空')],
 'RS':[('direct_cause','直接原因','text','—','环境/行为/决策'),('indirect_cause','间接原因','text','—','管理'),
       ('water_source','洪水来源','enum','W1–W7',''),('failed_component','失效构件','string','—','')],
 'US':[('space_type','地下空间类型','enum','9桶',''),('space_geom','几何/层数','string','—',''),
       ('defense_level','设防高程/挡水','float','m 或 cm',''),('n_exits','连通口/出口数','int','个')],
 'FC':[('component','构件/设备','string','—',''),('status','状态','enum','正常/失效/破坏',''),
       ('drain_capacity','排水能力','float','m³/h',''),('monitor','监测手段','string','—','')],
 'FW':[('depth_t','水深过程 depth(t)','object','四阶段参数','见水深参数化'),('d_peak','峰值水深','float','m'),
       ('velocity','流速','float','m/s',''),('turbidity','含砂/浑浊','enum','清/浑/含砂','')],
 'PP':[('pop_type','人群类型','enum','乘客/作业人员/公众/救援',''),('pop_count','人数','int','人'),
       ('familiarity','环境熟悉度','enum','高/中/低',''),('distribution','初始分布','string','—','')],
 'AC':[('response_time','响应时间','float','min',''),('route_choice','路径选择','text','—',''),
       ('herding','从众/折返','enum','无/从众/折返/其他',''),('evac_status','疏散结果','enum','成功/受阻/遇难','')],
 'ER':[('gov_level','政府响应级别','enum','Ⅰ–Ⅳ/未启动/未明确',''),('ent_level','企业响应级别','enum','一级/二级/未启动/未明确',''),
       ('t_alarm','报警时间','datetime','—',''),('t_start','响应启动时间','datetime','—','')],
 'RA':[('action','处置动作','text','—',''),('t_action','动作时间','datetime','—',''),
       ('resource','资源/装备','string','—',''),('seq','时序序号','int','—','')],
 'OC':[('dead','死亡人数','int','人'),('missing','失踪人数','int','人'),('injured','受伤人数','int','人'),
       ('loss_wan','直接经济损失','float','万元'),('interrupt_h','中断时长','float','小时'),
       ('evac_success','疏散成败','enum','成功/部分/失败/未明确','')],
 'KN':[('explicit_k','显性知识','text','—',''),('tacit_k','隐性知识','text','—',''),
       ('positive_k','正向隐性知识','text','—','专家经验')],
}
# ============ 关系（domain,关系,range,基数,说明）============
RELATIONS=[
 ('ME','产生来水','FW','1:n','降雨/河水/潮水形成进水来源'),
 ('ME','诱发','RS','1:n','极端天气暴露设施与管理薄弱点'),
 ('RS','破坏/失效','FC','1:n','风险源导致挡水/封堵/密封构件失效'),
 ('RS','导致','EV','n:1','风险源耦合触发事件'),
 ('US','包含','FC','1:n','地下空间由各类构件组成'),
 ('FW','淹没','US','n:1','水体以 depth(t) 淹没空间'),
 ('FC','过水/溃决','FW','1:n','失效构件成为过水通道'),
 ('EV','发生于','US','n:1','事件定位到地下空间'),
 ('EV','演化为','SC','n:1','真实事件经参数化成为情景'),
 ('SC','链式/分支','SC','1:n','情景链前态→后态、情景树分支'),
 ('PP','初始位于','US','n:1','人群初始分布于空间'),
 ('PP','执行','AC','1:n','人群产生疏散行为'),
 ('AC','作用于','FW','n:1','行为受水深等水体条件约束'),
 ('ER','响应','EV','1:1','针对事件启动响应'),
 ('ER','实施','RA','1:n','响应组织并实施处置动作'),
 ('RA','调控','FW','1:n','封堵/抽排改变 depth(t)'),
 ('RA','引导','AC','1:n','疏散引导改变人群行为'),
 ('EV','导致','OC','1:1','事件产生后果'),
 ('KN','指导','RA','1:n','知识支撑处置决策'),
 ('KN','指导','AC','1:n','知识/经验影响疏散'),
]

ontology={'classes':CLASSES,'attributes':ATTRS,'relations':[
 {'domain':d,'relation':r,'range':g,'cardinality':card,'note':note} for d,r,g,card,note in RELATIONS]}
(KNOW/'情景本体.json').write_text(json.dumps(ontology,ensure_ascii=False,indent=2),encoding='utf-8')

# ============ Markdown 规范 ============
md=['# 城市地下空间水灾情景本体设计','',
 '> 采用“类（Class）—属性（Attribute）—关系（Relation）”三元结构建模，作为第3章情景抽取、参数化与情景库构建的统一语义框架。本体图见 `results/figures/fig_情景本体.png`，机器可读版见 `data/knowledge/情景本体.json`。','',
 '## 1. 建模目标与范围','',
 '- 统一“真实案例—抽取实例—参数化情景”的语义口径，支撑 LLM 抽取、RAG 知识组织与智能体计算实验。',
 '- 范围聚焦城市地下空间（地铁车站/区间、隧道、地下车库与商业、管廊、有限空间等）水灾（进水/倒灌/透水/突水突泥）的演化、人群疏散与应急处置。','',
 '## 2. 类（13类）','',
 '| 编码 | 类 | 英文 | 层 | 定义 |','|---|---|---|---|---|']
for code,(zh,en,layer,desc) in CLASSES.items():
    md.append(f'| {code} | {zh} | {en} | {layer} | {desc} |')
md+=['','## 3. 属性','']
for code,ats in ATTRS.items():
    zh=CLASSES[code][0]
    md+=[f'### {code} {zh}','', '| 属性编码 | 名称 | 数据类型 | 单位/取值 | 说明 |','|---|---|---|---|---|']
    for tup in ats:
        a,n,t,u,*rest=tup; desc=rest[0] if rest else ''
        md.append(f'| {a} | {n} | {t} | {u} | {desc} |')
    md.append('')
md+=['## 4. 关系（20条）','',
 '| 主体类 | 关系 | 客体类 | 基数 | 说明 |','|---|---|---|---|---|']
code2zh={k:v[0] for k,v in CLASSES.items()}
for d,r,g,card,note in RELATIONS:
    md.append(f'| {code2zh[d]} | {r} | {code2zh[g]} | {card} | {note} |')
md+=['','## 5. 本体使用约定','',
 '1. 每个情景（SC）唯一对应一条四阶段 depth(t) 参数与一组人群/响应初值。',
 '2. 情景链表达时间演化（前态→后态），情景树表达关键不确定变量的分支（见第9步）。',
 '3. 抽取阶段无法确定的属性统一置“未明确”，并在置信度字段标注，禁止臆造。','']
(DOCS/'情景本体设计.md').write_text('\n'.join(md),encoding='utf-8')

# ============ 本体图 ============
fig,ax=plt.subplots(figsize=(15.5,9)); ax.set_xlim(0,17); ax.set_ylim(0,10); ax.axis('off')
layer_color={'环境':'#DCEBF7','致因':'#DCEBF7','空间':'#D9EDE3','水体':'#D9EDE3',
 '事件':'#FBE6D2','情景':'#FBE6D2','人员':'#FBF3D2','响应':'#E7E1F0','结果':'#F8DCDC','知识':'#E7E1F0'}
# code:(x,y)
pos={'ME':(1.7,8.4),'RS':(5.0,8.4),'US':(3.4,5.9),'FC':(6.9,5.9),'FW':(3.4,3.2),
 'EV':(10.3,5.9),'SC':(10.3,3.2),'PP':(13.4,5.9),'AC':(13.4,3.2),
 'ER':(15.9,5.9),'RA':(15.9,3.2),'OC':(12.2,0.8),'KN':(15.4,0.8)}
W,H=1.9,0.78
box_xy={}
for code,(x,y) in pos.items():
    zh=CLASSES[code][0]; layer=CLASSES[code][2]
    box=FancyBboxPatch((x-W/2,y-H/2),W,H,boxstyle='round,pad=0.04,rounding_size=0.12',
        linewidth=1.1,edgecolor='#7F7F7F',facecolor=layer_color.get(layer,'#EEEEEE'))
    ax.add_patch(box)
    ax.text(x,y,f'{code}\n{zh}',ha='center',va='center',fontsize=10.5,fontweight='bold')
    box_xy[code]=(x,y)
def edge(a,b,label,rad=0.0,lx=None,ly=None,color='#666666'):
    x1,y1=box_xy[a]; x2,y2=box_xy[b]
    arr=FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=12,
        linewidth=1.0,color=color,shrinkA=26,shrinkB=26,connectionstyle=f'arc3,rad={rad}')
    ax.add_patch(arr)
    if label:
        mx=(x1+x2)/2 if lx is None else lx; my=(y1+y2)/2 if ly is None else ly
        ax.text(mx,my,label,ha='center',va='center',fontsize=8.3,color='#333333',
            bbox=dict(boxstyle='round,pad=0.12',fc='white',ec='none',alpha=0.9))
# (a,b,label,rad,lx,ly)
edges=[
 ('ME','FW','产生来水',-0.18,1.5,5.7),('ME','RS','诱发',0,None,None),
 ('RS','FC','失效',0,5.9,7.25),('RS','EV','导致',0.12,7.9,7.4),
 ('US','FC','包含',0,None,None),('FW','US','淹没',0,None,None),
 ('FC','FW','溃决过水',0.2,4.7,4.35),
 ('EV','US','发生于',0.18,6.7,5.15),('EV','SC','演化为',0,None,None),
 ('PP','US','位于',0.22,8.6,7.05),('PP','AC','执行',0,None,None),
 ('AC','FW','受约束',0.18,8.5,2.55),
 ('ER','EV','响应',0,13.1,6.55),('ER','RA','实施',0,None,None),
 ('RA','FW','调控',-0.28,7.0,1.85),('RA','AC','引导',0.12,14.7,2.75),
 ('EV','OC','导致',0.15,11.2,2.15),
 ('KN','RA','指导',0,15.9,1.95),('KN','AC','指导',-0.22,13.4,1.55)]
for a,b,lab,rad,lx,ly in edges: edge(a,b,lab,rad,lx,ly)
# SC 自环（情景链式/分支）
loop=FancyArrowPatch((11.2,3.5),(11.2,2.9),connectionstyle='arc3,rad=-1.6',
    arrowstyle='-|>',mutation_scale=11,linewidth=1.0,color='#666666',shrinkA=2,shrinkB=2)
ax.add_patch(loop); ax.text(12.0,3.2,'链式/分支',ha='center',va='center',fontsize=8.3,
    bbox=dict(boxstyle='round,pad=0.12',fc='white',ec='none',alpha=0.9))
ax.text(8.5,9.65,'城市地下空间水灾情景本体（类—属性—关系）',ha='center',fontsize=15,fontweight='bold')
plt.tight_layout(); plt.savefig(FIG/'fig_情景本体.png',dpi=200,bbox_inches='tight'); plt.close()
print('本体类',len(CLASSES),'属性类',len(ATTRS),'关系',len(RELATIONS))
print('已写 情景本体.json / 情景本体设计.md / fig_情景本体.png')
