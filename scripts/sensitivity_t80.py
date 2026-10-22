# -*- coding: utf-8 -*-
"""
Offline #80 rule-layer sensitivity aggregation (no network, no API key).

Reads data/sensitivity_t80/t80_all.csv (150 paired runs x BASE/FINE/WALK) and:

  1. verifies 150 complete (cid, seed) keys with all three versions present;
  2. checks integer closure n = evacuated + rescued + stranded + deceased + in
     and safe = evacuated + rescued per run;
  3. compares versions pair-by-pair on (cid, seed) rather than only on pooled
     totals, so opposing per-pair changes cannot cancel:
       FINE - BASE  : check-interval change (safe / deceased / in expected equal);
       WALK - FINE  : transfer-mode change (deceased expected equal; safe and in
                      may differ because endpoint on-site agents are counted in);
  4. checks pooled safe / deceased / in anchors.

Chained comparison: FINE-BASE varies the check interval; WALK-FINE varies the
transfer mode; WALK-BASE changes both and is a combined control, not a single
-variable ablation.

Usage:
    python scripts/sensitivity_t80.py
Exit 0 on every check; exit 1 on any structural or anchor mismatch.
"""
import csv, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'data', 'sensitivity_t80', 't80_all.csv')
VERSIONS = ['BASE', 'FINE', 'WALK']

ANCHORS = {
    'BASE': {'safe': 20607, 'deceased': 2073, 'in': 0},
    'FINE': {'safe': 20607, 'deceased': 2073, 'in': 0},
    'WALK': {'safe': 20119, 'deceased': 2073, 'in': 488},
}

def main():
    ok = True
    rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig', newline='')))
    print(f"Loaded {len(rows)} rows from {os.path.relpath(SRC, ROOT)}")
    M = defaultdict(dict)
    for r in rows:
        M[(r['cid'], r['seed'])][r['version']] = r
    if len(M) != 150:
        ok = False; print(f"KEY COUNT MISMATCH: {len(M)} != 150")
    for k, d in M.items():
        for v in VERSIONS:
            if v not in d:
                ok = False; print(f"MISSING {v} on {k}")
                continue
            r = d[v]
            n = int(r['n']); ev = int(r['evacuated']); rs = int(r['rescued'])
            st = int(r['stranded']); dec = int(r['deceased']); ai = int(r['in'])
            safe = int(r['safe'])
            if ev + rs + st + dec + ai != n:
                ok = False; print(f"CLOSURE FAIL {v} {k}: {ev+rs+st+dec+ai} != {n}")
            if ev + rs != safe:
                ok = False; print(f"SAFE RECOMPUTE FAIL {v} {k}: {ev+rs} != {safe}")

    # pair-by-pair comparison
    fb_safe = fb_death = fb_in = 0
    wf_safe = wf_death = wf_in = 0
    for k, d in M.items():
        if not all(v in d for v in VERSIONS):
            continue
        b, f, w = d['BASE'], d['FINE'], d['WALK']
        for col, fb in [('safe', 'safe'), ('deceased', 'death'), ('in', 'in')]:
            if int(f[col]) != int(b[col]):
                if col == 'safe': fb_safe += 1
                elif col == 'deceased': fb_death += 1
                else: fb_in += 1
        if int(w['deceased']) != int(f['deceased']):
            wf_death += 1
        if int(w['safe']) != int(f['safe']):
            wf_safe += 1
        if int(w['in']) != int(f['in']):
            wf_in += 1
    if fb_safe or fb_death or fb_in:
        ok = False
        print(f"FINE-BASE pair differences (expected 0): safe={fb_safe} death={fb_death} in={fb_in}")
    if wf_death:
        ok = False; print(f"WALK-FINE pairs with different death count: {wf_death}")

    print("\n-- Pooled anchors --")
    for v in VERSIONS:
        sub = [r for r in rows if r['version'] == v]
        N = sum(int(r['n']) for r in sub)
        safe = sum(int(r['safe']) for r in sub)
        dec = sum(int(r['deceased']) for r in sub)
        ins = sum(int(r['in']) for r in sub)
        anc = ANCHORS[v]
        match = safe == anc['safe'] and dec == anc['deceased'] and ins == anc['in']
        if not match:
            ok = False
        print(f"{v:5s} runs={len(sub):3d} N={N:6d} safe={safe:6d} "
              f"safe-departure={safe/N:.4f} deceased={dec:4d} in={ins:4d} [{'OK' if match else 'MISMATCH'}]")

    print(f"\nPair-by-pair: FINE-BASE safe/death/in differ = {fb_safe}/{fb_death}/{fb_in}; "
          f"WALK-FINE safe/death/in differ = {wf_safe}/{wf_death}/{wf_in}")
    print('RESULT:', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
