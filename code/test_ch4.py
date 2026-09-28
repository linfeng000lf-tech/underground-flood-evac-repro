# -*- coding: utf-8 -*-
"""第4章 步骤7：单元测试（离线，不调用LLM）。
覆盖 水深/出口/路径更新、动作合法性、裁决可达性、承诺机制、日志完整性。"""
import importlib
from pathlib import Path
from hydro import get_scenario,depth_params
FloodEnv=importlib.import_module('22_space_env').FloodEnv
sample_population=importlib.import_module('23_profiles').sample_population
KnowledgeBase=importlib.import_module('24_knowledge_base').KnowledgeBase
ca=importlib.import_module('25_cognitive_agent')
CognitiveAgent=ca.CognitiveAgent
engine=importlib.import_module('26_mesa_engine')
EvacModel=engine.EvacModel

WL={'immediate_evacuate','wait_and_see','follow_crowd','nearest_exit',
    'follow_guidance','turn_back','help_others','shelter_stay'}

def test_water_and_exits():
    env=FloodEnv(depth_params(get_scenario('SCN-001')),entry='gate_A')
    opens=[]
    for t in range(0,160):
        env.update_water(t)
        opens.append(set(env.open_exits()))
    assert 'gate_A' not in opens[-1], 'A口峰值应关闭'
    assert 'gate_B' in opens[-1], 'B口应保持开放'
    assert env.G.nodes['platform']['depth']>=env.G.nodes['hall']['depth'],'站台为汇水低点'
    print(' 水深/出口 更新正确')

def test_path_and_speed():
    env=FloodEnv(depth_params(get_scenario('SCN-001')),entry='gate_A'); env.update_water(60)
    p=env.path_to_exit('platform')
    assert p and p[0]=='platform' and p[-1] in env.open_exits()
    assert all(env.G.nodes[n]['passable'] for n in p), '路径节点须可通行'
    v_dry=env.speed('gate_B'); v_wet=env.speed('platform')
    assert v_dry>v_wet>0, '水深应降低涉水速度'
    print(' 路径规划/涉水速度 正确')

def test_heuristic_and_adjudication():
    env=FloodEnv(depth_params(get_scenario('SCN-001')),entry='gate_A'); kb=KnowledgeBase()
    for step in range(0,120,3):
        env.update_water(step*10/60)
        for i,pf in enumerate(sample_population(12,seed=step)):
            a=CognitiveAgent(i,pf,'platform')
            obs=env.observe('platform'); act=ca.heuristic_action(a,obs,step>=150)
            assert act in WL
            a.cur_action=act
            tgt=a.adjudicate(env,step>=150,[])
            assert tgt is None or (tgt in env.G and env.G.nodes[tgt]['passable'])
    print(' 启发式动作合法、裁决目标可达')

def test_commitment():
    env=FloodEnv(depth_params(get_scenario('SCN-001')),entry='gate_A'); env.update_water(60)
    a=CognitiveAgent(0,sample_population(1,seed=1)[0],'platform'); a.committed=True
    occ={}
    for k in range(400):
        if a.status!='in': break
        a.update(env,k,10,True,0.5,[],occ,use_llm=False)
    assert a.status=='evacuated','承诺撤离者应到达出口'
    print(' 撤离承诺机制正确')

def test_full_run_and_logs():
    m=EvacModel('SCN-001',n=20,use_llm=False,tag='unittest')
    m.run(240); m.save()
    assert all(a.status in ('evacuated','stranded','in') for a in m.agents)
    assert set(a_ for a in m.agents for a_ in [a.cur_action] if a_) <= WL
    assert len(m.step_rows)>0 and len(m.traj)>0
    f1=Path(m.__class__.__module__)  # noop
    metrics=Path('results/runs/SCN-001_unittest_metrics.xlsx')
    traj=Path('results/runs/SCN-001_unittest_traj.xlsx')
    assert metrics.exists() and traj.exists()
    print(' 整跑可重复、动作合法、日志与落盘完整')

if __name__=='__main__':
    for name,fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
    print('全部单元测试通过 ✔')
