# -*- coding: utf-8 -*-
"""第4章 步骤1：轻量化空间—积水环境（NetworkX）。
抽象标准两层岛式车站拓扑；水深由 depth(t) 沿高程重力传播；支持出口关闭与可达路径。"""
from pathlib import Path
import numpy as np, networkx as nx
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']; plt.rcParams['axes.unicode_minus']=False
from hydro import depth_t
ROOT=Path(__file__).resolve().parents[1]; FIG=ROOT/'results'/'figures'

# 节点：id -> (中文, 高程level, 容量, 是否出口, 类型)
NODES={
 'gate_A':('A出入口',0,60,True,'gate'),'gate_B':('B出入口',0,60,True,'gate'),
 'wind':('风亭',0,20,False,'vent'),
 'corr_A':('A口通道',-1,120,False,'flat'),'corr_B':('B口通道',-1,120,False,'flat'),
 'hall':('站厅',-1,400,False,'flat'),
 'stair_A':('A楼扶梯',-1,50,False,'stair'),'stair_B':('B楼扶梯',-1,50,False,'stair'),
 'platform':('站台',-2,500,False,'flat'),'interval':('区间隧道',-2,300,False,'flat')}
EDGES=[('gate_A','corr_A',15),('gate_B','corr_B',15),('corr_A','hall',10),('corr_B','hall',10),
 ('hall','stair_A',8),('hall','stair_B',8),('stair_A','platform',8),('stair_B','platform',8),
 ('platform','interval',50),('wind','hall',30)]
# 各节点相对进水的传播滞后(min)与水深系数（重力：下层为汇水点）
LAG={'gate_A':0,'gate_B':0,'wind':0,'corr_A':3,'corr_B':3,'hall':4,
 'stair_A':6,'stair_B':6,'platform':8,'interval':8}
COEF={'gate_A':1.0,'gate_B':0.0,'wind':0.0,'corr_A':0.9,'corr_B':0.0,'hall':0.9,
 'stair_A':0.95,'stair_B':0.0,'platform':1.0,'interval':0.0}
GATE_CLOSE=0.30; FLAT_LIMIT=.70; STAIR_LIMIT=.30

class FloodEnv:
    def __init__(self, depth_p, entry='gate_A'):
        self.p=depth_p; self.entry=entry
        self.G=nx.Graph()
        for n,(lab,lv,cap,ex,ty) in NODES.items():
            self.G.add_node(n,label=lab,level=lv,cap=cap,is_exit=ex,type=ty,
                            depth=0.0,passable=True,exit_open=ex)
        for a,b,d in EDGES: self.G.add_edge(a,b,dist=d)
        # 进水节点系数置1
        COEF2=dict(COEF); COEF2[self.entry]=1.0
        # 非进水的同层另一出口保持干燥（已由COEF=0表达）
        self._coef=COEF2
        self.t=0.0
    def update_water(self,t):
        self.t=t
        for n in self.G.nodes:
            tt=max(t-LAG[n],0.0)
            d=float(depth_t(tt,self.p))*self._coef[n]
            self.G.nodes[n]['depth']=d
            ty=self.G.nodes[n]['type']
            limit=STAIR_LIMIT if ty=='stair' else FLAT_LIMIT
            self.G.nodes[n]['passable']=d<limit
            if self.G.nodes[n]['is_exit']:
                self.G.nodes[n]['exit_open']=d<GATE_CLOSE
    def speed(self,n):
        """涉水走行速度 m/s（平地 v0(1-h/.7)，楼梯 v0(1-h/.3)）。"""
        d=self.G.nodes[n]['depth']; ty=self.G.nodes[n]['type']
        if ty=='stair': return max(0.0,0.45*(1-d/.30))
        return max(0.0,1.0*(1-d/.70))
    def open_exits(self):
        return [n for n in self.G.nodes if self.G.nodes[n]['is_exit'] and self.G.nodes[n]['exit_open']]
    def path_to_exit(self,start):
        """到最近的开放且可达出口的最短路径（按距离）；无则 None。"""
        ok=[n for n in self.G.nodes if self.G.nodes[n]['passable']]
        H=self.G.subgraph(ok)
        targets=[n for n in ok if self.G.nodes[n]['is_exit'] and self.G.nodes[n]['exit_open']]
        if start not in H or not targets: return None
        best=None
        for tg in targets:
            try:
                p=nx.shortest_path(H,start,tg,weight='dist')
                L=sum(self.G.edges[p[i],p[i+1]]['dist'] for i in range(len(p)-1))
                if best is None or L<best[1]: best=(p,L)
            except nx.NetworkXNoPath: pass
        return best[0] if best else None
    def observe(self,start):
        """个体当前可感知信息（仅本节点与相邻节点，不泄露全局）。"""
        g=self.G
        return {'node':start,'depth':round(g.nodes[start]['depth'],3),
                'neighbors':{n:round(g.nodes[n]['depth'],2) for n in g.neighbors(start)},
                'open_exits_nearby':[n for n in g.neighbors(start)
                    if g.nodes[n]['is_exit'] and g.nodes[n]['exit_open']]}

POS={'gate_A':(1,3),'gate_B':(7,3),'wind':(4,3.7),'corr_A':(1.4,1.4),'corr_B':(6.6,1.4),
 'hall':(4,.4),'stair_A':(2.4,-.9),'stair_B':(5.6,-.9),'platform':(4,-2.2),'interval':(4,-3.5)}

def draw(env, sid, t_snap):
    env.update_water(t_snap)
    fig,ax=plt.subplots(figsize=(10,8)); ax.axis('off')
    depths=[env.G.nodes[n]['depth'] for n in env.G.nodes]
    vmax=max(max(depths),.5)
    for a,b,_ in EDGES:
        ax.plot([POS[a][0],POS[b][0]],[POS[a][1],POS[b][1]],color='#9aa7b1',lw=1.4,zorder=1)
    for n,(x,y) in POS.items():
        d=env.G.nodes[n]['depth']; r=d/vmax
        fc=(1,1-r*.55,1-r*.55) if d>0 else '#eef3f7'
        bw,bh=.95,.55
        box=FancyBboxPatch((x-bw/2,y-bh/2),bw,bh,boxstyle='round,pad=0.02,rounding_size=.06',
            fc=fc,ec=('#c0392b' if env.G.nodes[n]['is_exit'] and not env.G.nodes[n]['exit_open']
                 else '#c0392b' if env.G.nodes[n]['is_exit'] else '#7a8791'),
            lw=2.0 if env.G.nodes[n]['is_exit'] else 1.1,zorder=2)
        ax.add_patch(box)
        lab=NODES[n][0]+(f'\n{d:.2f}m' if d>0 else '')
        ax.text(x,y,lab,ha='center',va='center',fontsize=8.4,zorder=3)
    ax.text(4,4.5,f'图4-1 标准两层岛式车站空间网络与积水分布（{sid}，t={t_snap:.0f}min）',
            ha='center',fontsize=12.5,fontweight='bold')
    ax.text(4,-4.3,'红框=安全出口；填充越红水深越大；红框加粗实线=出口已关闭',ha='center',fontsize=9,color='#555')
    ax.set_xlim(-.5,8.5); ax.set_ylim(-4.7,4.9)
    ax.set_aspect('equal')
    fig.savefig(FIG/'fig_空间网络拓扑.png',dpi=200,bbox_inches='tight'); plt.close()
    print('已写 fig_空间网络拓扑.png')

if __name__=='__main__':
    from hydro import get_scenario,depth_params
    scn=get_scenario('SCN-001'); env=FloodEnv(depth_params(scn),entry='gate_A')
    for t in (0,10,25,60,150):
        env.update_water(t)
        print(f't={t:3d}  gateA={env.G.nodes["gate_A"]["depth"]:.2f} hall={env.G.nodes["hall"]["depth"]:.2f} '
              f'platform={env.G.nodes["platform"]["depth"]:.2f} 开放出口={env.open_exits()}')
    env.update_water(15)
    print('站台→出口路径:',env.path_to_exit('platform'))
    draw(env,'SCN-001',60)
