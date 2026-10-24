# -*- coding: utf-8 -*-
"""全篇复用：可复现性设置与实验配置落盘（对应指南 4.4、2.7）。"""
import os, json, random, datetime
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
EXP_DIR=ROOT/'experiments'
SEED=20240923

def set_seed(seed=SEED):
    """统一随机种子：random / numpy；仿真、抽样、机器学习共用。"""
    random.seed(seed); np.random.seed(seed)
    os.environ['PYTHONHASHSEED']=str(seed)
    return seed

def write_run_config(tag, params=None, model=None, temperature=None, seed=SEED,
                     scenarios=None, extra=None):
    """为每次实验生成带时间戳的配置文件，记录模型/温度/种子/情景，保证可复现。"""
    EXP_DIR.mkdir(parents=True,exist_ok=True)
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    cfg={'run_tag':tag,'timestamp':ts,'model':model,'temperature':temperature,'seed':seed,
         'scenarios':scenarios,'params':params or {},'extra':extra or {}}
    fp=EXP_DIR/f'{ts}_{tag}.json'
    fp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    return fp

if __name__=='__main__':
    set_seed()
    demo=write_run_config('环境自检',model='deepseek-chat',temperature=0.0,seed=SEED,
                          scenarios=['SCN-001'],extra={'note':'可复现性配置示例'})
    print('种子已设置为',SEED,'；示例配置：',demo)
