# -*- coding: utf-8 -*-
"""情景库数据完整性/正确性/可用性审计。"""
import json
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; PROC=ROOT/'data'/'processed'
scn=json.loads((PROC/'情景库.json').read_text(encoding='utf-8'))
df=pd.read_excel(PROC/'情景库.xlsx',dtype=object)
clean2=pd.read_excel(PROC/'clean_文件2_案例汇总.xlsx',dtype=object)
cases=set(clean2['案例名称'].dropna().astype(str))

def depth_t(t,p):
    d0,ts,tpk,tpl,te,dp=p
    if t<=ts: return d0*t/ts if ts>0 else d0
    if t<=tpk: return d0+(dp-d0)*(t-ts)/(tpk-ts)
    if t<=tpk+tpl: return dp
    if t<=te: return dp*(te-t)/(te-tpk-tpl)
    return 0.0

issues=[]; warns=[]
TOP={'id','name','archetype','event','water_source','space','defense','drain','population','response','depth','prior'}
POP_EXPECT={'S5':'作业人员','S6':'作业人员','S7':'作业人员','S8':'作业人员','S1':'乘客','S2':'乘客','S3':'公众','S4':'公众'}
NCOUNT={'S1':(50,300,1200),'S2':(20,250,500),'S3':(8,40,180),'S4':(40,400,2000),
 'S5':(3,8,15),'S6':(10,40,120),'S7':(1,3,6),'S8':(10,40,150),'S9':(5,20,80)}
SCALE_KEY={'小规模':0,'中等规模':1,'大规模':2}
# 期望风险/成功（与14一致）
def expect_prior(dp,timing,scale):
    ds=0 if dp<.15 else 1 if dp<.5 else 2 if dp<1.0 else 3 if dp<1.3 else 4 if dp<1.7 else 5
    rs={'响应及时':-1,'响应滞后':0,'未有效响应':1}[timing]; tot=ds+rs+(1 if scale=='大规模' else 0)
    band='高' if tot>=4 else '中' if tot>=2 else '低'
    succ=round(float(np.clip(0.99-dp*.28+{'响应及时':.12,'响应滞后':0,'未有效响应':-.28}[timing],.05,.99)),2)
    return band,succ

for s in scn:
    sid=s['id']
    miss=TOP-set(s)
    if miss: issues.append(f'{sid} 缺顶层字段 {miss}')
    d=s['depth']; r=s['response']; pp=s['population']; pr=s['prior']
    # 时间序
    if not (0<=d['t_seep']<d['t_peak']<d['t_peak']+d['t_plat']<d['t_end']):
        issues.append(f'{sid} 时间参数顺序错误 {d}')
    if not (0<=d['d0']<=d['d_peak']): issues.append(f'{sid} d0/d_peak 异常')
    # depth_t 复现峰值
    p=[d['d0'],d['t_seep'],d['t_peak'],d['t_plat'],d['t_end'],d['d_peak']]
    if abs(depth_t(d['t_peak'],p)-d['d_peak'])>1e-6: issues.append(f'{sid} depth_t 峰值不可复现')
    if depth_t(d['t_end']+1,p)!=0: warns.append(f'{sid} t_end后未归零')
    # 报警/启动与时机
    if r['timing']=='未有效响应':
        if r['alarm_min'] is not None or r['start_min'] is not None:
            issues.append(f'{sid} 未响应却有时间')
    else:
        if r['alarm_min'] is None or r['start_min'] is None: issues.append(f'{sid} 响应却缺时间')
        elif r['alarm_min']>r['start_min']: issues.append(f'{sid} 报警晚于启动')
    # 人群类型与空间
    if POP_EXPECT.get(s['space']) and pp['type']!=POP_EXPECT[s['space']]:
        issues.append(f"{sid} 人群类型 {pp['type']} 与空间 {s['space']} 不符")
    # n_ref 与规模/空间
    exp_n=NCOUNT[s['space']][SCALE_KEY[pp['scale']]]
    if pp['n_ref']!=exp_n: issues.append(f"{sid} n_ref={pp['n_ref']} 期望{exp_n}")
    # 先验
    eb,es=expect_prior(d['d_peak'],r['timing'],pp['scale'])
    if pr['risk_band']!=eb: issues.append(f"{sid} 风险带 {pr['risk_band']} 期望{eb}")
    if abs(pr['evac_success']-es)>0.011: issues.append(f"{sid} 成功先验 {pr['evac_success']} 期望{es}")
    # 锚定案例存在
    if s['archetype'] not in cases: issues.append(f"{sid} 锚定案例不在库: {s['archetype']}")

# xlsx 与 json 一致性
if len(df)!=len(scn): issues.append('xlsx/json 条数不一致')
xids=list(df['情景编号']); jids=[s['id'] for s in scn]
if xids!=jids: issues.append('xlsx/json 编号顺序不一致')

print('=== 情景库审计 ===')
print('情景数:',len(scn))
print('\n-- 覆盖度 --')
print('模板:',df['模板'].value_counts().sort_index().to_dict())
print('事件类型:',df['事件类型'].value_counts().sort_index().to_dict())
print('空间类型:',df['空间类型'].value_counts().sort_index().to_dict())
print('风险带:',df['先验风险带'].value_counts().to_dict())
print('可能性带:',df['发生可能性带'].value_counts().to_dict())
print('\n-- 问题(ERROR) --', len(issues))
for i in issues: print(' ✗',i)
print('\n-- 警告(WARN) --', len(warns))
for w in warns: print(' !',w)
print('\n结论:', '通过，无错误' if not issues else f'存在{len(issues)}处错误')
