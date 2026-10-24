"""Rebuild reported process indicators using aggregate records only. No API or engine."""
from pathlib import Path
import csv,json,statistics,collections

ROOT=Path(__file__).resolve().parents[1]
def load(rel):
    with (ROOT/rel).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def indexed(rows,fields):
    out={}
    for r in rows:
        k=tuple(r[f] for f in fields)
        assert k not in out,('duplicate key',k)
        out[k]=r
    return out
def near(actual,target,tol=0.000051):assert abs(actual-target)<=tol,(actual,target)
def main():
    runs=load('data/clean_main/clean_main_450.csv')
    reference=indexed([r for r in runs if r['model']!='rule_reference'],['model','cid','seed'])
    process=indexed(load('data/clean_main/process_runs_300.csv'),['model','cid','seed'])
    assert len(process)==300 and set(process)==set(reference)
    for k,r in process.items():
        assert int(r['n'])==int(reference[k]['n'])==int(r['first_decision_n'])
        assert int(r['autonomous_exit_n'])==int(reference[k]['evacuated'])
        assert 0<=int(r['exits_before_minute5_n'])<=int(r['autonomous_exit_n'])
        assert int(r['first_evacuation_action_n'])==sum(int(r[z]) for z in ['first_nearest_exit_n','first_follow_guidance_n','first_immediate_evacuate_n'])
    hist=load('data/clean_main/exit_time_histogram.csv')
    seen=set();times=collections.defaultdict(list)
    for r in hist:
        key=(r['model'],float(r['exit_time_min']));assert key not in seen
        seen.add(key);n=int(r['count']);assert n>0 and key[1]>=0
        times[key[0]].extend([key[1]]*n)
    print('Main process summaries')
    for m,evac,early,median in [('deepseek',.7181657848324515,.7796303647832032,2.17),('qwen',.23236331569664903,.2818078237751614,9.83)]:
        rr=[r for r in process.values() if r['model']==m]
        n=sum(int(r['n']) for r in rr);exit_n=sum(int(r['autonomous_exit_n']) for r in rr)
        initial=sum(int(r['first_evacuation_action_n']) for r in rr)/n
        before=sum(int(r['exits_before_minute5_n']) for r in rr)/exit_n
        assert len(times[m])==exit_n
        near(initial,evac,1e-12);near(before,early,1e-12);near(statistics.median(times[m]),median,1e-12)
        print(f'{m}: initial evacuation action={100*initial:.1f}%, exits before minute 5={100*before:.1f}%, pooled median exit={statistics.median(times[m]):.2f} min')
    paired=indexed(load('data/ablation_kb/t79_paired_detail.csv'),['provider','cid','seed'])
    ab=indexed(load('data/ablation_kb/process_runs_72.csv'),['provider','cid','seed','condition'])
    assert len(ab)==72
    expected={(*k,c) for k in paired for c in ['on','off']};assert set(ab)==expected
    for k,r in ab.items():
        p=paired[k[:3]];condition=k[3];calls=int(r['successful_decision_events'])
        assert calls==int(p[condition+'_calls']) and calls>0
        for f in ['wait_event_n','llm_target_nonnull_n','rule_target_nonnull_n']:assert 0<=int(r[f])<=calls
        assert int(r['autonomous_exit_n'])==int(p[condition+'_evac_n'])
        near(int(r['wait_event_n'])/calls,float(p[condition+'_wait']),1e-12)
    print('Ablation process summaries, equally weighted runs')
    targets={'deepseek':{'on':(.3234,.3574,.6731,2.7419),'off':(.3984,.4046,.5886,2.7144)},
             'qwen':{'on':(.7689,.1123,.2256,9.7392),'off':(.7822,.1512,.2136,10.4481)}}
    for m in targets:
        for c,target in targets[m].items():
            rr=[r for r in ab.values() if r['provider']==m and r['condition']==c];assert len(rr)==18
            values=tuple(statistics.mean(int(r[f])/int(r['successful_decision_events']) for r in rr) for f in ['wait_event_n','llm_target_nonnull_n','rule_target_nonnull_n'])
            values+=(statistics.mean(float(r['median_autonomous_exit_min']) for r in rr),)
            for actual,wanted in zip(values,target):near(actual,wanted)
            print(m,c,'wait / LLM target / rule target / mean run median:',','.join(f'{v:.4f}' for v in values))
    cov=load('data/ablation_kb/knowledge_selection_coverage.csv');indexed(cov,['provider','item_id'])
    assert len(cov)==46
    selected={r['item_id'] for r in cov if int(r['retrieved_event_n'])>0}
    assert len(selected)==14
    assert all(int(r['retrieved_event_n'])==0 for r in cov if r['item_id'] in ['K08','K09'])
    print('Reconstructed ON retrieval coverage: 14 of 23 items; K08 and K09 not selected')
    audit=load('data/sensitivity_t80/walk_endpoint_audit.csv')
    aa=indexed(audit,['cid','seed']);ss=indexed([r for r in load('data/sensitivity_t80/t80_all.csv') if r['version']=='WALK'],['cid','seed'])
    assert len(aa)==150 and set(aa)==set(ss)
    for k,r in aa.items():
        for f in ['n','safe','in','evacuated','rescued','stranded','deceased']:assert int(r[f])==int(ss[k][f])
        for f in ['extra_active_fatality_triggers','extra_stranded_hold_triggers','individual_finalizer_differences']:assert int(r[f])==0
    print('WALK endpoint audit: 150 matched runs, no extra finalizer-triggered state changes')
    print('RESULT: PASS')

if __name__=='__main__':main()
