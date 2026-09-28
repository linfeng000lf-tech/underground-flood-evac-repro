# -*- coding: utf-8 -*-
"""
任务7：基于本体的情景抽取（规则模板 + 可选 LLM）。
规则离线产出抽取表；`python code/10_extract.py --llm` 在密钥有效时用 LLM 补规则留空字段。
输出：data/processed/情景抽取表.xlsx（3表）、data/processed/情景抽取实例.jsonl
"""
import re, sys, json, argparse
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; PROC=ROOT/'data'/'processed'
x1=pd.read_excel(PROC/'clean_文件1_应急数据.xlsx',dtype=object)
x2=pd.read_excel(PROC/'clean_文件2_案例汇总.xlsx',dtype=object)
def c(x): return '' if pd.isna(x) else str(x).strip()
F=x2.groupby('案例名称',sort=False).first()

# ---------- 事件类型归并（按“进水直接机制”优先级）----------
ETYPE=[
 ('T8 给水/消防管爆裂',['消防水管爆裂','消防管爆裂','给水管道','自来水管爆裂']),
 ('T3 台风伴生内涝',['台风']),
 ('T5 施工透水/突水突泥',['突水突泥','透水','涌砂','涌泥','盾构','掌子面','桩孔透水','老空区透水',
        '岩溶水突水','冻结法','钻穿','泥浆涌出','围护桩','护壁透水']),
 ('T4 挡水/结构设施失效',['挡水墙倒塌','止水帷幕破裂','管片','天花塌漏','天花板塌漏',
        '外部管道破裂','地面下陷','水管接驳口脱落','结构裂损','地下室外墙','外墙破坏',
        '渗漏点','结构渗漏','隧道渗漏']),
 ('T6 管网/污水倒灌',['污水涌入','污水倒灌','排水管道','下水道','排污口回涌','检查井爆裂',
        '排水管堵塞','气囊','污水管检查井','管网堵塞','封堵口','污水管封堵','窨井']),
 ('T7 有限空间作业淹溺',['有限空间','井下作业','集水井','污水管网清理','失足坠','坠入',
        '中毒','缺氧','水位突涨','井下水位','盖板塌陷','孔洞','掉入','落入']),
 ('T2 河/湖/山洪倒灌',['河水倒灌','河流洪水','山洪','湖水','护城河','运河','洪水倒灌',
        '上游来水','洪灾','管涌']),
 ('T1 暴雨内涝倒灌',['暴雨','雨水倒灌','强降水','降雨','地表积水','内涝','积水倒灌','出入口进水',
        '风井倒灌','极端暴雨','倒灌','积水']),
]
def hits_in(text):
    out=[]
    for code,kws in ETYPE:
        if any(k in text for k in kws) and code not in out: out.append(code)
    return out
def decide(core,full,pt,evac,evacnote):
    h=hits_in(core) or hits_in(full)
    fall=(pt=='作业人员' and evac.startswith('无公众')
          and bool(re.search(r'坠入|跌落|失足|盖板塌陷|掉入|落入',core+evacnote)))
    if any(x.startswith('T5') for x in h):
        pri=next(x for x in h if x.startswith('T5'))
    elif fall:
        pri=next((x for x in h if x.startswith('T7')),'T7 有限空间作业淹溺')
    elif h: pri=h[0]
    elif pt=='作业人员': pri='T7 有限空间作业淹溺'
    else: pri='未明确'
    return pri,[x for x in h if x!=pri][:3]

# ---------- 洪水来源 ----------
def water_src(text):
    if re.search(r'消防水管爆裂|消防管爆裂|给水管道|自来水管爆裂|饮用水管|给水管',text): return 'W7 消防/给水'
    if '山洪' in text: return 'W3 山洪'
    if re.search(r'河水|河道水|湖水|运河|护城河|洪灾',text): return 'W2 河/湖/潮汐'
    if re.search(r'承压|岩溶|老空',text): return 'W4 地下水/承压/岩溶/老空'
    if re.search(r'集水坑|基坑积水|施工积水',text): return 'W6 施工水体'
    if re.search(r'雨水|暴雨|降雨|降水|强降水',text) and not re.search(r'污水涌入|污水倒灌',text):
        return 'W1 大气降水/地表径流'
    if re.search(r'污水|排水管道|下水道|管网|检查井|排污',text): return 'W5 市政管网'
    if '地下水' in text: return 'W4 地下水/承压/岩溶/老空'
    return 'W1 大气降水/地表径流'

# ---------- 致因类别与失效构件 ----------
def cause_flags(direct,indirect):
    return ('是' if re.search(r'环境[:：]',direct) else '',
            '是' if re.search(r'行为[:：]',direct) else '',
            '是' if re.search(r'决策[:：]',direct) else '',
            '是' if re.search(r'管理[:：]',indirect) else '')
COMP=[('挡水墙/挡水板',['挡水墙','挡水板']),('止水帷幕',['止水帷幕']),('管片',['管片']),
 ('盾尾密封',['盾尾密封','盾尾']),('封堵/气囊',['封堵','气囊']),('污水管/检查井',['污水管','检查井']),
 ('排水泵/抽排设施',['排水泵','水泵','抽排']),('围护桩/护壁/边坡',['围护桩','护壁','边坡']),
 ('沙袋/临时挡水',['沙袋']),('其他管道',['管道'])]
def failed_comp(text):
    return '；'.join(name for name,kws in COMP if any(k in text for k in kws))

# ---------- 峰值水深 ----------
QUAL=[('没顶/淹至头顶',1.8),('淹至胸',1.3),('淹至腰',1.0),('膝盖',0.45),('脚踝|脚面',0.12)]
def d_peak(*fields):
    clauses=[]
    for f in fields:
        for s in re.split(r'[；;\n。]',c(f)):
            if re.search(r'路面|路段|地面|水库|道路|京广|水池',s): continue
            clauses.append(s)
    best=None; qflag=''
    def take(v,flag):
        nonlocal best,qflag
        if 0<v<=3.0 and (best is None or v>best): best,qflag=v,flag
    for s in clauses:
        for lab,val in QUAL:
            if re.search(lab,s): take(val,'定性')
        m=re.search(r'(?:水深|积水|水位|淹没)\S{0,5}?([\d.]+)\s*米',s)
        if m: take(float(m.group(1)),'实测/记载')
        m=re.search(r'(?:水深|积水|水位|淹没|内部积水)\S{0,5}?([\d.]+)\s*(?:厘米|cm)\b',s)
        if m: take(float(m.group(1))/100,'实测/记载')
        m=re.search(r'峰值\s*[\d.]+\s*[-~]\s*([\d.]+)\s*m\b',s)
        if m: take(float(m.group(1)),'实测/记载(管内)')
    return best,qflag

# ---------- 人群类型/数量 ----------
def pop_type(text):
    worker=bool(re.search(r'作业|施工|井下|工人|清淤|勘探|检修|盾构|掌子面|工地|基坑|操作',text))
    passenger=bool(re.search(r'乘客|列车|运营',text))
    public=bool(re.search(r'业主|小区|车库|顾客|群众|商场|住户',text))
    n=sum([worker,passenger,public])
    if n>1: return '混合'
    if worker: return '作业人员'
    if passenger: return '乘客'
    if public: return '公众'
    return '未明确'
def pop_count(text):
    best=None
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*万(?:多人|余人|人)',text):
        best=max(best or 0,float(m.group(1))*10000)
    for m in re.finditer(r'(\d+)\s*(?:余人|多人|余名)',text):
        best=max(best or 0,float(m.group(1)))
    return int(best) if best else None

# ---------- 响应时序 ----------
def first_clock(text,ctx):
    cand=[]
    for s in re.split(r'[；;\n。]',text):
        if re.search(ctx,s):
            for m in re.finditer(r'(\d{1,2}):(\d{2})',s):
                cand.append(int(m.group(1))*60+int(m.group(2)))
    return f'{min(cand)//60:02d}:{min(cand)%60:02d}' if cand else ''
def evac_min(text):
    m=re.search(r'(\d+)\s*分钟(?:内)?(?:完成|结束)?疏散',text)
    if m: return int(m.group(1))
    m=re.search(r'疏散.{0,6}?(\d+)\s*分钟',text)
    return int(m.group(1)) if m else None
def booleans(text):
    return ('是' if re.search(r'设防|挡水板|反坡|驼峰|防汛挡板|沙袋|防水闸',text) else '',
            '是' if re.search(r'漫过|冲垮|倒塌|溃决|失效|冲开|冲开',text) else '',
            '是' if re.search(r'排水泵|抽排|排水设施',text) else '',
            '是' if re.search(r'排水不及|超负荷|无法及时排|排水能力不足',text) else '')

# ---------- 逐案例抽取 ----------
main_rows=[]; cause_rows=[]; time_rows=[]
for nm in F.index:
    r=F.loc[nm]
    et=c(r['事故类型']); direct=c(r['直接原因']); indirect=c(r['间接原因'])
    measures=c(r['处置措施(原)']); evacnote=c(r['疏散备注'])
    evac=c(r['疏散情况'])
    core=' '.join([nm,et,direct,c(r['地下空间类型'])])
    blob=' '.join([nm,et,direct,indirect,measures,evacnote,c(r['地下空间类型'])])
    pt0=pop_type(blob)
    pri,sec=decide(core,blob,pt0,evac,evacnote); ws=water_src(core)
    env,beh,dec,mng=cause_flags(direct,indirect); fc=failed_comp(blob)
    dp,dq=d_peak(evacnote,measures,direct)
    pt=pop_type(blob); pc=pop_count(evacnote)
    dfp,dfl,drp,drol=booleans(blob)
    ta=first_clock(measures,r'报警|报告|拨打')
    ts=first_clock(measures,r'启动|停运|封闭|疏散|响应')
    em=evac_min(measures)
    def num(col):
        v=c(r[col]);
        return float(v) if v else None
    spacecode='地铁车站' if '金沙湖' in nm else c(r['地下空间类型编码'])
    if re.search(r'标准|导则|规程|预案|指引|论文|建议与答复|综合报道',nm): kind,inc='文献制度','否'
    elif re.search(r'英睿顶盛|体之翼',nm): kind,inc='非地下空间(游泳)','否'
    elif '质能科技' in nm: kind,inc='信息不足','否'
    elif nm=='湖南长沙新昌路项目“7·20”工地淹溺事故': kind,inc='重复记录','否'
    else: kind,inc='真实事件','是'
    main_rows.append([nm,c(r['事件时间']),pri,'；'.join(sec),ws,spacecode,
        c(r['事故等级']),c(r['政府响应级别']),c(r['企业响应级别']),c(r['推断置信度']),
        dp,dq,pt,pc,dfp,dfl,drp,drol,
        num('死亡人数'),num('失踪人数'),num('受伤人数'),num('直接经济损失_万元'),num('中断时长_小时'),
        kind,inc])
    cause_rows.append([nm,env,beh,dec,mng,fc,direct,indirect])
    time_rows.append([nm,ta,ts,em,measures])

# ---------- 可选 LLM 补空（仅 --llm 且密钥有效）----------
ap=argparse.ArgumentParser(); ap.add_argument('--llm',action='store_true'); args=ap.parse_args()
if args.llm:
    try:
        from llm_utils import llm_json, config
        if config()['api_key'] in ('','请在此粘贴你的API密钥','你的API密钥'): raise RuntimeError('占位密钥')
        schema=['事件类型','洪水来源','峰值水深_m','人群类型','关键失效构件']
        for i in range(len(main_rows)):
            nm=main_rows[i][0]
            cr=next(x for x in cause_rows if x[0]==nm)
            prompt=(f'案例：{nm}\n直接原因：{cr[6][:600]}\n处置：{next(x for x in time_rows if x[0]==nm)[4][:600]}\n'
                    '请抽取：事件类型(T1-T8中文)、洪水来源、峰值水深_m(数字或null)、人群类型、关键失效构件。只输出JSON。')
            try:
                o=llm_json(prompt,system='你是地下空间水灾信息抽取助手，只输出JSON。',schema=schema,tag='07_情景抽取_LLM')
                if not main_rows[i][2].startswith('T'): main_rows[i][2]=o.get('事件类型') or main_rows[i][2]
                if main_rows[i][10] is None and isinstance(o.get('峰值水深_m'),(int,float)):
                    main_rows[i][10]=float(o['峰值水深_m']); main_rows[i][11]='LLM抽取'
            except Exception as e:
                print('LLM跳过',nm[:20],type(e).__name__)
    except Exception as e:
        print('未启用LLM（',type(e).__name__,str(e)[:60],'），仅用规则结果')

# ---------- 写出 ----------
hm=['案例名称','事件时间','事件类型(主)','事件类型(次)','洪水来源','地下空间类型','事故等级','政府响应','企业响应','置信度',
    '峰值水深_m','水深标记','人群类型','人群数量','设防存在','设防失效','排水存在','排水失效',
    '死亡','失踪','受伤','损失_万元','中断_小时','资料类型','纳入情景库']
hc=['案例名称','环境因','行为因','决策因','管理因','失效构件','直接原因(原)','间接原因(原)']
ht=['案例名称','最早报警','最早响应启动','疏散用时_min','处置措施(原)']
out=PROC/'情景抽取表.xlsx'
with pd.ExcelWriter(out,engine='openpyxl') as w:
    pd.DataFrame(main_rows,columns=hm).to_excel(w,sheet_name='事件情景抽取',index=False)
    pd.DataFrame(cause_rows,columns=hc).to_excel(w,sheet_name='致因抽取',index=False)
    pd.DataFrame(time_rows,columns=ht).to_excel(w,sheet_name='响应时序抽取',index=False)
# JSONL
with open(PROC/'情景抽取实例.jsonl','w',encoding='utf-8') as f:
    for row in main_rows:
        f.write(json.dumps(dict(zip(hm,row)),ensure_ascii=False,default=str)+'\n')

print('事件类型(主)分布:')
print(pd.Series([r[2] for r in main_rows]).value_counts().to_string())
print('\n峰值水深已提取案例数:',sum(1 for r in main_rows if r[10] is not None))
print('已写 情景抽取表.xlsx / 情景抽取实例.jsonl；共',len(main_rows),'案例')
