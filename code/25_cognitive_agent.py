# -*- coding: utf-8 -*-
"""第4章 步骤3/5：认知驱动的疏散智能体。
认知架构 感知—评估—应对—行动：LLM 负责评估与决策，规则层负责可达性裁决与运动。
use_llm=False 时用启发式（PMT/有限理性）决策，作为离线基线与保底路线。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROMPT=(ROOT/'prompts'/'03_智能体决策_system.txt').read_text(encoding='utf-8')

def edge_cap(env,a,b):
    """边并发容量≈长度×有效宽度×密度；宽度由最窄端类型决定，瓶颈由几何自然产生。"""
    ta=env.G.nodes[a]['type']; tb=env.G.nodes[b]['type']
    L=env.G.edges[a,b]['dist']
    if 'stair' in (ta,tb): w=2.0
    elif 'gate' in (ta,tb): w=2.0
    else: w=3.0
    return max(2,round(L*w*1.0))

def heuristic_action(agent, obs, broadcast, crowd_targets=()):
    """规则化基线（PMT/有限理性）。
    官方广播→绝大多数人服从并承诺撤离；无广播→存在乐观偏倚与风险正常化，
    自我撤离阈值更高（低估缓慢涨水），阈值随风险偏好/经验/熟悉度/从众异质。"""
    d=obs['depth']; p=agent.profile; moving=len(crowd_targets)>0
    if broadcast:
        rng=getattr(agent,'model',None)
        ignore=.03+(.12 if p['风险偏好']=='寻求' else 0)
        if rng is None or rng.rng.random()>ignore:
            return 'follow_guidance'
    trig=.45
    if p['风险偏好']=='厌恶': trig-=.08
    if p['水灾经验']=='有': trig-=.10
    if p['熟悉度']=='高': trig-=.05
    if p['风险偏好']=='寻求': trig+=.12
    if p['熟悉度']=='低': trig+=.08
    if moving: trig-=.06
    trig=min(max(trig,.22),.70)
    if d>=trig:
        if d>=.8: return 'immediate_evacuate'
        return 'nearest_exit' if p['熟悉度']!='低' else 'follow_crowd'
    if d>=.15 and moving: return 'follow_crowd'
    return 'wait_and_see'

class CognitiveAgent:
    def __init__(self,aid,profile,start='platform'):
        self.id=aid; self.profile=profile; self.start=start
        self.loc=('node',start); self.status='in'
        self.prev=None; self.edge=None  # ('a','b',remaining,total)
        self.actions=[]; self.last_dec_step=-99
        self.evac_time=None; self.exposure_s=0.0; self.peak_depth=0.0
        self.cur_action=None; self.target=None; self.committed=False
        self.lethal_s=0.0; self.lethal_onset=None; self.rescue_time=None
    @property
    def node(self):
        return self.loc[1] if self.loc[0]=='node' else None
    def lethal_depth(self):
        return 1.0 if self.profile['年龄']=='儿童' else 1.37
    # ---------- 感知 ----------
    def context_tags(self,obs,broadcast,crowd_density):
        tg=set(); d=obs['depth']
        if d>=.10: tg.add('水深')
        if d>=.25: tg.update(['撤离','封口'])
        if broadcast: tg.update(['播报','信息'])
        if crowd_density>=1.2: tg.update(['从众','瓶颈','社会影响'])
        if self.profile['熟悉度']=='低': tg.add('熟悉度')
        if self.profile['水灾经验']=='有': tg.add('风险感知')
        return tg
    def perceive(self,env,broadcast,crowd_density):
        n=self.node or (self.edge[0] if self.edge else self.start)
        obs=env.observe(n if n in env.G else self.start)
        return obs
    # ---------- 决策（LLM 或启发式）----------
    def decide(self,env,kb,sim_step,broadcast,crowd_density,crowd_targets,
               use_llm=False,temperature=.7,decision_interval=3):
        if kb is None and hasattr(self,'model'): kb=self.model.kb
        obs=self.perceive(env,broadcast,crowd_density)
        tags=self.context_tags(obs,broadcast,crowd_density)
        if use_llm:
            from llm_utils import llm_json
            from schemas import AgentDecision
            user=json.dumps({'个人画像':self.profile,'当前感知':obs,
                '相关知识':[it['text'] for it in kb.retrieve(tags,k=3)],
                '广播状态':broadcast,'周围人群动作':crowd_targets},ensure_ascii=False)
            o=llm_json(user,system=PROMPT,schema=AgentDecision,temperature=temperature,
                       tag='08_agent_decision',seed=1000+self.id)
            action=o['action'] if isinstance(o,dict) else o.action
            target=(o.get('target') if isinstance(o,dict) else o.target)
        else:
            action=heuristic_action(self,obs,broadcast,crowd_targets); target=None
        self.cur_action=action; self.target=target
        if action in ('immediate_evacuate','nearest_exit','follow_guidance'):
            self.committed=True
        self.actions.append((sim_step,action)); self.last_dec_step=sim_step
        return action
    # ---------- 规则层：动作→可达移动目标 ----------
    def adjudicate(self,env,broadcast,crowd_targets):
        a=self.cur_action; n=self.node
        if a in ('immediate_evacuate','nearest_exit','follow_guidance'):
            path=env.path_to_exit(n)
            return path[1] if path and len(path)>1 else None
        if a=='follow_crowd':
            cand=[t for t in crowd_targets if t in env.G.neighbors(n)
                  and env.G.nodes[t]['passable']]
            if cand: return max(set(cand),key=cand.count)
            path=env.path_to_exit(n); return path[1] if path and len(path)>1 else None
        if a=='turn_back':
            if self.prev and env.G.nodes[self.prev]['passable'] \
               and self.prev in env.G.neighbors(n): return self.prev
            return None
        return None  # wait_and_see / shelter_stay / help_others 原地
    # ---------- 运动 / 状态推进 ----------
    def update(self,env,sim_step,dt_s,broadcast,crowd_density,crowd_targets,
               edge_occupancy,use_llm=False,decision_interval=3,decision_interval_calm=12):
        # 暴露与峰值水深记录（撤离者除外）
        ref=self.node or (self.edge[0] if self.edge else self.start)
        d=env.G.nodes[ref]['depth'] if ref in env.G else 0
        if self.status!='evacuated' and d>0:
            self.exposure_s+=dt_s; self.peak_depth=max(self.peak_depth,d)
        if self.status=='evacuated': return
        if self.status=='stranded':
            # 受困者原地等待救援；持续处于超过致死阈值的深水中则累积致死暴露
            if d>self.lethal_depth():
                self.lethal_s+=dt_s
                if self.lethal_onset is None: self.lethal_onset=env.t
            return
        if self.loc[0]=='edge':
            self._move_edge(env,dt_s); return
        n=self.node
        # 当前节点已不可通行：强制撤离，否则受困
        if not env.G.nodes[n]['passable']:
            path=env.path_to_exit(n)
            if not path or len(path)<2:
                self.status='stranded'; return
            self._enter_edge(env,path[1],edge_occupancy); return
        # 已向更高处逃来（上一节点明显更深）→ 进入撤离承诺，坚持到出口
        if self.prev and self.prev in env.G and not self.committed:
            if env.G.nodes[self.prev]['depth'] > env.G.nodes[n]['depth']+.10:
                self.committed=True
        # 困在不断缩小的干岛：无可达出口且水深危险/无开放出口
        path=env.path_to_exit(n)
        if (not path or len(path)<2) and (
                env.G.nodes[n]['depth']>=.30 or not env.open_exits()):
            self.status='stranded'; return
        # 撤离承诺：有路径就持续向外，无路则受困
        if self.committed:
            if path and len(path)>1:
                self._enter_edge(env,path[1],edge_occupancy); return
            self.status='stranded'; return
        # 自适应决策间隔：脚下有水或有广播时频繁评估，平静时稀疏（降低调用，符合注意分配）
        eff_interval=decision_interval if (d>=.10 or broadcast) else decision_interval_calm
        need_decide=(self.last_dec_step<0) or (sim_step-self.last_dec_step>=eff_interval)
        if need_decide:
            self.decide(env,None,sim_step,broadcast,crowd_density,crowd_targets,
                        use_llm=use_llm,decision_interval=decision_interval)
        tgt=self.adjudicate(env,broadcast,crowd_targets)
        if tgt: self._enter_edge(env,tgt,edge_occupancy)
    def _enter_edge(self,env,tgt,occ):
        n=self.node; key=tuple(sorted((n,tgt)))
        cap=edge_cap(env,n,tgt)
        ew=getattr(getattr(self,'model',None),'exit_width',None)
        if ew is not None and ('stair' in (env.G.nodes[n]['type'],env.G.nodes[tgt]['type'])
                               or 'gate' in (env.G.nodes[n]['type'],env.G.nodes[tgt]['type'])):
            cap=max(1,round(cap*ew/2.0))  # 窄门同时压缩断面并发容量
        if occ.get(key,0)>=cap: return  # 瓶颈排队，下一时段再试
        if hasattr(self,'model') and not self.model.can_enter_edge(n,tgt): return  # 比流量限流
        dist=env.G.edges[n,tgt]['dist']
        self.loc=('edge',None); self.edge=(n,tgt,dist,dist); occ[key]=occ.get(key,0)+1
    def _move_edge(self,env,dt_s):
        a,b,rem,tot=self.edge
        b_exit=env.G.nodes[b]['is_exit']
        b_ok=env.G.nodes[b]['passable'] or (b_exit and env.G.nodes[b]['exit_open'])
        if not b_ok:
            # 目的地已不可达：退回 a（允许从受困节点向可通行节点逃生，不在此拦截）
            if env.G.nodes[a]['passable']:
                self.loc=('node',a); self.edge=None
            else:
                self.status='stranded'
            return
        v=min(env.speed(a),env.speed(b))
        rem-=v*dt_s
        if rem<=0:
            self.loc=('node',b); self.edge=None; self.prev=a
            if b_exit and env.G.nodes[b]['exit_open']:
                self.status='evacuated'; self.evac_time=env.t
        else:
            self.edge=(a,b,rem,tot)
