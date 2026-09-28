# -*- coding: utf-8 -*-
"""
LLM 连通性验证。
用法（先在 .env 填好 LLM_API_KEY）：
    python code/01_llm_check.py
可选：加 --backup 测试备用模型；加 --all 主备都测。
"""
import os, sys, time, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from openai import OpenAI

PLACEHOLDERS = ('', '请在此粘贴你的API密钥', '请在此粘贴第二家密钥', '你的API密钥')


def test_endpoint(tag, key_var, url_var, model_var):
    key = os.getenv(key_var, '').strip()
    base = os.getenv(url_var, '').strip()
    model = os.getenv(model_var, '').strip()
    print(f'\n===== {tag} =====')
    print(f'  base_url : {base}')
    print(f'  model    : {model}')

    if key in PLACEHOLDERS:
        print('  [跳过] 尚未配置有效 API 密钥：请打开 .env 填写 ' + key_var)
        return False
    print(f'  key      : {key[:4]}****{key[-4:] if len(key) > 8 else ""}')

    client = OpenAI(api_key=key, base_url=base, timeout=30)
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user',
                       'content': '只回复两个字：正常'}],
            max_tokens=10, temperature=0,
        )
        dt = time.time() - t0
        text = resp.choices[0].message.content.strip()
        print(f'  [成功] 模型回复：“{text}”  耗时 {dt:.2f} 秒')
        return True
    except Exception as e:
        dt = time.time() - t0
        name = type(e).__name__
        print(f'  [失败] {name}（{dt:.2f} 秒）')
        msg = str(e)
        print('         ' + msg[:300])
        if 'authentication' in msg.lower() or '401' in msg or 'api key' in msg.lower():
            print('         -> 多为密钥错误/未生效，请核对 LLM_API_KEY。')
        elif 'connect' in msg.lower() or 'timeout' in msg.lower():
            print('         -> 多为网络/代理问题，请检查网络或 base_url。')
        return False


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--backup', action='store_true', help='只测备用模型')
    ap.add_argument('--all', action='store_true', help='主备模型都测')
    args = ap.parse_args()

    results = {}
    if args.backup:
        results['备用'] = test_endpoint('备用模型', 'LLM_API_KEY_BACKUP',
                                        'LLM_BASE_URL_BACKUP', 'LLM_MODEL_BACKUP')
    else:
        results['主用'] = test_endpoint('主用模型', 'LLM_API_KEY',
                                        'LLM_BASE_URL', 'LLM_MODEL')
        if args.all:
            results['备用'] = test_endpoint('备用模型', 'LLM_API_KEY_BACKUP',
                                            'LLM_BASE_URL_BACKUP', 'LLM_MODEL_BACKUP')

    print('\n===== 汇总 =====')
    for k, v in results.items():
        print(f'  {k}: {"通过" if v else "未通过/未配置"}')
    sys.exit(0 if any(results.values()) else 1)
