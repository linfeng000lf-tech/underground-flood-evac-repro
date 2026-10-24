# -*- coding: utf-8 -*-
"""
llm_utils 离线逻辑测试（不联网、不需要密钥）：
JSON抽取 / 校验 / 缓存命中 / 非法JSON重试 / schema失败重试 / 限流异常重试 / 日志落盘。
运行：python code/test_llm_utils.py
"""
import sys, tempfile, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_utils

# 把缓存/日志重定向到临时目录
_tmp = Path(tempfile.mkdtemp(prefix='llmtest_'))
llm_utils.BASE = _tmp

passed = []
def check(name, cond):
    assert cond, '失败: ' + name
    passed.append(name)

# ---------- 1) extract_json ----------
check('纯对象', llm_utils.extract_json('{"a":1,"b":"x"}') == {'a': 1, 'b': 'x'})
check('代码围栏', llm_utils.extract_json('```json\n{"a":1}\n```') == {'a': 1})
check('前后带解释', llm_utils.extract_json('好的，结果如下：\n{"a":1}\n以上。') == {'a': 1})
check('数组', llm_utils.extract_json('[{"a":1},{"a":2}]') == [{'a': 1}, {'a': 2}])
try:
    llm_utils.extract_json('没有任何json')
    check('非法应报错', False)
except ValueError:
    check('非法应报错', True)

# ---------- 2) validate ----------
ok, _ = llm_utils.validate({'a': 1, 'b': 2}, ['a', 'b'])
check('必填键齐全', ok)
ok, err = llm_utils.validate({'a': 1}, ['a', 'b'])
check('缺键拦截', not ok and 'b' in err)
ok, _ = llm_utils.validate({'x': -1}, lambda o: o['x'] >= 0 or 'x必须非负')
check('自定义校验拦截', not ok)
ok, _ = llm_utils.validate({'x': 5}, lambda o: o['x'] >= 0)
check('自定义校验通过', ok)

# ---------- 伪造底层调用 ----------
def make_fake(side_effects):
    calls = {'n': 0, 'history': []}
    def fake(messages, model, temperature, max_tokens, json_mode):
        idx = calls['n']
        calls['n'] += 1
        effect = side_effects[min(idx, len(side_effects) - 1)]
        calls['history'].append(messages)
        if isinstance(effect, Exception):
            raise effect
        return effect, {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}
    return fake, calls

# ---------- 3) 成功 + 缓存命中 ----------
fake, calls = make_fake(['{"案例类型":"透水","地下空间类型":"区间隧道"}'])
llm_utils._raw_chat = fake
r1 = llm_utils.llm_json('p1', schema=['案例类型', '地下空间类型'], tag='t1')
r2 = llm_utils.llm_json('p1', schema=['案例类型', '地下空间类型'], tag='t1')
check('结果正确', r1['案例类型'] == '透水')
check('缓存命中(只调1次)', calls['n'] == 1 and r2 == r1)

# 不同 prompt 应再调用
llm_utils.llm_json('p2-different', schema=['案例类型'], tag='t1')
check('不同请求不命中缓存', calls['n'] == 2)

# ---------- 4) 非法 JSON -> 重试后成功 ----------
fake, calls = make_fake(['结果是 {"a": 1 坏了', '{"a":1}'])
llm_utils._raw_chat = fake
r = llm_utils.llm_json('p3', tag='t2')
check('非法JSON重试成功', r == {'a': 1} and calls['n'] == 2)
check('重试带纠错提示', any('未能通过校验' in m['content']
                            for m in calls['history'][1] if m['role'] == 'user'))

# ---------- 5) schema 失败 -> 重试后成功 ----------
fake, calls = make_fake(['{"a":1}', '{"a":1,"b":2}'])
llm_utils._raw_chat = fake
r = llm_utils.llm_json('p4', schema=['a', 'b'], tag='t3')
check('缺字段重试成功', r == {'a': 1, 'b': 2} and calls['n'] == 2)

# ---------- 6) 限流异常 -> 重试后成功 ----------
class RateLimitError(Exception):
    pass
llm_utils._raw_chat, calls = make_fake([RateLimitError('429 rate limit'), '{"ok":true}'])
llm_utils.time.sleep = lambda s: None        # 去掉退避等待
r = llm_utils.llm_json('p5', tag='t4')
check('限流后重试成功', r == {'ok': True} and calls['n'] == 2)

# ---------- 7) 日志与缓存文件 ----------
cache_path = _tmp / 'results' / 'cache' / 'llm_cache.json'
log_path = _tmp / 'results' / 'runs' / 'llm_calls.jsonl'
check('缓存文件存在', cache_path.exists())
lines = [json.loads(x) for x in log_path.read_text(encoding='utf-8').splitlines()]
check('日志含ok/retry/cached',
      {'ok', 'retry'} <= {x['status'] for x in lines}
      and any(x.get('cached') for x in lines))

print('\n全部 %d 项测试通过 ✔' % len(passed))
for i, n in enumerate(passed, 1):
    print(f'  {i:2d}. {n}')
print('\n临时目录:', _tmp)
