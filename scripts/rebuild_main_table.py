# -*- coding: utf-8 -*-
"""
Offline rebuild and verification for the clean three-model main table.

No network access and no API key are required. This script reads
data/clean_main/clean_main_450.csv (25 cids x 6 seeds x 3 models) and:

  1. checks the model set, per-model 150 unique (cid, seed) keys, and that the
     three model key sets match exactly;
  2. checks equal headcount on matched keys, non-negative counts, five-outcome
     closure, and recomputes safe = evacuated + rescued against the stored field;
  3. recomputes population-weighted safe-departure and fatality anchors;
  4. reports run-level mean safe-departure;
  5. recomputes run-level paired differences, win/loss/tie, a fixed-seed
     150-pair paired bootstrap 95% interval, and a cluster-by-cid (25 whole
     scenario groups) 95% interval.

Bootstrap settings are fixed (B=10000, seed=20261022) so intervals are
reproducible offline; the last digit may differ from the manuscript because of
resampling-sequence implementation, while means, integer totals and win/loss/tie
are exact.

Usage:
    python scripts/rebuild_main_table.py
Exit 0 on every check; exit 1 on any structural or anchor mismatch.
"""
import csv, os, sys, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAIN = os.path.join(ROOT, 'data', 'clean_main', 'clean_main_450.csv')

MODELS = ['rule_reference', 'deepseek', 'qwen']
B = 10000
SEED = 20261022

# Integer population-weighted anchors (exact counts) and proportional tolerance.
ANCHORS = {
    'rule_reference': {'N': 22680, 'safe': 20607, 'deceased': 2073, 'safe_rate': 0.9086},
    'deepseek':       {'N': 22680, 'safe': 22671, 'deceased': 9,    'safe_rate': 0.9996},
    'qwen':           {'N': 22680, 'safe': 22129, 'deceased': 551, 'safe_rate': 0.9757},
}
# Exact run-level paired (a-b) mean and win/loss/tie anchors.
PAIR_ANCHORS = {
    ('deepseek', 'rule_reference'): {'mean': 0.066500, 'w': 31, 'l': 0,  't': 119},
    ('qwen', 'rule_reference'):      {'mean': 0.048881, 'w': 30, 'l': 8,  't': 112},
    ('deepseek', 'qwen'):            {'mean': 0.017619, 'w': 27, 'l': 0,  't': 123},
}

def ci95(vals):
    s = sorted(vals); n = len(s)
    return s[int(n*2.5/100)], s[int(n*97.5/100)]

def main():
    ok = True
    with open(MAIN, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} run rows from {os.path.relpath(MAIN, ROOT)}")

    # 1. model set exactly
    got_models = sorted({r['model'] for r in rows})
    if got_models != sorted(MODELS):
        ok = False; print(f"MODEL SET MISMATCH: {got_models} != {sorted(MODELS)}")

    # 2. per-model unique (cid, seed) keys and exact shared key set
    by_model = defaultdict(dict)
    for r in rows:
        by_model[r['model']][(r['cid'], r['seed'])] = r
    key_sets = {}
    for m in MODELS:
        ks = set(by_model[m])
        dup = len(by_model[m]) - len(ks)
        if dup:
            ok = False; print(f"DUPLICATE KEYS in {m}: {dup}")
        if len(ks) != 150:
            ok = False; print(f"RUN COUNT MISMATCH {m}: {len(ks)} != 150")
        key_sets[m] = ks
    shared = key_sets['rule_reference'] & key_sets['deepseek'] & key_sets['qwen']
    if len(shared) != 150:
        ok = False; print(f"SHARED KEY SET MISMATCH: {len(shared)} != 150")
    for m in MODELS:
        only = key_sets[m] - shared
        if only:
            ok = False; print(f"KEYS in {m} not shared: {sorted(only)[:5]}")

    # 3/4. per-key headcount, non-negative, closure, safe recompute
    for k in shared:
        nvals = {}
        for m in MODELS:
            r = by_model[m][k]
            n = int(r['n']); ev = int(r['evacuated']); rs = int(r['rescued'])
            st = int(r['stranded']); dec = int(r['deceased']); ai = int(r['alive_in'])
            nvals[m] = n
            for col, val in [('evacuated',ev),('rescued',rs),('stranded',st),
                             ('deceased',dec),('alive_in',ai),('safe',int(r['safe']))]:
                if val < 0:
                    ok = False; print(f"NEGATIVE {m} {k} {col}={val}")
            if ev + rs + st + dec + ai != n:
                ok = False; print(f"CLOSURE FAIL {m} {k}: sum={ev+rs+st+dec+ai} != n={n}")
            if ev + rs != int(r['safe']):
                ok = False; print(f"SAFE RECOMPUTE FAIL {m} {k}: {ev+rs} != stored {r['safe']}")
        if len(set(nvals.values())) != 1:
            ok = False; print(f"HEADCOUNT MISMATCH on {k}: {nvals}")

    # population-weighted anchors (integer totals first, proportion within 5e-4)
    print("\n-- Population-weighted (pooled) anchors --")
    for m in MODELS:
        sub = list(by_model[m].values())
        N = sum(int(r['n']) for r in sub)
        safe = sum(int(r['safe']) for r in sub)
        dec = sum(int(r['deceased']) for r in sub)
        anc = ANCHORS[m]
        rate = safe / N
        int_ok = (N == anc['N'] and safe == anc['safe'] and dec == anc['deceased'])
        prop_ok = abs(rate - anc['safe_rate']) < 5e-4
        if not int_ok:
            ok = False
            print(f"INTEGER ANCHOR MISMATCH {m}: N={N} safe={safe} death={dec}")
        if not prop_ok:
            ok = False; print(f"RATE ANCHOR MISMATCH {m}: {rate:.6f} vs {anc['safe_rate']}")
        print(f"{m:16s} runs={len(sub):3d} N={N:6d} safe={safe:6d} "
              f"rate={rate:.6f} deceased={dec:4d} [{'OK' if int_ok and prop_ok else 'MISMATCH'}]")

    # run-level means
    print("\n-- Run-level mean safe-departure --")
    for m in MODELS:
        sub = list(by_model[m].values())
        rm = sum(int(r['safe'])/int(r['n']) for r in sub) / len(sub)
        print(f"{m:16s} run-mean={rm:.6f}")

    # paired differences, W/L/T, paired bootstrap, cluster-cid interval
    print(f"\n-- Run-level paired differences (a - b), B={B}, seed={SEED} --")
    pairs = {k: {m: int(by_model[m][k]['safe'])/int(by_model[m][k]['n']) for m in MODELS}
             for k in shared}
    for (a, b), anc in PAIR_ANCHORS.items():
        d = [pairs[k][a]-pairs[k][b] for k in shared]
        mean = sum(d)/len(d)
        w = sum(1 for x in d if x > 1e-9); l = sum(1 for x in d if x < -1e-9)
        t = len(d)-w-l
        if abs(mean - anc['mean']) > 1e-5 or (w, l, t) != (anc['w'], anc['l'], anc['t']):
            ok = False
            print(f"PAIR ANCHOR MISMATCH {a}-{b}: mean={mean:+.6f} W/L/T={w}/{l}/{t}")
        rng = random.Random(SEED)
        boots = [sum(d[rng.randrange(len(d))] for _ in range(len(d)))/len(d) for _ in range(B)]
        blo, bhi = ci95(boots)
        bycid = defaultdict(list)
        for k in shared:
            bycid[k[0]].append(pairs[k][a]-pairs[k][b])
        cids = list(bycid)
        cboot = []
        for _ in range(B):
            g = [cids[rng.randrange(len(cids))] for _ in range(len(cids))]
            allv = [v for c in g for v in bycid[c]]
            cboot.append(sum(allv)/len(allv))
        clo, chi = ci95(cboot)
        print(f"{a}-{b:16s} mean={mean:+.6f} W/L/T={w}/{l}/{t} "
              f"paired-boot95=[{blo:+.4f},{bhi:+.4f}] cluster-cid95=[{clo:+.4f},{chi:+.4f}]")

    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
