# -*- coding: utf-8 -*-
"""Major Revision - 敏感性补测（离线，无API费用）。
A 涉水阈值±0.10 在【中等 EXP-001】（水深在阈值附近，阈值可能约束）
B B支路入流系数全扫 0→.9 在【EXP-095】，定位零死亡拐点
C 熟悉度占比 在【温和 EXP-018 + 无播报】（寻路差异显现）
D 救援参数网格【F2全淹】：运力±50% ×（正常 / 延迟+短窗口）；并测救援可达边界 rescue_stair/rescue_flat
"""
import json, importlib, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; RUNS = ROOT/'results'/'runs'
sys.path.insert(0, str(ROOT/'code'))
EvacModel = importlib.import_module('26_mesa_engine').EvacModel
space = importlib.import_module('22_space_env')
configs = {c['cid']: c['cfg'] for c in json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))}
SEEDS = (20241001, 20241002, 20241003)
F2 = {'gate_B': .9, 'corr_B': .8, 'stair_B': .9}

def once(cid, seed, coef=None, **over):
    g = dict(configs[cid]); g.update(over)
    m = EvacModel(seed=seed, use_llm=False, tag='SEN2', **g)
    if coef: m.env._coef.update(coef)
    s = m.run(900)
    et = s['evac_times']; med = float(np.median(et)) if et else np.nan
    return {'自救率': round(s['evacuated']/m.n, 3), '救援率': round(s['rescued']/m.n, 3),
            '受困率': round(s['stranded']/m.n, 3), '死亡率': round(s['deceased']/m.n, 3),
            '死亡人数': s['deceased'], '撤离中位时间_min': round(med, 2)}

def sweep(fname, cid, cases, coef=None, groupcol='条件'):
    rows = []
    for label, over in cases:
        for seed in SEEDS:
            r = {groupcol: label, 'seed': seed}; r.update(once(cid, seed, coef=coef, **over)); rows.append(r)
    df = pd.DataFrame(rows); df.to_csv(RUNS/f'{fname}.csv', index=False, encoding='utf-8-sig')
    agg = df.groupby(groupcol)[['自救率','救援率','受困率','死亡率','死亡人数','撤离中位时间_min']].mean().round(3)
    print('\n====', fname, '===='); print(agg.to_string()); return agg

def limits(g, f, st):
    space.GATE_CLOSE = g; space.FLAT_LIMIT = f; space.STAIR_LIMIT = st

def main():
    # A 涉水阈值 on moderate EXP-001
    rows = []
    for label, (g, f, st) in {'偏严-0.10': (.2, .6, .2), '基线': (.3, .7, .3), '偏宽+0.10': (.4, .8, .4)}.items():
        limits(g, f, st)
        for seed in SEEDS:
            r = {'条件': label, 'seed': seed}; r.update(once('EXP-001', seed)); rows.append(r)
    limits(.3, .7, .3)
    dfa = pd.DataFrame(rows); dfa.to_csv(RUNS/'敏感性_涉水阈值_中等.csv', index=False, encoding='utf-8-sig')
    print('\n==== 涉水阈值(中等 EXP-001) ====')
    print(dfa.groupby('条件')[['自救率','救援率','受困率','死亡率']].mean().round(3).to_string())

    # B B coef full sweep on EXP-095
    sweep('敏感性_B支路全扫', 'EXP-095',
          [(f'{v}', {'alarm_min': configs['EXP-095'].get('alarm_min', 'UNSET')}) for v in
           (0, .1, .2, .3, .4, .5, .7, .9)],
          coef=None)
    # need coef applied per value -> custom
    rows = []
    for v in (0, .1, .2, .3, .4, .5, .7, .9):
        coef = {'gate_B': v, 'corr_B': v, 'stair_B': v}
        for seed in SEEDS:
            r = {'B系数': v, 'seed': seed}; r.update(once('EXP-095', seed, coef=coef)); rows.append(r)
    dfb = pd.DataFrame(rows); dfb.to_csv(RUNS/'敏感性_B支路全扫.csv', index=False, encoding='utf-8-sig')
    print('\n==== B支路系数全扫(EXP-095) ====')
    print(dfb.groupby('B系数')[['自救率','救援率','受困率','死亡率','死亡人数']].mean().round(3).to_string())

    # C familiarity on mild EXP-018 with no broadcast
    sweep('敏感性_熟悉度_温和', 'EXP-018',
          [(f'{int(f*100)}%', {'fam_frac': f, 'alarm_min': None}) for f in (0, .25, .5, .75, 1.0)])

    # D rescue capacity grid on F2
    # D1 normal timing/window
    sweep('救援运力_正常窗口', 'EXP-095',
          [('1.5/min', {'rescue_rate': 1.5}), ('3.0/min', {'rescue_rate': 3.0}),
           ('4.5/min', {'rescue_rate': 4.5})], coef=F2)
    # D2 delayed start (90) + short effective window (30)
    sweep('救援运力_延迟短窗', 'EXP-095',
          [('1.5/min', {'rescue_rate': 1.5, 'rescue_min': 90, 'rescue_window': 30}),
           ('3.0/min', {'rescue_rate': 3.0, 'rescue_min': 90, 'rescue_window': 30}),
           ('4.5/min', {'rescue_rate': 4.5, 'rescue_min': 90, 'rescue_window': 30})], coef=F2)
    # D3 reachable-boundary params (these likely bind)
    sweep('救援可达边界', 'EXP-095',
          [('stair .7', {'rescue_stair': .7}), ('stair .9 (base)', {'rescue_stair': .9}),
           ('stair 1.1', {'rescue_stair': 1.1}),
           ('flat 1.6', {'rescue_flat': 1.6}), ('flat 2.0 (base)', {'rescue_flat': 2.0}),
           ('flat 2.4', {'rescue_flat': 2.4})], coef=F2)

if __name__ == '__main__':
    main()
