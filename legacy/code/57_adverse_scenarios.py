# -*- coding: utf-8 -*-
"""阶段1B：不利/现实情景族——检验"零死亡"成立的条件边界。
基线取最严重配置(EXP-096/095)，注入多水源系数使原本恒干的B支路也被淹，
叠加救援延迟/受限/无救援。无救援族强制跑满900步再做致死判定(避免提前终止伪影)。
参数证据等级：A=事故调查报告载明机制；B=极端降雨下合理外推（文中如实标注）。单独成族报告。"""
import json, importlib, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'
sys.path.insert(0,str(ROOT/'code'))
e=importlib.import_module('26_mesa_engine'); EvacModel=e.EvacModel
configs={c['cid']:c['cfg'] for c in json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))}

# (名称, B/风亭系数覆盖, 救援模式, 证据等级, 说明)
# rescue: 'normal'=用cfg原救援; dict=覆盖救援参数; 'none'=无救援(跑满全程)
FAMILIES=[
 ('F0_基线(一干一湿+正常救援)', {}, 'normal', 'A', '原始设定：B支路恒干、救援正常'),
 ('F1_B支路半淹(正常救援)', {'gate_B':.5,'corr_B':.45,'stair_B':.5}, 'normal', 'B', '第二水源中等强度'),
 ('F2_B支路全淹(正常救援)', {'gate_B':.9,'corr_B':.8,'stair_B':.9}, 'normal', 'A', '多水源/双向漫溢'),
 ('F3_全淹+风亭(正常救援)', {'gate_B':.9,'corr_B':.8,'stair_B':.9,'wind':.8,'hall':.95}, 'normal', 'B', '多水源含风亭'),
 ('F4_全淹+救援延迟受限', {'gate_B':.9,'corr_B':.8,'stair_B':.9},
    dict(rescue_min=90,rescue_flat=1.0,rescue_stair=.5), 'A', '救援延迟且涉水/楼梯受限'),
 ('F5_全淹+无救援', {'gate_B':.9,'corr_B':.8,'stair_B':.9}, 'none', 'A', '救援不可达(最坏)'),
 ('F6_一干一湿+无救援', {}, 'none', 'A', 'B支路恒干但无救援(检验救援必要性)'),
]
def main():
    rows=[]
    for cid in ('EXP-096','EXP-095'):
        for name,coef,rmode,grade,desc in FAMILIES:
            for seed in (20241001,20241002,20241003):
                cfg=dict(configs[cid]);
                # 用每重复种子重建（execute内seed=0占位，改为传入）
                g2=dict(cfg)
                if rmode=='none': g2['rescue_min']=None
                elif isinstance(rmode,dict): g2.update(rmode)
                m=EvacModel(seed=seed,use_llm=False,tag='ADV',**g2)
                if coef: m.env._coef.update(coef)
                if rmode=='none':
                    for _ in range(900): m.step()
                    m.finalize_no_rescue(); s=m.summary()
                else:
                    s=m.run(900)
                rows.append({'base':cid,'family':name,'证据等级':grade,'说明':desc,'seed':seed,
                    'n':m.n,'自救率':round(s['evacuated']/m.n,3),
                    '救援率':round(s['rescued']/m.n,3),'受困率':round(s['stranded']/m.n,3),
                    '死亡率':round(s['deceased']/m.n,3),'死亡人数':s['deceased']})
    df=pd.DataFrame(rows)
    df.to_csv(RUNS/'第6章_不利情景族.csv',index=False,encoding='utf-8-sig')
    agg=df.groupby(['base','family','证据等级','说明']).agg(
        自救率=('自救率','mean'),救援率=('救援率','mean'),受困率=('受困率','mean'),
        死亡率=('死亡率','mean'),死亡人数=('死亡人数','max')).round(3).reset_index()
    agg.to_excel(RUNS/'第6章_不利情景汇总.xlsx',index=False)
    print(agg.to_string(index=False))

if __name__=='__main__':
    main()
