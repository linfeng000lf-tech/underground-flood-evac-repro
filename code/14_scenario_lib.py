# -*- coding: utf-8 -*-
"""任务9：情景链/情景树推演，生成参数化情景库（xlsx + 供仿真 JSON）。"""
import json, argparse
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; PROC=ROOT/'data'/'processed'
tpl=pd.read_excel(PROC/'水深参数化模板.xlsx',dtype=object)
TPL={r['code']:r for _,r in tpl.iterrows()}
def fnum(x): return float(x)

# 分支变量取值
DEF={'D_OK':'设防达标','D_WK':'设防薄弱','D_FL':'设防失效'}
DR ={'PMP_OK':'排水充足','PMP_WK':'排水一般','PMP_FL':'排水失效'}
POP={'SM':'小规模','MD':'中等规模','LG':'大规模'}
FAM={'FAM_HI':'熟悉度高','FAM_MD':'熟悉度中','FAM_LO':'熟悉度低'}
RESP={'R_OK':'响应及时','R_DL':'响应滞后','R_NO':'未有效响应'}
# 各空间类型的人群规模参考人数（低/中/高）
NCOUNT={'S1':(50,300,1200),'S2':(20,250,500),'S3':(8,40,180),'S4':(40,400,2000),
 'S5':(3,8,15),'S6':(10,40,120),'S7':(1,3,6),'S8':(10,40,150),'S9':(5,20,80)}
# 种子：模板,锚定真实案例,事件类型,空间类型
SEED={'A1':('北京地铁金安桥站“7·18”暴雨进水事件','T1','S1'),
 'A2':('郑州地铁5号线“7·20”淹溺事件','T1','S2'),
 'A3':('湖南龙山龙领国际小区地下车库洪水倒灌致人死亡事件','T2','S3'),
 'A4':('2007年济南银座地下购物广场水灾','T2','S4'),
 'A5':('深圳“4·11”短时极端强降水导致暗渠清淤作业人员淹溺事件','T1','S5'),
 'A6':('广东省佛山市轨道交通2号线一期工程“2·7”透水坍塌重大事故','T5','S2'),
 'A7':('天心新昌路建设项目“7·20”一般淹溺事故','T7','S7'),
 'A8':('杭州地铁1号线金沙湖站“5·18”管涌进水事件','T2','S1'),
 'A9':('福州地铁因台风“海葵”导致车站周边多处积水全线网车站暂停运营事件','T3','S1'),
 'A10':('上海地铁天潼路站消防水管爆裂漏水事件','T8','S1')}
# 变体配置：模板 -> [(变体名,DEF,DR,POP,FAM,RESP), ...]；第一项为基准
VAR={
 'A1':[('基准','D_WK','PMP_WK','MD','FAM_LO','R_DL'),('设防达标及时停运','D_OK','PMP_OK','MD','FAM_LO','R_OK'),
       ('排水失效车站被淹','D_FL','PMP_FL','LG','FAM_LO','R_DL')],
 'A2':[('基准','D_FL','PMP_FL','LG','FAM_LO','R_NO'),('预警前置区间停运','D_OK','PMP_OK','MD','FAM_LO','R_OK'),
       ('挡水薄弱列车迫停','D_WK','PMP_WK','LG','FAM_LO','R_DL')],
 'A3':[('基准','D_WK','PMP_WK','MD','FAM_HI','R_DL'),('响应及时封库','D_OK','PMP_OK','SM','FAM_HI','R_OK'),
       ('通知失效业主困库','D_FL','PMP_FL','MD','FAM_HI','R_NO')],
 'A4':[('基准','D_WK','PMP_WK','LG','FAM_MD','R_OK'),('客流高峰响应滞后','D_FL','PMP_FL','LG','FAM_LO','R_DL'),
       ('预案完备快速疏散','D_OK','PMP_OK','LG','FAM_MD','R_OK')],
 'A5':[('基准','D_FL','PMP_FL','SM','FAM_HI','R_NO'),('作业预警及时撤离','D_WK','PMP_WK','SM','FAM_HI','R_OK')],
 'A6':[('基准','D_WK','PMP_WK','MD','FAM_HI','R_DL'),('监测预警及时撤场','D_OK','PMP_OK','MD','FAM_HI','R_OK'),
       ('突水突发撤离不及','D_FL','PMP_FL','MD','FAM_HI','R_NO')],
 'A7':[('基准','D_WK','PMP_WK','SM','FAM_HI','R_DL'),('盲目施救伤亡扩大','D_FL','PMP_FL','SM','FAM_HI','R_NO'),
       ('作业规范监护到位','D_OK','PMP_OK','SM','FAM_HI','R_OK')],
 'A8':[('基准','D_WK','PMP_WK','MD','FAM_LO','R_OK'),('管涌发展响应滞后','D_FL','PMP_FL','LG','FAM_LO','R_DL')],
 'A9':[('基准','D_WK','PMP_WK','LG','FAM_LO','R_OK'),('潮位顶托排水失效','D_FL','PMP_FL','LG','FAM_LO','R_DL'),
       ('预警前置网停运','D_OK','PMP_OK','MD','FAM_LO','R_OK')],
 'A10':[('基准','D_OK','PMP_OK','MD','FAM_LO','R_OK'),('夜间爆裂发现滞后','D_WK','PMP_WK','SM','FAM_LO','R_DL')],
}
# 发生可能性带（按原型在68案例中的常见度）
PROBB={'A1':'高','A2':'中','A3':'中','A4':'中','A5':'低','A6':'中','A7':'中','A8':'低','A9':'中','A10':'低'}

def depth_band(t,defc,drc):
    if defc=='D_FL' or drc=='PMP_FL': col='dp_高'
    elif defc=='D_WK' or drc=='PMP_WK': col='dp_基准'
    else: col='dp_低'
    return fnum(t[col])
def risk_band(dp,resp,pop):
    ds=0 if dp<.15 else 1 if dp<.5 else 2 if dp<1.0 else 3 if dp<1.3 else 4 if dp<1.7 else 5
    rs={'R_OK':-1,'R_DL':0,'R_NO':1}[resp]; tot=ds+rs+(1 if pop=='LG' else 0)
    band='高' if tot>=4 else '中' if tot>=2 else '低'
    succ=np.clip(0.99-dp*0.28+{'R_OK':.12,'R_DL':0,'R_NO':-.28}[resp],.05,.99)
    return band,round(float(succ),2)

rows=[]; sid=0
rng=np.random.default_rng(20240923)
for ac,variants in VAR.items():
    anchor,T,S=SEED[ac]; t=TPL[ac]
    for vname,defc,drc,pc,fm,rp in variants:
        sid+=1
        dp=depth_band(t,defc,drc)
        dp=round(dp*float(rng.uniform(.92,1.08)),2)
        nlo,nm_,nhi=NCOUNT[S]; n={'SM':nlo,'MD':nm_,'LG':nhi}[pc]
        rb,succ=risk_band(dp,rp,pc)
        # 水深时间参数（来自模板）
        d0,ts,tpk,tplp,te=fnum(t.d0),fnum(t.t_seep),fnum(t.t_peak),fnum(t.t_plat),fnum(t.t_end)
        # 响应时机对报警/启动的影响（min，相对进水）
        lag={'R_OK':(max(int(ts)-5,0),int(ts)),'R_DL':(int(tpk),int(tpk)+10),'R_NO':(None,None)}[rp]
        rows.append({'情景编号':f'SCN-{sid:03d}','情景名称':f"{t['原型名称']}-{vname}",
            '情景原型':anchor,'模板':ac,'事件类型':T,'洪水来源':t.get('标定案例') and
            {'A1':'W1','A2':'W1','A3':'W2','A4':'W2','A5':'W1','A6':'W4','A7':'W5','A8':'W2','A9':'W1','A10':'W7'}[ac],
            '空间类型':S,'设防状态':DEF[defc],'排水状态':DR[drc],
            '人群类型':{'S5':'作业人员','S6':'作业人员','S7':'作业人员','S8':'作业人员'}.get(S,
                '乘客' if S in('S1','S2') else '公众'),
            '人群规模':POP[pc],'人群数量_参考':n,'熟悉度':FAM[fm],'响应时机':RESP[rp],
            '报警_min':lag[0],'响应启动_min':lag[1],
            'd0':d0,'t_seep':ts,'t_peak':tpk,'t_plat':tplp,'t_end':te,'峰值水深_m':dp,
            '先验风险带':rb,'疏散成功概率_先验':succ,'发生可能性带':PROBB[ac]})
df=pd.DataFrame(rows)
cols=['情景编号','情景名称','情景原型','模板','事件类型','洪水来源','空间类型','设防状态','排水状态',
 '人群类型','人群规模','人群数量_参考','熟悉度','响应时机','报警_min','响应启动_min',
 'd0','t_seep','t_peak','t_plat','t_end','峰值水深_m','先验风险带','疏散成功概率_先验','发生可能性带']
df=df[cols]
df.to_excel(PROC/'情景库.xlsx',index=False)
sim=[]
for r in rows:
    sim.append({'id':r['情景编号'],'name':r['情景名称'],'archetype':r['情景原型'],
      'event':r['事件类型'],'water_source':r['洪水来源'],'space':r['空间类型'],
      'defense':r['设防状态'],'drain':r['排水状态'],
      'population':{'type':r['人群类型'],'scale':r['人群规模'],'n_ref':r['人群数量_参考'],'familiarity':r['熟悉度']},
      'response':{'timing':r['响应时机'],'alarm_min':r['报警_min'],'start_min':r['响应启动_min']},
      'depth':{'d0':r['d0'],'t_seep':r['t_seep'],'t_peak':r['t_peak'],'t_plat':r['t_plat'],
               't_end':r['t_end'],'d_peak':r['峰值水深_m']},
      'prior':{'risk_band':r['先验风险带'],'evac_success':r['疏散成功概率_先验'],'prob_band':r['发生可能性带']}})
(PROC/'情景库.json').write_text(json.dumps(sim,ensure_ascii=False,indent=2),encoding='utf-8')
print('生成情景数:',len(df))
print('\n按模板:',df['模板'].value_counts().sort_index().to_dict())
print('按空间:',df['空间类型'].value_counts().to_dict())
print('风险带:',df['先验风险带'].value_counts().to_dict())
print('已写 情景库.xlsx / 情景库.json')
