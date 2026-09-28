# -*- coding: utf-8 -*-
"""3.3 统一标识 + 标签归并映射 + 要素/动作/知识编码表；回写清洗文件。"""
import re, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; PROC=ROOT/'data'/'processed'
f2=pd.read_excel(PROC/'clean_文件2_案例汇总.xlsx',dtype=object)
f1=pd.read_excel(PROC/'clean_文件1_应急数据.xlsx',dtype=object)

# 1) 案例/事件标识（file2 为超集，按其出现顺序）
cases=[]
for n in f2['案例名称'].dropna():
    if n not in cases: cases.append(n)
case_reg=[]
for i,n in enumerate(cases,1):
    sub=f2[f2['案例名称']==n].iloc[0]
    case_reg.append({'case_id':f'CASE-{i:04d}','event_id':f'EVT-{i:04d}','案例名称':n,
        '事件类型':sub.get('事故类型'),'空间类型':sub.get('地下空间类型'),
        '事故等级':sub.get('事故等级'),'事件时间':sub.get('事件时间'),
        '含应急数据(文件1)':'是' if n in set(f1['案例名称'].dropna()) else '否'})
case_df=pd.DataFrame(case_reg)
name2id={r['案例名称']:r['case_id'] for _,r in case_df.iterrows()}

# 2) 记录标识并回写
f2.insert(0,'record_id',[f'REC2-{i:04d}' for i in range(1,len(f2)+1)])
f2.insert(0,'event_id',f2['案例名称'].map({r['案例名称']:r['event_id'] for _,r in case_df.iterrows()}))
f2.insert(0,'case_id',f2['案例名称'].map(name2id))
f1.insert(0,'record_id',[f'REC1-{i:04d}' for i in range(1,len(f1)+1)])
f1.insert(0,'event_id',f1['案例名称'].map({r['案例名称']:r['event_id'] for _,r in case_df.iterrows()}))
f1.insert(0,'case_id',f1['案例名称'].map(name2id))
f2.to_excel(PROC/'clean_文件2_案例汇总.xlsx',index=False)
f1.to_excel(PROC/'clean_文件1_应急数据.xlsx',index=False)
rec2=f2[['record_id','case_id','案例名称','工作流程环节']].copy(); rec2.columns=['record_id','case_id','案例名称','环节/内容']
rec1=f1[['record_id','case_id','案例名称','数据具体内容(原)']].copy(); rec1.columns=['record_id','case_id','案例名称','环节/内容']

# 3) 标签归并映射（原始分类 → 标准大类 A-G）
lab=[]
for raw,g in f1.groupby('原始分类'):
    vc=g['标准大类名称'].value_counts()
    primary=vc.index[0]; code=g.loc[g['标准大类名称']==primary,'标准大类编码'].iloc[0]
    subq=re.search(r'（(.+?)）',str(raw))
    lab.append({'原始标签':raw,'出现次数':len(g),'归并编码':code,'归并大类':primary,
        '子类(括号内)':subq.group(1) if subq else '',
        '是否一对多':'是(取主类)' if len(vc)>1 else '否'})
lab_df=pd.DataFrame(lab).sort_values(['归并编码','出现次数'],ascending=[True,False])

# 4) 统一编码表
cv=json.loads((PROC/'受控词表.json').read_text(encoding='utf-8'))
elem=[]
for dim,items in cv.items():
    for it in items:
        elem.append({'维度':dim,'编码':it['code'],'术语':it['term']})
elem_df=pd.DataFrame(elem)
RA=[('RA1','预警发布与气象监测'),('RA2','接警与信息上报'),('RA3','关闭出入口/设置防洪挡板'),
 ('RA4','列车限速'),('RA5','区段/线路停运'),('RA6','关闭车站'),('RA7','广播与组织疏散'),
 ('RA8','进水点封堵抢险'),('RA9','应急抽排'),('RA10','人员搜救'),('RA11','医疗救护'),
 ('RA12','处置失效/盲目施救(负向)')]
ra_df=pd.DataFrame(RA,columns=['编码','处置动作'])
KN=[('KN1','事件事理与事态演进知识'),('KN2','环境与气象水文监测知识'),('KN3','设备设施状态知识'),
 ('KN4','结构与工程安全知识'),('KN5','人员观察与疏散行为知识'),('KN6','外部预警与预案规则知识'),
 ('KN7','通讯与信息上报知识')]
kn_df=pd.DataFrame(KN,columns=['编码','知识类别'])

with pd.ExcelWriter(PROC/'统一标识.xlsx',engine='openpyxl') as w:
    case_df.to_excel(w,sheet_name='案例事件标识',index=False)
    rec2.to_excel(w,sheet_name='文件2记录标识',index=False)
    rec1.to_excel(w,sheet_name='文件1记录标识',index=False)
    lab_df.to_excel(w,sheet_name='标签归并映射',index=False)
    elem_df.to_excel(w,sheet_name='统一编码-情景要素',index=False)
    ra_df.to_excel(w,sheet_name='统一编码-处置动作',index=False)
    kn_df.to_excel(w,sheet_name='统一编码-知识',index=False)
print('案例/事件:',len(case_df),' 文件2记录:',len(rec2),' 文件1记录:',len(rec1))
print('原始标签数:',len(lab_df),' 一对多:',(lab_df['是否一对多']=='是(取主类)').sum())
print('要素编码:',len(elem_df),' 动作:',len(ra_df),' 知识:',len(kn_df))
# 5) 脱敏扫描：手机号/身份证
pat_phone=re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)'); pat_id=re.compile(r'(?<!\d)\d{17}[\dXx](?!\d)')
hits=0
for name,d in [('文件1',f1),('文件2',f2)]:
    for c in d.columns:
        for v in d[c].dropna().astype(str):
            if pat_phone.search(v) or pat_id.search(v):
                print('发现疑似PII:',name,c,v[:20]); hits+=1
print('PII 命中:',hits,'（0=无需脱敏）')
print('已写 统一标识.xlsx，并回写两份 clean 文件 ID 列')
