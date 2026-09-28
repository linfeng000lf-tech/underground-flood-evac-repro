# -*- coding: utf-8 -*-
"""将空间几何模板注入情景库 JSON（每个情景成为完整可计算初始条件）。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PROC=ROOT/'data'/'processed'; KN=ROOT/'data'/'knowledge'
scn=json.loads((PROC/'情景库.json').read_text(encoding='utf-8'))
geom={g['空间编码']:g for g in json.loads((KN/'空间与运动参数.json').read_text(encoding='utf-8'))['space_geometry']}
for s in scn:
    g=geom[s['space']]
    s['geometry']={'area_m2':g['典型面积_m2'],'n_exits':g['有效出口数'],
        'exit_width_m':g['单出口有效宽度_m'],'path_mean_m':g['平均内部路径_m'],
        'path_max_m':g['最长路径_m'],'exit_specific_flow_p_m_min':g['出口单宽通行能力_人每mmin'],
        'evac_way':g['疏散方式']}
(PROC/'情景库.json').write_text(json.dumps(scn,ensure_ascii=False,indent=2),encoding='utf-8')
print('已为',len(scn),'个情景注入 geometry')
print('示例字段:',list(scn[0].keys()))
