# -*- coding: utf-8 -*-
"""第4章 步骤6：Mesa 混合仿真引擎。
每步：更新水深 → 感知 → (间隔)LLM决策 → 规则运动；决策与运动解耦、LLM缓存。
输出 results/runs 宏观指标、个体轨迹（供第6章）；图4-3 引擎时序。"""
import json, argparse, importlib
from pathlib import Path
import numpy as np, pandas as pd, mesa
ROOT=Path(__file__).resolve().parents[1]; RUNS=ROOT/'results'/'runs'; FIG=ROOT/'results'/'figures'
RUNS.mkdir(parents=True,exist_ok=True)
from hydro import get_scenario,depth_params
FloodEnv=importlib.import_module('22_space_env').FloodEnv
sample_population=importlib.import_module('23_profiles').sample_population
KnowledgeBase=importlib.import_module('24_knowledge_base').KnowledgeBase
CognitiveAgent=importlib.import_module('25_cognitive_agent').CognitiveAgent

AREA={'platform':500,'hall':400,'corr_A':80,'corr_B':80,'gate_A':30,'gate_B':30,
 'stair_A':25,'stair_B':25,'wind':20,'interval':300}

def pick_entry(scn):
    return 'interval' if scn['space']=='S2' else 'gate_A'

class EvacAgent(CognitiveAgent):
    def __init__(self,model,aid,profile,start):
        CognitiveAgent.__init__(self,aid,profile,start)
        self.model=model; self.unique_id=aid; self.pos=None
        model.register_agent(self)

class EvacModel(mesa.Model):
    def __init__(self,sid,n=None,dt_s=10,seed=20240923,use_llm=False,
                 decision_interval=3,decision_interval_calm=12,broadcast_override=None,
                 rescue_min=None,rescue_flat=2.0,rescue_stair=.9,lethal_hold=600,
                 rescue_rate=3.0,rescue_window=120,
                 herding=True,fam_level=None,depth_override=None,alarm_min='UNSET',
                 exit_width=2.0,start_override=None,entry_override=None,
                 fam_frac=None,tag='run'):
        super().__init__(seed=seed)
        self.scn=get_scenario(sid)
        if depth_override:
            self.scn={**self.scn,'depth':{**self.scn['depth'],**depth_override}}
        self.dt_s=dt_s; self.use_llm=use_llm
        self.decision_interval=decision_interval
        self.decision_interval_calm=decision_interval_calm; self.tag=tag
        self.rescue_min=rescue_min; self.rescue_flat=rescue_flat
        self.rescue_stair=rescue_stair; self.lethal_hold=lethal_hold
        self.rescue_rate=rescue_rate; self.rescue_window=rescue_window
        self.herding=herding; self.fam_level=fam_level; self.exit_width=exit_width
        self._step_enter={}
        self.kb=KnowledgeBase()
        self.entry=entry_override if entry_override else pick_entry(self.scn)
        self.env=FloodEnv(depth_params(self.scn),entry=self.entry)
        nref=self.scn['population']['n_ref']
        self.n=n if n else min(nref,400)
        profs=sample_population(self.n,seed)
        if fam_frac is not None:
            nonstaff=[p for p in profs if p['角色']!='站务']
            k_hi=int(round(fam_frac*len(nonstaff)))
            for j,p in enumerate(nonstaff): p['熟悉度']='高' if j<k_hi else '低'
        elif fam_level=='high':
            for p in profs:
                if p['角色']!='站务': p['熟悉度']='高'
        elif fam_level=='low':
            for p in profs:
                if p['角色']!='站务': p['熟悉度']='低'
        rng=np.random.default_rng(seed)
        for i,pf in enumerate(profs):
            if start_override is not None: start=start_override
            elif pf['角色']=='站务': start='hall'
            else:
                r=rng.random(); start='platform' if r<.6 else 'hall' if r<.85 else \
                    ('corr_A' if r<.925 else 'corr_B')
            EvacAgent(self,i,pf,start)
        self.alarm=self.scn['response']['alarm_min']
        if alarm_min!='UNSET': self.alarm=alarm_min
        self.broadcast_override=broadcast_override
        self.sim_step=0; self.step_rows=[]; self.traj=[]
        self.datacollector=mesa.DataCollector(model_reporters={
          'in':lambda m:sum(a.status=='in' for a in m.agents),
          'evacuated':lambda m:sum(a.status=='evacuated' for a in m.agents),
          'stranded':lambda m:sum(a.status=='stranded' for a in m.agents),
          'rescued':lambda m:sum(a.status=='rescued' for a in m.agents),
          'deceased':lambda m:sum(a.status=='deceased' for a in m.agents)})
        self.datacollector.collect(self)
    def broadcast_active(self,t_min):
        if self.broadcast_override is not None: return self.broadcast_override
        return self.alarm is not None and t_min>=self.alarm
    def node_counts(self):
        c={}
        for a in self.agents:
            n=a.node
            if n: c[n]=c.get(n,0)+1
        return c
    def step(self):
        dt=self.dt_s; t_min=self.sim_step*dt/60.0
        self.env.update_water(t_min)
        bc=self.broadcast_active(t_min)
        counts=self.node_counts()
        # 人群目标图（观察他人正从本节点去往何处）；关闭从众时置空
        flow={}
        if self.herding:
            for a in self.agents:
                if a.edge: flow.setdefault(a.edge[0],[]).append(a.edge[1])
        occ={}
        for a in self.agents:
            if a.edge:
                k=tuple(sorted((a.edge[0],a.edge[1]))); occ[k]=occ.get(k,0)+1
        order=self.agents.shuffle(inplace=False)
        self._step_enter={}
        acts=[]
        for a in order:
            n=a.node or (a.edge[0] if a.edge else 'platform')
            dens=counts.get(n,0)/AREA.get(n,100)
            targets=flow.get(n,[])
            a.update(self.env,self.sim_step,dt,bc,dens,targets,occ,
                     use_llm=self.use_llm,decision_interval=self.decision_interval,
                     decision_interval_calm=self.decision_interval_calm)
            if a.cur_action is not None and a.last_dec_step==self.sim_step:
                acts.append(a.cur_action)
            # 个体轨迹
            ref=a.node or (a.edge[0] if a.edge else n)
            self.traj.append({'step':self.sim_step,'id':a.id,'loc':ref,
                'depth':round(self.env.G.nodes[ref]['depth'],3) if ref in self.env.G else None,
                'action':a.cur_action,'status':a.status})
        ne=sum(a.status=='evacuated' for a in self.agents)
        ns=sum(a.status=='stranded' for a in self.agents)
        nr=sum(a.status=='rescued' for a in self.agents)
        nd=sum(a.status=='deceased' for a in self.agents)
        self.step_rows.append({'step':self.sim_step,'t_min':round(t_min,2),'broadcast':bc,
            'in':self.n-ne-ns-nr-nd,'evacuated':ne,'stranded':ns,'rescued':nr,'deceased':nd,
            'mean_exposure_s':round(np.mean([a.exposure_s for a in self.agents]),1)})
        self.datacollector.collect(self)
        self.sim_step+=1
        return acts
    def can_enter_edge(self,n,tgt):
        """断面比流量限流（Fruin 水平约75 人/(m·min)）：对楼扶梯/闸机断面按每步通过率限流。"""
        g=self.env.G
        if g.nodes[n]['type'] not in ('stair','gate') and g.nodes[tgt]['type'] not in ('stair','gate'):
            return True
        key=tuple(sorted((n,tgt))); used=self._step_enter.get(key,0)
        quota=int(np.ceil(75*self.exit_width*(self.dt_s/60.0)))
        if used>=quota: return False
        self._step_enter[key]=used+1; return True
    def run(self,n_steps=120,rescue_min=None):
        for _ in range(n_steps):
            self.step()
            if all(a.status in ('evacuated','stranded') for a in self.agents): break
        rmin=self.rescue_min if rescue_min is None else rescue_min
        if rmin is not None:
            while self.sim_step*self.dt_s/60.0 < rmin:
                self.step()
            self.extract_phase(rmin)
        else:
            self.finalize_no_rescue()
        return self.summary()
    def finalize_no_rescue(self):
        """无救援：深水受困(超过失稳阈值)→致死风险；浅水受困维持待援。"""
        for a in self.agents:
            if a.status!='stranded': continue
            if a.peak_depth>a.lethal_depth() or a.lethal_s>=self.lethal_hold:
                a.status='deceased'
    def rescue_component(self):
        """救援者可到达的节点：从干的地面出入口进入；平地(舟艇)水深≤rescue_flat，楼梯≤rescue_stair。"""
        import networkx as nx
        g=self.env.G
        def rpass(n):
            d=g.nodes[n]['depth']; ty=g.nodes[n]['type']
            lim=self.rescue_stair if ty=='stair' else self.rescue_flat
            return d<=lim
        nodes=[n for n in g.nodes if rpass(n)]
        H=g.subgraph(nodes)
        staging=[n for n in nodes if g.nodes[n]['is_exit'] and g.nodes[n]['depth']<=self.rescue_flat]
        comp=set()
        for s in staging:
            comp.update(nx.node_connected_component(H,s))
        return comp
    def _agent_depth(self,a):
        if a.node is not None: pts=[a.node]
        elif a.edge is not None: pts=[a.edge[0],a.edge[1]]
        else: pts=[]
        d=max([self.env.G.nodes[p]['depth'] for p in pts],default=0.0)
        return d,pts
    def extract_phase(self,rmin,window=None):
        """有限运力救援：逐分钟更新水深与可达域；未受困可达者引导步行出站；
        深水受困者按舟艇运力(人/min)、深水优先提取；不可达且没顶者致死。"""
        window=self.rescue_window if window is None else window
        bucket=0.0
        for k in range(int(window)+1):
            t=rmin+k
            self.env.update_water(t)
            comp=self.rescue_component()
            # 引导未受困、可达者步行出站（不占舟艇运力）
            for a in self.agents:
                if a.status=='in':
                    _,pts=self._agent_depth(a)
                    if any(p in comp for p in pts):
                        a.status='rescued'; a.rescue_time=t
            # 不可达且没顶/超时受困 → 致死
            for a in self.agents:
                if a.status!='stranded': continue
                d,pts=self._agent_depth(a)
                if not any(p in comp for p in pts) and \
                   (d>a.lethal_depth() or a.lethal_s>=self.lethal_hold):
                    a.status='deceased'
            # 舟艇运力提取可达受困者（深水优先 triage）
            bucket+=self.rescue_rate
            cand=[]
            for a in self.agents:
                if a.status!='stranded': continue
                d,pts=self._agent_depth(a)
                if any(p in comp for p in pts): cand.append((d,a))
            cand.sort(key=lambda x:-x[0])
            take=int(np.floor(bucket))
            for d,a in cand[:take]:
                a.status='rescued'; a.rescue_time=t
            bucket-=min(take,len(cand))
            if all(a.status in ('evacuated','rescued','deceased') for a in self.agents): break
        # 时间窗结束仍受困：没顶者致死，浅水维持 stranded（未决风险）
        for a in self.agents:
            if a.status=='stranded':
                d,_=self._agent_depth(a)
                if d>a.lethal_depth(): a.status='deceased'
    def summary(self):
        ag=list(self.agents)
        def cnt(s): return sum(a.status==s for a in ag)
        survived=cnt('evacuated')+cnt('rescued')
        res={'sid':self.scn['id'],'name':self.scn['name'],'n':self.n,
          'evacuated':cnt('evacuated'),'rescued':cnt('rescued'),
          'stranded':cnt('stranded'),'deceased':cnt('deceased'),
          'survive_rate':round(survived/self.n,3),
          'evac_rate':round(cnt('evacuated')/self.n,3),
          'evac_times':[round(a.evac_time,2) for a in ag if a.evac_time is not None],
          'mean_exposure_s':round(float(np.mean([a.exposure_s for a in ag])),1),
          'peak_depths':[round(a.peak_depth,2) for a in ag]}
        return res
    def save(self):
        pd.DataFrame(self.step_rows).to_excel(
            ROOT/'results'/'runs'/f"{self.scn['id']}_{self.tag}_metrics.xlsx",index=False)
        pd.DataFrame(self.traj).to_excel(
            ROOT/'results'/'runs'/f"{self.scn['id']}_{self.tag}_traj.xlsx",index=False)

def draw_timing():
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['axes.unicode_minus']=False
    fig,ax=plt.subplots(figsize=(12,4.2)); ax.axis('off'); ax.set_xlim(0,12); ax.set_ylim(0,6)
    lanes=[('环境层\n更新水深 depth(t)\n出口/可达状态','#dbe9f6',4.6),
           ('认知层（LLM）\n感知→评估→应对\n动作白名单','#fde6d2',3.2),
           ('运动层（规则）\n路径裁决→涉水移动\n瓶颈排队','#d9ece0',1.8)]
    for t,fc,y in lanes:
        b=FancyBboxPatch((.4,y-.55),3.0,1.1,boxstyle='round,pad=.02',fc=fc,ec='#7a8791')
        ax.add_patch(b); ax.text(1.9,y,t,ha='center',va='center',fontsize=9.3)
    steps=['①更新\n积水','②个体\n感知','③检索\n知识','④LLM\n决策','⑤可达性\n裁决','⑥涉水\n移动','⑦记录\n日志']
    x=4.3
    for i,s in enumerate(steps):
        xx=x+i*1.05
        b=FancyBboxPatch((xx-.42,2.5),.84,1.0,boxstyle='round,pad=.02',fc='#e8e0f0',ec='#8a7fa0')
        ax.add_patch(b); ax.text(xx,3.0,s,ha='center',va='center',fontsize=8.2)
        if i<len(steps)-1:
            ax.add_patch(FancyArrowPatch((xx+.42,3.0),(xx+.63,3.0),arrowstyle='-|>',
                mutation_scale=11,color='#666'))
    ax.text(1.9,4.05,'',); 
    for y1,y2 in [(4.05,3.75),(2.65,2.35)]:
        ax.add_patch(FancyArrowPatch((1.9,y1),(1.9,y2),arrowstyle='<|-|>',mutation_scale=11,color='#888'))
    ax.text(6,5.4,'图4-3 混合仿真引擎单步时序（决策/运动解耦，LLM结果缓存）',
            ha='center',fontsize=12.5,fontweight='bold')
    ax.text(6,.7,'决策每 decision_interval 步或到达节点时触发；运动每步按涉水速度推进，dt=10s',
            ha='center',fontsize=9,color='#555')
    fig.savefig(FIG/'fig_引擎时序.png',dpi=200,bbox_inches='tight'); plt.close()
    print('已写 fig_引擎时序.png')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--sid',default='SCN-001'); ap.add_argument('--n',type=int,default=40)
    ap.add_argument('--steps',type=int,default=240); ap.add_argument('--llm',action='store_true')
    ap.add_argument('--rescue',type=float,default=None); ap.add_argument('--seed',type=int,default=20240923)
    ap.add_argument('--rescue_flat',type=float,default=2.0)
    a=ap.parse_args()
    m=EvacModel(a.sid,n=a.n,use_llm=a.llm,rescue_min=a.rescue,seed=a.seed,
                 rescue_flat=a.rescue_flat,tag='smoke')
    res=m.run(a.steps); m.save()
    print(json.dumps({k:v for k,v in res.items() if k not in ('evac_times','peak_depths')},
        ensure_ascii=False,indent=2))
    draw_timing()
