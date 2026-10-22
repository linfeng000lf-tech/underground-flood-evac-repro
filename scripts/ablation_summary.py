# -*- coding: utf-8 -*-
"""
Offline #79 knowledge-retrieval ablation summary (no network, no API key).

Reads data/ablation_kb/t79_paired_detail.csv (6 cids x 3 seeds x 2 providers =
36 ON/OFF paired rows, each carrying integer headcount and outcome counts) and:

  1. structurally verifies exactly 18 unique ON/OFF pairs per provider, no
     duplicate (provider, cid, seed), both ends non-mixed (no API-failure
     fallback), integer five-outcome closure, and equal on/off headcount;
  2. reports the run-level mean paired difference (ON - OFF) in safe-departure
     proportion with win/loss/tie;
  3. reports the population-weighted (pooled) ON and OFF safe-departure and the
     pooled ON - OFF difference, recomputed from the published integer counts.

This is a descriptive summary of the executed runs; a near-zero mean is not
evidence of equivalence and does not establish a retrieval mechanism. ON was
executed before OFF in each pair (fixed runner order), so this is a targeted,
exploratory ablation, not a randomized interleaved design.

Usage:
    python scripts/ablation_summary.py
Exit 0 when structural checks pass; exit 1 on any structural or count mismatch.
"""
import csv, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'data', 'ablation_kb', 't79_paired_detail.csv')
PROVIDERS = ['deepseek', 'qwen']

def main():
    ok = True
    rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig', newline='')))
    print(f"Loaded {len(rows)} paired rows from {os.path.relpath(SRC, ROOT)}")
    if len(rows) != 36:
        ok = False; print(f"ROW COUNT MISMATCH: {len(rows)} != 36")

    seen = set()
    by_prov = defaultdict(list)
    for r in rows:
        key = (r['provider'], r['cid'], r['seed'])
        if key in seen:
            ok = False; print(f"DUPLICATE PAIR {key}")
        seen.add(key); by_prov[r['provider']].append(r)

    for prov in PROVIDERS:
        sub = by_prov.get(prov, [])
        if len(sub) != 18:
            ok = False; print(f"PAIR COUNT MISMATCH {prov}: {len(sub)} != 18")
        for r in sub:
            # structural: non-mixed, integer closure, equal headcount, safe recompute
            if r['on_mixed'] != 'False' or r['off_mixed'] != 'False':
                ok = False; print(f"MIXED PAIR {prov} {r['cid']} {r['seed']}")
            n = int(r['n'])
            for pre in ['on', 'off']:
                ev = int(r[f'{pre}_evac_n']); rs = int(r[f'{pre}_rescued_n'])
                st = int(r[f'{pre}_stranded_n']); dec = int(r[f'{pre}_death_n'])
                ai = int(r[f'{pre}_in_n']); safe = int(r[f'{pre}_safe_n'])
                if ev + rs + st + dec + ai != n:
                    ok = False; print(f"CLOSURE FAIL {prov} {r['cid']} {r['seed']} {pre}")
                if ev + rs != safe:
                    ok = False; print(f"SAFE RECOMPUTE FAIL {prov} {r['cid']} {r['seed']} {pre}")
            # run-level mean paired difference + W/L/T
            d = float(r['on_safe']) - float(r['off_safe'])
            r['_d'] = d

    print("\n-- Run-level mean paired (ON - OFF) safe-departure --")
    print("-- Population-weighted (pooled) ON / OFF from integer counts --")
    for prov in PROVIDERS:
        sub = by_prov.get(prov, [])
        diffs = [r['_d'] for r in sub]
        rmean = sum(diffs)/len(diffs)
        w = sum(1 for x in diffs if x > 1e-9); l = sum(1 for x in diffs if x < -1e-9)
        t = len(diffs)-w-l
        onN = sum(int(r['n']) for r in sub); offN = onN
        onS = sum(int(r['on_safe_n']) for r in sub); offS = sum(int(r['off_safe_n']) for r in sub)
        onPool = onS/onN; offPool = offS/offN
        print(f"{prov:9s} pairs={len(sub):2d} runMean(ON-OFF)={rmean:+.6f} W/L/T={w}/{l}/{t}")
        print(f"          pooled ON={onPool:.6f} OFF={offPool:.6f} "
              f"pooled(ON-OFF)={onPool-offPool:+.6f}  (N_on={onN}, N_off={offN})")

    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
