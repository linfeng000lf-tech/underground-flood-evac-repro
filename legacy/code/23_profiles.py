# -*- coding: utf-8 -*-
"""第4章 步骤2：异质人群画像。维度分布（据案例与公开统计设定）+ 固定种子抽样。"""
import json, argparse
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']; plt.rcParams['axes.unicode_minus']=False
ROOT=Path(__file__).resolve().parents[1]; KN=ROOT/'data'/'knowledge'; FIG=ROOT/'results'/'figures'

# 各维度取值与概率（车站客流场景；透明先验，可在第5章用案例再标定）
DIST={
 '年龄':{'儿童':.06,'青年':.45,'中年':.38,'老年':.11},
 '性别':{'男':.48,'女':.52},
 '行动能力':{'正常':.86,'缓慢':.10,'受限':.04},
 '角色':{'乘客':.97,'站务':.03},
 '熟悉度':{'高':.10,'中':.30,'低':.60},
 '结伴':{'独自':.55,'结伴':.32,'家庭组':.13},
 '水灾经验':{'有':.18,'无':.82},
 '风险偏好':{'厌恶':.52,'中性':.40,'寻求':.08},
}
MOB_SPEED={'正常':1.0,'缓慢':.8,'受限':.55}

def _pick(rng,probd):
    k=list(probd); return rng.choice(k,p=[probd[x] for x in k])

def sample_profile(rng):
    role=_pick(rng,DIST['角色'])
    age=_pick(rng,DIST['年龄'])
    # 行动能力与年龄联动
    if age=='儿童': mob=rng.choice(['缓慢','受限'],p=[.7,.3])
    elif age=='老年': mob=rng.choice(['正常','缓慢','受限'],p=[.25,.55,.20])
    else: mob=_pick(rng,{'正常':.93,'缓慢':.05,'受限':.02})
    fam='高' if role=='站务' else _pick(rng,DIST['熟悉度'])
    p={'角色':role,'年龄':age,'性别':_pick(rng,DIST['性别']),'行动能力':mob,
       '熟悉度':fam,'结伴':_pick(rng,DIST['结伴']),'水灾经验':_pick(rng,DIST['水灾经验']),
       '风险偏好':_pick(rng,DIST['风险偏好'])}
    p['速度系数']=MOB_SPEED[mob]
    return p

def sample_population(n,seed=20240923):
    rng=np.random.default_rng(seed)
    return [sample_profile(rng) for _ in range(n)]

def draw(n=300,seed=20240923):
    pop=sample_population(n,seed)
    fig,axes=plt.subplots(2,4,figsize=(14,7)); dims=list(DIST)
    for ax,dim in zip(axes.flat,dims):
        vals=[p[dim] for p in pop]
        cats=list(DIST[dim]); cnt=[vals.count(c) for c in cats]
        b=ax.bar(cats,cnt,color='#5b9bd5',edgecolor='#2e5e8c')
        ax.bar_label(b,fontsize=8,padding=2)
        ax.set_title(dim,fontsize=11); ax.tick_params(labelsize=9)
        ax.set_ylim(0,max(cnt)*1.18)
    fig.suptitle(f'图4-4 异质人群画像各维度分布（n={n}，seed={seed}）',fontsize=13.5,fontweight='bold')
    fig.tight_layout(rect=[0,0,1,.96]); fig.savefig(FIG/'fig_画像分布.png',dpi=200); plt.close()
    print('已写 fig_画像分布.png')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--n',type=int,default=300)
    ap.add_argument('--seed',type=int,default=20240923); a=ap.parse_args()
    pop=sample_population(a.n,a.seed)
    KN.mkdir(exist_ok=True)
    (KN/'人群画像分布.json').write_text(json.dumps(
        {'distributions':DIST,'mobility_speed':MOB_SPEED,'seed':a.seed,'n':a.n},
        ensure_ascii=False,indent=2),encoding='utf-8')
    from collections import Counter
    for dim in DIST:
        print(dim,dict(Counter(p[dim] for p in pop)))
    print('示例画像:',pop[0])
    draw(a.n,a.seed)
