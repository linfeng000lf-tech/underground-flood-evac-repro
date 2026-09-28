# -*- coding: utf-8 -*-
"""第4章 SolaraViz 网页实时动画。
运行： solara run code/28_viz.py   （浏览器打开 http://localhost:8765）
左侧为车站网络—积水—人群实时动画，右侧为撤离/受困/救援/死亡曲线。
离线自检： python code/28_viz.py   （渲染若干帧到 results/figures，不启动网页）"""
import importlib
import solara
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from mesa.visualization import SolaraViz, make_plot_component
from mesa.visualization.utils import update_counter

# 国内网络下 jsdelivr 常被重置，改用 unpkg 作为前端资源 CDN（drop-in）
solara.settings.assets.cdn = 'https://unpkg.com/'

_s22=importlib.import_module('22_space_env')
POS=_s22.POS; NODES=_s22.NODES; EDGES=_s22.EDGES
EvacModel=importlib.import_module('26_mesa_engine').EvacModel

STATUS_STYLE={'in':('#1f6fb2','o',46),'evacuated':('#2e9e44','o',46),
 'stranded':('#e8772e','s',52),'rescued':('#17a2b8','o',46),'deceased':('#333333','X',64)}

def _agent_xy(a):
    if a.edge:
        u,v,rem,tot=a.edge; frac=(tot-rem)/tot
        return (POS[u][0]+(POS[v][0]-POS[u][0])*frac,
                POS[u][1]+(POS[v][1]-POS[u][1])*frac)
    n=a.node if a.node else a.start
    return POS[n]

def draw_frame(ax,model):
    """绘制单帧：网络—积水—人群。Solara 组件与离线自检共用，保证所见即所测。"""
    xs=[p[0] for p in POS.values()]; ys=[p[1] for p in POS.values()]
    ax.set_xlim(min(xs)-1.1,max(xs)+1.1); ax.set_ylim(min(ys)-.9,max(ys)+1.0); ax.axis('off')
    for u,v,_ in EDGES:
        ax.plot([POS[u][0],POS[v][0]],[POS[u][1],POS[v][1]],color='#9aa7b1',lw=2,zorder=1)
    for name,(zh,lv,cap,isex,ty) in NODES.items():
        d=model.env.G.nodes[name]['depth']; r=min(d/.70,1.2)
        fc=(1,.93-r*.33,.93-r*.62) if d>0 else '#f4f7fa'
        open_=model.env.G.nodes[name]['exit_open']
        ec='#2e9e44' if (isex and open_) else '#c0392b' if isex else '#7a8791'
        ax.add_patch(Circle(POS[name],.34,fc=fc,ec=ec,lw=3.0 if isex else 1.3,zorder=2))
        ax.text(POS[name][0],POS[name][1]-.52,f"{zh}\n{d:.2f}m",
                ha='center',va='top',fontsize=7.6,zorder=3)
    for a in model.agents:
        x,y=_agent_xy(a); col,mk,sz=STATUS_STYLE.get(a.status,STATUS_STYLE['in'])
        ax.scatter([x],[y],c=col,marker=mk,s=sz,edgecolors='white',linewidths=.5,zorder=4)
    t=model.sim_step*model.dt_s/60.0
    ax.set_title(f"t={t:.1f} min   广播:{'是' if model.broadcast_active(t) else '否'}",fontsize=11)
    ax.text(0.01,0.99,'●在站  ●已撤离  ■受困  ●获救  ✕死亡；出口绿框=开放/红框=关闭',
            transform=ax.transAxes,ha='left',va='top',fontsize=7.8)

@solara.component
def NetworkView(model):
    update_counter.get()
    fig=Figure(figsize=(8.6,9.4)); ax=fig.add_subplot()
    draw_frame(ax,model)
    solara.FigureMatplotlib(fig,format='png',bbox_inches='tight')

OutcomePlot=make_plot_component(['evacuated','stranded','rescued','deceased'])

page=SolaraViz(
    EvacModel,
    components=[NetworkView,OutcomePlot],
    model_params={
        'n': {'type':'slider','min':10,'max':200,'step':10,'value':80,'label':'站内人数'},
        'herding': {'type':'checkbox','value':True,'label':'从众行为'},
    },
    play_interval=250,
    name='地下空间水灾人群疏散实时动画',
)

if __name__=='__main__':
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from pathlib import Path
    FIG=Path(__file__).resolve().parents[1]/'results'/'figures'
    m=EvacModel('SCN-001',n=80,tag='frame')
    for k in range(240):
        m.step()
        if k in (60,150,239):
            fig,ax=plt.subplots(figsize=(8.6,9.4)); draw_frame(ax,m)
            fig.savefig(FIG/f'fig_动画帧_{k}.png',dpi=130,bbox_inches='tight'); plt.close()
    df=m.datacollector.get_model_vars_dataframe()
    print('帧已生成；曲线列:',list(df.columns),'行数',len(df))
    print(df.iloc[[-1]].to_dict('records')[0])
