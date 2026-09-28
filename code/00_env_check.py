# -*- coding: utf-8 -*-
"""环境自检：确认关键库可导入并打印版本。运行：python code/00_env_check.py"""
import sys, importlib

print('Python:', sys.version.split()[0], '|', sys.executable)

mods = [
    ('pandas', None), ('numpy', None), ('openpyxl', None), ('jieba', None),
    ('openai', None), ('dotenv', 'python-dotenv'), ('pydantic', None),
    ('networkx', None), ('mesa', None),
    ('sklearn', 'scikit-learn'), ('xgboost', None), ('mlxtend', None),
    ('shap', None), ('matplotlib', None), ('seaborn', None),
    ('tqdm', None), ('joblib', None), ('fitz', 'pymupdf'), ('docx', 'python-docx'),
]
ok, fail = 0, 0
for m, pkg in mods:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, '__version__', 'ok')
        print(f'  [OK] {pkg or m:16s} {ver}')
        ok += 1
    except Exception as e:
        print(f'  [FAIL] {pkg or m:14s} {e}')
        fail += 1

print(f'\n结果：{ok} 个可用，{fail} 个失败')
sys.exit(1 if fail else 0)
