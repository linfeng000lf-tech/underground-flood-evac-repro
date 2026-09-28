# -*- coding: utf-8 -*-
"""Major Revision - 新增离线敏感性与L1中间(单调)条件实验（不调用真实LLM，无API费用）。
输出 results/runs/：
  敏感性_涉水阈值.csv      规则层可达阈值 ±0.10 m
  敏感性_救援容量.csv      救援运力 ±50%（F2全淹背景，运力为约束）
  敏感性_B支路入流.csv     恒干B支路入流系数 0.05/0.10（零死亡稳健性）
  L1_单调性_播报.csv       分级播报时机（连续，而非全有/全无）
  L1_单调性_熟悉度.csv     高熟悉人群占比 0→1（中间条件）
阈值口径：可达阈值 GATE_CLOSE/FLAT_LIMIT/STAIR_LIMIT（22_space_env 模块常量）。"""
import json, importlib, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; RUNS = ROOT/'results'/'runs'
sys.path.insert(0, str(ROOT/'code'))
engine = importlib.import_module('26_mesa_engine'); EvacModel = engine.EvacModel
space = importlib.import_module('22_space_env')

configs = {c['cid']: c['cfg'] for c in json.loads((RUNS/'批量配置.json').read_text(encoding='utf-8'))}
SEEDS = (20241001, 20241002, 20241003)
F2COEF = {'gate_B': .9, 'corr_B': .8, 'stair_B': .9}

def run_once(cid, seed, coef=None, **over):
    g = dict(configs[cid]); g.update(over)
    m = EvacModel(seed=seed, use_llm=False, tag='SENS', **g)
    if coef: m.env._coef.update(coef)
    s = m.run(900)
    et = s['evac_times']
    med = float(np.median(et)) if et else np.nan
    return {'n': m.n,
            '自救率': round(s['evacuated']/m.n, 3),
            '救援率': round(s['rescued']/m.n, 3),
            '受困率': round(s['stranded']/m.n, 3),
            '死亡率': round(s['deceased']/m.n, 3),
            '死亡人数': s['deceased'],
            '撤离中位时间_min': round(med, 2)}

def set_limits(gate, flat, stair):
    space.GATE_CLOSE = gate; space.FLAT_LIMIT = flat; space.STAIR_LIMIT = stair

def block(name, cid, vary, fixed_coef=None):
    rows = []
    for label, over in vary:
        for seed in SEEDS:
            r = {'条件': label, 'seed': seed}; r.update(run_once(cid, seed, coef=fixed_coef, **over))
            rows.append(r)
    df = pd.DataFrame(rows); df.to_csv(RUNS/f'{name}.csv', index=False, encoding='utf-8-sig')
    agg = df.groupby('条件').agg(
        自救率=('自救率', 'mean'), 救援率=('救援率', 'mean'), 受困率=('受困率', 'mean'),
        死亡率=('死亡率', 'mean'), 死亡人数=('死亡人数', 'mean'),
        撤离中位时间_min=('撤离中位时间_min', 'mean')).round(3)
    print('\n====', name, '===='); print(agg.to_string())
    return agg

def main():
    # 1) 涉水可达阈值 ±0.10（基线 EXP-095，一干一湿+正常救援）
    set_limits(.30, .70, .30)
    lim_rows = []
    for label, (g, f, st) in {
            '偏严(-0.10)': (.20, .60, .20),
            '基线': (.30, .70, .30),
            '偏宽(+0.10)': (.40, .80, .40)}.items():
        set_limits(g, f, st)
        for seed in SEEDS:
            r = {'条件': label, 'seed': seed}; r.update(run_once('EXP-095', seed)); lim_rows.append(r)
    set_limits(.30, .70, .30)
    df = pd.DataFrame(lim_rows); df.to_csv(RUNS/'敏感性_涉水阈值.csv', index=False, encoding='utf-8-sig')
    print('\n==== 敏感性_涉水阈值 ====')
    print(df.groupby('条件')[['自救率', '救援率', '受困率', '死亡率']].mean().round(3).to_string())

    # 2) 救援运力 ±50%（F2 全淹背景，运力为约束）
    block('敏感性_救援容量', 'EXP-095',
          [('减半 1.5/min', {'rescue_rate': 1.5}),
           ('基线 3.0/min', {'rescue_rate': 3.0}),
           ('加倍 4.5/min', {'rescue_rate': 4.5})],
          fixed_coef=F2COEF)

    # 3) B 支路入流系数 0.05/0.10（基线恒干=0；正常救援）
    b_rows = []
    for label, v in {'恒干 0': 0.0, '微渗 0.05': .05, '小源 0.10': .10}.items():
        coef = {'gate_B': v, 'corr_B': v, 'stair_B': v}
        for seed in SEEDS:
            r = {'条件': label, 'seed': seed}; r.update(run_once('EXP-095', seed, coef=coef)); b_rows.append(r)
    dfb = pd.DataFrame(b_rows); dfb.to_csv(RUNS/'敏感性_B支路入流.csv', index=False, encoding='utf-8-sig')
    print('\n==== 敏感性_B支路入流 ====')
    print(dfb.groupby('条件')[['自救率', '救援率', '受困率', '死亡率']].mean().round(3).to_string())

    # 4) L1 单调：分级播报时机（EXP-095）
    block('L1_单调性_播报', 'EXP-095',
          [('0 min', {'alarm_min': 0}), ('5 min', {'alarm_min': 5}),
           ('10 min', {'alarm_min': 10}), ('20 min', {'alarm_min': 20}),
           ('40 min', {'alarm_min': 40}), ('无播报', {'alarm_min': None})])

    # 5) L1 单调：高熟悉人群占比（EXP-095，默认播报）
    block('L1_单调性_熟悉度', 'EXP-095',
          [('0%', {'fam_frac': 0.0}), ('25%', {'fam_frac': .25}),
           ('50%', {'fam_frac': .5}), ('75%', {'fam_frac': .75}),
           ('100%', {'fam_frac': 1.0})])

if __name__ == '__main__':
    main()
