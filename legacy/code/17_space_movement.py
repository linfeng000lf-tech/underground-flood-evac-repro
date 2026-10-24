# -*- coding: utf-8 -*-
"""补充情景库可计算层：空间几何模板 + 人-水运动/危险模型 + 关停撤离阈值（xlsx+json）。"""
import json, argparse
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; KN=ROOT/'data'/'knowledge'
# 1) 空间几何模板（典型值，依据 GB50157、GB/T33668、T/CECAS20010、DB4403/T552 及典型工程）
GEOM=[
 # code,名称,典型面积m2,有效出口数,单出口有效宽m,平均内部路径m,最长路径m,疏散方式
 ('S1','地铁车站',3000,4,2.0,80,140,'站台→站厅→出入口楼扶梯'),
 ('S2','地铁区间隧道',0,2,1.1,400,800,'纵向疏散平台/端门→相邻车站或竖井'),
 ('S3','地下车库',3000,2,1.4,60,120,'人行疏散楼梯→地面；坡道禁行'),
 ('S4','地下商业与人防',5000,4,2.0,80,150,'分散安全出口→地面'),
 ('S5','地下管线/管廊(含暗渠)',0,2,0.7,100,300,'检查井/安全口垂直撤离'),
 ('S6','其他隧道',0,2,1.1,500,900,'横通道/紧急出口'),
 ('S7','有限空间/井下作业',20,1,0.6,5,15,'爬梯/三脚架垂直提升'),
 ('S8','矿山井巷',0,2,1.5,200,600,'井筒/巷道→安全出口'),
 ('S9','其他/未明确',1000,2,1.4,50,120,'就近安全出口'),
]
geom_df=pd.DataFrame(GEOM,columns=['空间编码','空间名称','典型面积_m2','有效出口数','单出口有效宽度_m',
    '平均内部路径_m','最长路径_m','疏散方式'])
# 出口单宽通行能力（无水，人/(m·min)）：楼扶梯参考地铁标准取75
geom_df['出口单宽通行能力_人每mmin']=[75,60,60,75,40,60,30,60,60]

# 2) 人-水运动与危险模型（依据深圳大学学报2022水侵疏散、Jonkman、Bernardini、Bristol实验）
MOVE={
 '平地走行速度_mps':1.0,                 # 60 m/min
 '平地速度折减':'v(h)=v0*(1-h/0.70)，h为水深(m)，0≤h<0.70',
 '平地极限水深_m':0.70,
 '楼梯走行速度_mps':0.45,                # 27 m/min
 '楼梯速度折减':'v(h)=v0*(1-h/0.30)，0≤h<0.30',
 '楼梯极限水深_m':0.30,
 '出口有效流动系数N':90,
 '行为分级':{'I':'h<0.10 正常行走','II':'0.10≤h<0.30 缓慢行走',
            'III':'0.30≤h<0.50 移向就近安全口','IV':'0.50≤h<0.70 自行疏散或等待救援'},
 '漂浮失稳水深_成人_m':1.37,'漂浮失稳水深_儿童_m':1.0,
 '流速失稳阈值_mps':{'0.6':'勉强维持平衡','1.0':'可能被冲走','1.5':'几乎无法站立'},
 '通行能力下降_Bristol':{'.15m内':'约9.3%','约.30m':'约14.6%','约.50m以上':'约26%'},
}
# 3) 关停/撤离阈值（处置智能体规则；来源见公开资料登记表）
CLOSE=[
 ('出入口','站外积水达两级台阶或0.30m','设防洪挡板并关闭该出入口'),
 ('车站','有效疏散出口不足2个','关闭车站、暂停服务'),
 ('行车','轨行区积水漫过扣件','区段限速25km/h'),
 ('行车','轨行区积水漫过轨面','禁止列车通过、区段停运'),
 ('行车','多区段停运或供电受损','控制中心决策全线停运'),
 ('站内','积水有蔓延站厅/疏散通道或设备房趋势','关闭车站并组织疏散'),
 ('内涝风险','积水>0.15m/0.30m/0.40m','蓝/黄/橙红分级（CECS）'),
]
close_df=pd.DataFrame(CLOSE,columns=['对象','触发条件','处置动作'])

with pd.ExcelWriter(KN/'空间与运动参数.xlsx',engine='openpyxl') as w:
    geom_df.to_excel(w,sheet_name='空间几何模板',index=False)
    pd.DataFrame([{'参数':k,'取值/说明':json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v}
        for k,v in MOVE.items()]).to_excel(w,sheet_name='水中运动与危险模型',index=False)
    close_df.to_excel(w,sheet_name='关停撤离阈值',index=False)
out={'space_geometry':geom_df.to_dict(orient='records'),'movement_hazard':MOVE,
     'closure_thresholds':close_df.to_dict(orient='records')}
(KN/'空间与运动参数.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('空间几何模板:',len(geom_df),'类空间')
print('已写 空间与运动参数.xlsx / .json')
