# -*- coding: utf-8 -*-
"""第4章 步骤4：疏散知识库（显性/隐性）+ 标签检索，约束智能体决策、抑制幻觉。"""
import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; KN=ROOT/'data'/'knowledge'; PROC=ROOT/'data'/'processed'

# (id,type,tags,text,source)
ITEMS=[
 ('K01','explicit',['水深','撤离'],'出入口倒灌、积水持续上涨并威胁用电与疏散安全时，应及时组织乘客撤离。','城市轨道交通运营防汛防台风指南'),
 ('K02','explicit',['出口','关站'],'有效疏散出口不足2个时，应关闭车站、暂停服务。','城市轨道交通运营防汛防台风指南'),
 ('K03','explicit',['水深','封口'],'站外积水达两级台阶或0.30m时，应在该出入口设防洪挡板并关闭。','地铁站外积水30cm关闭站口'),
 ('K04','explicit',['限速','轨行区'],'轨行区积水漫过扣件时，区段限速25km/h。','合肥轨交极端天气应对方案'),
 ('K05','explicit',['停运','轨行区'],'积水漫过轨面时，禁止列车通过、区段停运。','合肥轨交极端天气应对方案'),
 ('K06','explicit',['疏散时间','规范'],'站台人员应在4min内撤离、全部到达安全区不超过6min。','地铁安全疏散规范 GB/T33668-2017'),
 ('K07','explicit',['涉水','速度'],'平地涉水速度约 v=v0(1-h/0.70)，楼梯约 v=v0(1-h/0.30)。','地铁车站水侵应急疏散仿真研究(深大学报)'),
 ('K08','explicit',['失稳','水深'],'成人约1.37m、儿童约1.0m水深可致漂浮失稳。','Flood simulation and risk in underground spaces'),
 ('K09','explicit',['流速','失稳'],'流速0.6m/s勉强平衡、1.0m/s可能被冲走、1.5m/s几乎无法站立。','Flood simulation and risk in underground spaces'),
 ('K10','explicit',['不得','涉水'],'不得盲目趟水，应使用安全出口、听从工作人员引导。','城市轨道交通运营防汛防台风指南'),
 ('K11','explicit',['设防','高差'],'地铁出入口地面标高宜高出室外地面300–450mm，否则设防淹闸槽。','地铁设计规范 GB50157-2013'),
 ('K12','explicit',['分级','内涝'],'内涝积水分级：<.15m蓝、.15–.3黄、.3–.4橙、>.4红。','内涝风险评估标准(征求意见稿)'),
 ('K13','implicit',['从众','社会影响'],'信息不明时，个体会参考周围人群行动，出现从众与观望。','隐性知识(案例归纳)'),
 ('K14','implicit',['熟悉度','出口'],'熟悉环境者偏好常用出口，陌生者更依赖标识与工作人员引导。','隐性知识(案例归纳)'),
 ('K15','implicit',['折返','损失厌恶'],'个体会因取物、找人折返，损失厌恶会增强折返倾向。','隐性知识(案例归纳)'),
 ('K16','implicit',['观望','锚定'],'人们倾向低估涨水速度、锚定既往经验，从而延迟撤离。','隐性知识(案例归纳)'),
 ('K17','implicit',['恐慌','瓶颈'],'拥挤与时间压力下，瓶颈处易出现推挤与拥堵。','隐性知识(案例归纳)'),
 ('K18','implicit',['互助','社会影响'],'紧急时人们会协助同伴、老人儿童，但也可能盲目施救扩大伤亡。','隐性知识(案例归纳)'),
 ('K19','implicit',['信息','播报'],'及时、明确的广播能显著降低观望、促进有序撤离。','隐性知识(案例归纳)'),
 ('K20','implicit',['风险感知','经验'],'有灾验者风险感知更高、更早撤离；无经验者易过度自信。','隐性知识(案例归纳)'),
]

class KnowledgeBase:
    def __init__(self,items=ITEMS):
        self.items=[{'id':i,'type':t,'tags':set(tg),'text':x,'source':s}
                    for i,t,tg,x,s in items]
    def retrieve(self,context,k=3):
        ctx=set(context)
        def score(it): return (len(it['tags']&ctx), 1 if it['type']=='explicit' else 0)
        ranked=sorted(self.items,key=lambda it:score(it),reverse=True)
        out=[it for it in ranked if it['tags']&ctx]
        return (out or ranked)[:k]
    def as_text(self,context,k=3):
        return '\n'.join(f"[{it['id']}|{'显性' if it['type']=='explicit' else '隐性'}] {it['text']}"
                         for it in self.retrieve(context,k))

def build():
    kb=KnowledgeBase()
    KN.mkdir(exist_ok=True)
    ser=[{**{k:v for k,v in it.items() if k!='tags'},'tags':sorted(it['tags'])} for it in kb.items]
    (KN/'知识库.json').write_text(json.dumps(ser,ensure_ascii=False,indent=2),encoding='utf-8')
    df=pd.DataFrame([{'id':i,'类型':'显性' if t=='explicit' else '隐性','标签':'/'.join(tg),
                      '内容':x,'来源':s} for i,t,tg,x,s in ITEMS])
    df.to_excel(PROC/'知识库.xlsx',index=False)
    print('条目数:',len(ITEMS),' 显性:',sum(x[1]=='explicit' for x in ITEMS),
          ' 隐性:',sum(x[1]=='implicit' for x in ITEMS))
    print('已写 知识库.json / 知识库.xlsx')

if __name__=='__main__':
    build()
    kb=KnowledgeBase()
    for ctx in [['水深','撤离'],['从众','社会影响','瓶颈'],['熟悉度','播报']]:
        print('\n情境标签:',ctx)
        print(kb.as_text(ctx,k=3))
