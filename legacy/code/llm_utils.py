# -*- coding: utf-8 -*-
"""
全篇复用的 LLM 调用模块。
核心：llm_json() —— 重试(指数退避) + 磁盘缓存 + JSONL 日志 + JSON 抽取与校验。

用法
----
from llm_utils import llm_json
data = llm_json(
    prompt='从文本抽取字段...',
    system='你是应急信息抽取助手，只输出JSON。',
    schema=['案例类型', '地下空间类型'],   # 也可传 pydantic 模型 / 自定义函数
    tag='01_情景抽取',
)

配置：根目录 .env 的 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL。
"""
import os
import re
import json
import time
import hashlib
import random
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# ---------- 路径与配置 ----------
BASE = Path(__file__).resolve().parents[1]          # 工程根；测试时可 monkeypatch
load_dotenv(BASE / '.env')

def _paths():
    cache_dir = BASE / 'results' / 'cache'
    runs_dir = BASE / 'results' / 'runs'
    cache_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / 'llm_cache.json', runs_dir / 'llm_calls.jsonl'

def config():
    provider = (os.getenv('LLM_PROVIDER', '') or '').strip().lower()
    if provider in ('backup', 'qwen', 'qwen-plus', 'ali', 'dashscope'):
        return {
            'api_key': os.getenv('LLM_API_KEY_BACKUP', '').strip(),
            'base_url': os.getenv('LLM_BASE_URL_BACKUP', '').strip(),
            'model': os.getenv('LLM_MODEL_BACKUP', '').strip(),
        }
    return {
        'api_key': os.getenv('LLM_API_KEY', '').strip(),
        'base_url': os.getenv('LLM_BASE_URL', '').strip(),
        'model': os.getenv('LLM_MODEL', '').strip(),
    }

_PLACEHOLDER = {'', '请在此粘贴你的API密钥', '你的API密钥'}
_clients = {}
_MEMCACHE = {}      # 进程内缓存：cache路径 -> dict，避免每次调用重读整盘缓存

def _get_memcache(cache_path, use_cache):
    if not use_cache:
        return {}
    key = str(cache_path)
    if key not in _MEMCACHE:
        _MEMCACHE[key] = _load_cache()
    return _MEMCACHE[key]

def get_client():
    """惰性创建 OpenAI 兼容客户端（DeepSeek/通义/Ollama 均兼容），按 base_url 分别缓存。"""
    cfg = config()
    if cfg['api_key'] in _PLACEHOLDER:
        raise RuntimeError('未配置有效 LLM_API_KEY：请在工程根 .env 填入真实密钥')
    if cfg['base_url'] not in _clients:
        from openai import OpenAI
        _clients[cfg['base_url']] = OpenAI(
            api_key=cfg['api_key'], base_url=cfg['base_url'], timeout=60)
    return _clients[cfg['base_url']]


# ================= 日志 =================
def _log(record: dict):
    _, log_path = _paths()
    record = {'ts': datetime.now().isoformat(timespec='seconds'), **record}
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


# ================= 缓存 =================
def _load_cache():
    cache_path, _ = _paths()
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def _save_cache(cache):
    cache_path, _ = _paths()
    tmp = cache_path.with_suffix('.tmp')
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
    tmp.replace(cache_path)

def _cache_key(base_url, model, messages, temperature, max_tokens):
    raw = json.dumps({'base_url': base_url, 'model': model, 'messages': messages,
                      'temperature': temperature, 'max_tokens': max_tokens},
                     ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


# ================= JSON 抽取 =================
_FENCE = re.compile(r'^\s*```(?:json)?\s*|\s*```\s*$', re.IGNORECASE)

def extract_json(text: str):
    """从可能带解释/代码围栏的文本中抽取 JSON 对象或数组，返回解析结果；失败抛 ValueError。"""
    if text is None:
        raise ValueError('模型返回为空')
    s = text.strip()
    s = _FENCE.sub('', s).strip()

    candidates = [s]
    for opener, closer in (('{', '}'), ('[', ']')):
        if opener in s and closer in s:
            candidates.append(s[s.find(opener): s.rfind(closer) + 1])

    seen = set()
    for c in candidates:
        c = c.strip()
        if c in seen:
            continue
        seen.add(c)
        try:
            return json.loads(c)
        except Exception:
            continue
    raise ValueError('未在输出中找到可解析的 JSON')


# ================= 校验 =================
def validate(obj, schema):
    """
    schema 支持：
      - pydantic 模型类：模型校验，返回其 dump 的 dict
      - list/tuple/set：必填键名集合
      - callable：fn(obj) 返回 True 或错误字符串/抛异常
    返回 (通过?, 结果或错误信息)。
    """
    if schema is None:
        return True, obj

    # pydantic 模型
    if hasattr(schema, 'model_validate'):
        try:
            m = schema.model_validate(obj)
            return True, m.model_dump()
        except Exception as e:
            return False, str(e)

    if callable(schema):
        try:
            r = schema(obj)
        except Exception as e:
            return False, str(e)
        if isinstance(r, str):          # 返回字符串 = 错误信息
            return False, r
        if r is False:
            return False, '自定义校验未通过'
        if isinstance(r, dict):         # 返回 dict = 转换后的结果
            return True, r
        return True, obj                # True / None / 其它真值 = 通过

    if isinstance(schema, (list, tuple, set)):
        if not isinstance(obj, dict):
            return False, '输出应为 JSON 对象(含字段: %s)' % ', '.join(map(str, schema))
        missing = [k for k in schema if k not in obj]
        if missing:
            return False, '缺少必填字段: %s' % ', '.join(map(str, missing))
        return True, obj

    return False, '不支持的 schema 类型: %r' % type(schema)


# ================= 原始对话（可被测试 monkeypatch） =================
def _raw_chat(messages, model, temperature, max_tokens, json_mode):
    """调用一次接口，返回 (文本, usage字典)。json_mode 不被支持时自动降级。"""
    client = get_client()
    kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if json_mode:
        try:
            resp = client.chat.completions.create(response_format={'type': 'json_object'}, **kwargs)
            return resp.choices[0].message.content, _usage(resp)
        except Exception as e:
            if _is_jsonmode_unsupported(e):
                pass            # 降级为普通模式
            else:
                raise
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content, _usage(resp)

def _usage(resp):
    u = getattr(resp, 'usage', None)
    if u is None:
        return {}
    return {'prompt_tokens': getattr(u, 'prompt_tokens', None),
            'completion_tokens': getattr(u, 'completion_tokens', None),
            'total_tokens': getattr(u, 'total_tokens', None)}

def _is_jsonmode_unsupported(e):
    m = str(e).lower()
    return ('response_format' in m or 'json' in m) and ('not support' in m or 'unsupported' in m
            or 'invalid' in m or 'unrecognized' in m or 'unknown' in m)


# ================= 可重试异常判定 =================
def _retryable(e):
    name = type(e).__name__
    if name in ('RateLimitError', 'APITimeoutError', 'APIConnectionError',
                'InternalServerError', 'ConflictError'):
        return True
    m = str(e).lower()
    return any(x in m for x in ('429', '502', '503', '504', 'timeout',
                                'overloaded', 'rate limit', 'temporarily'))


# ================= 主函数 =================
def llm_json(prompt, system=None, schema=None, model=None, temperature=0.0,
             max_tokens=2000, retries=4, use_cache=True, json_mode=True,
             tag='', seed=None, **kw):
    """
    返回通过校验的 JSON（dict/list）。全部尝试失败时抛 RuntimeError。
    缓存键只与请求有关；命中缓存仍会按当前 schema 校验，校验不过则带纠错信息重试。
    """
    cfg = config()
    model = model or cfg['model']
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    cache_path, _ = _paths()
    cache = _get_memcache(cache_path, use_cache)
    ckey = _cache_key(cfg['base_url'], model, messages, temperature, max_tokens)

    if use_cache and ckey in cache:
        cached_text = cache[ckey]['content']
        try:
            obj = extract_json(cached_text)
            ok, result = validate(obj, schema)
            if ok:
                _log({'tag': tag, 'model': model, 'cached': True, 'status': 'ok'})
                return result
        except Exception:
            pass
        # 缓存内容未通过当前校验 -> 落到下面的纠错重试

    last_err = ''
    _prev_text = ''
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            call_messages = messages
            if last_err:
                correction = [
                    {'role': 'user', 'content':
                        '上一次输出未能通过校验（%s）。请修正，并只输出一个合法 JSON，'
                        '不要输出解释或代码围栏。' % last_err},
                ]
                if _prev_text:
                    correction.insert(0, {'role': 'assistant', 'content': _prev_text})
                call_messages = messages + correction
            text, usage = _raw_chat(call_messages, model, temperature, max_tokens, json_mode)
            _prev_text = text
            dt = time.time() - t0

            obj = extract_json(text)
            ok, result = validate(obj, schema)
            if not ok:
                raise ValueError('JSON 校验失败: %s' % result)

            if use_cache:
                cache[ckey] = {'content': text, 'model': model,
                               'ts': datetime.now().isoformat(timespec='seconds')}
                _save_cache(cache)
            _log({'tag': tag, 'model': model, 'cached': False, 'status': 'ok',
                  'attempt': attempt, 'latency_s': round(dt, 2), **usage})
            return result

        except Exception as e:
            dt = time.time() - t0
            last_err = str(e)
            bad_json = isinstance(e, ValueError)
            retry_now = attempt < retries and (bad_json or _retryable(e))
            _log({'tag': tag, 'model': model, 'cached': False,
                  'status': 'retry' if retry_now else 'fail',
                  'attempt': attempt, 'latency_s': round(dt, 2),
                  'error': type(e).__name__, 'detail': last_err[:300]})
            if not retry_now:
                break
            wait = min(2 ** attempt + random.random(), 30)
            time.sleep(wait)

    raise RuntimeError('llm_json 多次调用仍失败[%s]: %s' % (tag, last_err))


def llm_text(prompt, system=None, model=None, temperature=0.3, max_tokens=2000,
             retries=3, tag='', **kw):
    """纯文本返回（同样带重试/日志/缓存）。"""
    cfg = config()
    model = model or cfg['model']
    messages = ([{'role': 'system', 'content': system}] if system else [])
    messages.append({'role': 'user', 'content': prompt})
    cache_path, _ = _paths()
    cache = _get_memcache(cache_path, True)
    ckey = _cache_key(cfg['base_url'], model, messages, temperature, max_tokens)
    if ckey in cache:
        _log({'tag': tag, 'model': model, 'cached': True, 'status': 'ok'})
        return cache[ckey]['content']

    last_err = ''
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            text, usage = _raw_chat(messages, model, temperature, max_tokens, False)
            cache[ckey] = {'content': text, 'model': model,
                           'ts': datetime.now().isoformat(timespec='seconds')}
            _save_cache(cache)
            _log({'tag': tag, 'model': model, 'cached': False, 'status': 'ok',
                  'attempt': attempt, 'latency_s': round(time.time() - t0, 2), **usage})
            return text
        except Exception as e:
            last_err = str(e)
            retry_now = attempt < retries and _retryable(e)
            _log({'tag': tag, 'model': model, 'status': 'retry' if retry_now else 'fail',
                  'attempt': attempt, 'error': type(e).__name__, 'detail': last_err[:300]})
            if not retry_now:
                break
            time.sleep(min(2 ** attempt + random.random(), 30))
    raise RuntimeError('llm_text 多次调用仍失败[%s]: %s' % (tag, last_err))
