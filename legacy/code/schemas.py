# -*- coding: utf-8 -*-
"""结构化输出的 pydantic 数据模型（对应指南 4.3），与 prompts/ 下 JSON Schema 一致。
LLM 返回后立即用这些模型校验，非法值（动作越界、水深为负）直接判失败并重试/置空。"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

# ---- 第3章：情景抽取 ----
class StageEvent(BaseModel):
    time: Optional[str] = None
    water_depth_cm: Optional[float] = Field(None, ge=0)
    location: Optional[str] = None
    info_broadcast: Optional[str] = None
    crowd_action: Optional[str] = None

class ScenarioExtractResult(BaseModel):
    case_id: str
    事件类型: Optional[str] = None
    洪水来源: Optional[str] = None
    空间类型: Optional[str] = None
    进水位置: Optional[str] = None
    峰值水深_m: Optional[float] = Field(None, ge=0, le=10)
    人群类型: Optional[str] = None
    人群数量: Optional[int] = Field(None, ge=0)
    关键失效构件: Optional[str] = None
    stage_chain: List[StageEvent] = []
    evacuation_started: Optional[bool] = None
    confidence: float = Field(0.0, ge=0, le=1)

# ---- 第4章：个体疏散决策 ----
Action = Literal['immediate_evacuate','wait_and_see','follow_crowd','nearest_exit',
                 'follow_guidance','turn_back','help_others','shelter_stay']
class AgentDecision(BaseModel):
    action: Action
    target: Optional[str] = None
    risk_perception: float = Field(0.0, ge=0, le=1)
    coping_appraisal: float = Field(0.0, ge=0, le=1)
    social_influence: float = Field(0.0, ge=0, le=1)
    reason: str = ''
    confidence: float = Field(0.0, ge=0, le=1)

# ---- 第3/4章：知识抽取 ----
class KnowledgeItem(BaseModel):
    id: str
    type: Literal['explicit','implicit']
    tags: List[str] = []
    text: str
    source: Optional[str] = None
    confidence: float = Field(0.0, ge=0, le=1)
class KnowledgeExtract(BaseModel):
    items: List[KnowledgeItem] = []

# ---- 第3章：情景推演 ----
class DepthParams(BaseModel):
    d0: float = Field(0.0, ge=0)
    t_seep: float = Field(0, ge=0)
    t_peak: float = Field(0, ge=0)
    t_plat: float = Field(0, ge=0)
    t_end: float = Field(0, ge=0)
    d_peak: float = Field(0.0, ge=0, le=10)
class ScenarioDeduction(BaseModel):
    scenario_id: str
    archetype: str
    event: str
    space: str
    defense: Literal['达标','薄弱','失效']
    drain: Literal['充足','一般','失效']
    depth: DepthParams
    prior_risk_band: Optional[Literal['低','中','高']] = None
    note: str = ''

if __name__=='__main__':
    d=AgentDecision(action='wait_and_see',risk_perception=.4,coping_appraisal=.6,reason='信息不足，先观望')
    print('示例决策校验通过:',d.action)
    try:
        AgentDecision(action='fly_away')
    except Exception as e:
        print('非法动作被拦截:',type(e).__name__)
