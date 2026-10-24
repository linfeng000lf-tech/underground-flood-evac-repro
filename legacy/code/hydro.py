# -*- coding: utf-8 -*-
"""共享水动力模块：水深四阶段 depth(t)、原型模板与情景库加载（第4章起复用）。"""
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PROC=ROOT/'data'/'processed'

def depth_t(t,p):
    """梯形四阶段水深。p=[d0,t_seep,t_peak,t_plat,t_end,d_peak]，t 可为标量或数组（分钟）。"""
    d0,ts,tpk,tpl,te,dp=p
    t=np.asarray(t,float); out=np.zeros_like(t)
    rup=(dp-d0)/max(tpk-ts,1e-9); rdn=dp/max(te-(tpk+tpl),1e-9)
    s1=t<ts; out[s1]=d0*t[s1]/max(ts,1e-9)
    s2=(t>=ts)&(t<tpk); out[s2]=d0+rup*(t[s2]-ts)
    s3=(t>=tpk)&(t<tpk+tpl); out[s3]=dp
    s4=(t>=tpk+tpl)&(t<te); out[s4]=dp-rdn*(t[s4]-(tpk+tpl))
    out[t>=te]=0
    return out

def depth_params(scn):
    """从情景库记录取水深参数列表。"""
    d=scn['depth']
    return [d['d0'],d['t_seep'],d['t_peak'],d['t_plat'],d['t_end'],d['d_peak']]

def load_templates():
    return {r['code']:r for r in json.loads((PROC/'水深参数化模板.json').read_text(encoding='utf-8'))}

def load_scenarios():
    return json.loads((PROC/'情景库.json').read_text(encoding='utf-8'))

def get_scenario(sid):
    return next(s for s in load_scenarios() if s['id']==sid)

if __name__=='__main__':
    scn=get_scenario('SCN-001'); p=depth_params(scn)
    print('SCN-001 水深参数:',p)
    print('t=0/10/30/120 min 水深:',[round(float(depth_t(t,p)),3) for t in (0,10,30,120)])
