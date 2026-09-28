@echo off
setlocal enableextensions
title 城市地下空间水灾人群疏散计算实验 - 一键复现
set "ROOT=E:\underground-flood-evac"
set "ENV=C:\Users\30525\miniconda3\envs\flood"
set "PY=%ENV%\python.exe"
set "SOLARA=%ENV%\Scripts\solara.exe"
set "PATH=%ENV%;%ENV%\Scripts;%PATH%"
cd /d "%ROOT%"
if not exist "%PY%" (
  echo [错误] 未找到 flood 环境的 python：%PY%
  echo 请确认 miniconda 路径，或先创建 flood 环境。
  pause
  goto end
)

:menu
cls
echo ============================================================
echo    城市地下空间水灾人群疏散  计算实验平台 - 一键复现
echo ============================================================
echo.
echo   [1] 快速单次疏散仿真（离线，免费，约1分钟）
echo   [2] 启动网页可视化平台（浏览器实时动画）
echo   [3] 完整复现全流程（离线/本地缓存，默认不花钱，用时较长）
echo   [4] 完整复现 + 真实大模型与千问跨模型（调用API，有费用）
echo   [5] 环境自检（Python / 依赖 / LLM 连通）
echo   [0] 退出
echo.
set "choice="
set /p choice=请输入选项编号后回车:
if "%choice%"=="1" goto quick
if "%choice%"=="2" goto web
if "%choice%"=="3" goto full
if "%choice%"=="4" goto full_llm
if "%choice%"=="5" goto check
if "%choice%"=="0" goto end
goto menu

:quick
cls
echo ===== 快速单次疏散仿真 SCN-001（离线）=====
"%PY%" code\26_mesa_engine.py --sid SCN-001 --n 40 --steps 360
goto donemenu

:web
cls
echo ===== 网页可视化平台 =====
echo 浏览器将打开 http://127.0.0.1:8767
echo 关闭本黑色窗口即停止服务；若网页未自动打开，请手动输入上面地址。
start "" http://127.0.0.1:8767
"%SOLARA%" run code\28_viz.py --host 127.0.0.1 --port 8767
goto donemenu

:check
cls
echo ===== 环境自检 =====
"%PY%" code\00_env_check.py
echo.
echo ===== LLM 连通测试（会真实调用一次）=====
"%PY%" code\01_llm_check.py
goto donemenu

:full
cls
echo ===== 完整复现（离线/本地缓存，默认不花钱）=====
echo 大规模批量步骤可能耗时较长，请耐心等待；中途勿关闭窗口。
echo.
echo --- [1] 数据清洗 ---
"%PY%" code\06_clean.py || goto failed
echo --- [2] 情景本体 ---
"%PY%" code\09_ontology.py || goto failed
echo --- [3] 情景要素抽取（命中本地缓存则免费）---
"%PY%" code\10_extract.py || goto failed
echo --- [4] 抽取质量抽检 ---
"%PY%" code\11_audit.py || goto failed
echo --- [5] 受控词表 ---
"%PY%" code\12_controlled_vocab.py || goto failed
echo --- [6] 水深参数化 ---
"%PY%" code\13_depth_param.py || goto failed
echo --- [7] 情景库推演 ---
"%PY%" code\14_scenario_lib.py || goto failed
echo --- [8] 情景库一致性审计 ---
"%PY%" code\16_scenario_audit.py || goto failed
echo --- [9] 空间-积水环境 ---
"%PY%" code\22_space_env.py || goto failed
echo --- [10] 异质人群画像 ---
"%PY%" code\23_profiles.py || goto failed
echo --- [11] 知识库 ---
"%PY%" code\24_knowledge_base.py || goto failed
echo --- [12] 案例回放校准 ---
"%PY%" code\31_case_replay.py || goto failed
echo --- [13] 经典效应复现 ---
"%PY%" code\32_classic_effects.py || goto failed
echo --- [14] 留出案例盲测 ---
"%PY%" code\33_holdout.py || goto failed
echo --- [15] 稳健性分析 ---
"%PY%" code\34_robustness.py || goto failed
echo --- [16] LHS实验设计 ---
"%PY%" code\35_experiment_design.py || goto failed
echo --- [17] 大规模批量运行（1920 run，耗时较长）---
"%PY%" code\36_batch_run.py || goto failed
echo --- [18] 批量结果汇总 ---
"%PY%" code\38_batch_summary.py || goto failed
echo --- [19] 特征宽表构建 ---
"%PY%" code\42_build_features.py || goto failed
echo --- [20] 描述性分析 ---
"%PY%" code\43_descriptive.py || goto failed
echo --- [21] 关联规则挖掘 ---
"%PY%" code\44_association_rules.py || goto failed
echo --- [22] 机器学习模型 ---
"%PY%" code\45_ml_models.py || goto failed
echo --- [23] SHAP可解释性 ---
"%PY%" code\46_shap.py || goto failed
echo --- [24] 交叉验证 ---
"%PY%" code\47_cross_validate.py || goto failed
echo --- [25] 干预沙盘阈值 ---
"%PY%" code\48_sandbox_thresholds.py || goto failed
goto success

:full_llm
cls
echo ============================================================
echo  [提示] 本选项会真实调用 DeepSeek / 千问 API，产生费用。
echo  本地已做缓存，命中缓存不重复计费；千问跨模型约需1-2小时。
echo ============================================================
set "ok="
set /p ok=确认继续请输入 yes 后回车:
if /i not "%ok%"=="yes" goto menu
call :full || goto failed
echo --- [附加1] 真实LLM抽检 ---
"%PY%" code\41_llm_spotcheck.py || goto failed
echo --- [附加2] 千问跨模型复现（约1-2小时）---
"%PY%" code\50_qwen_replicate.py --k 16 || goto failed
goto success

:success
echo.
echo ============================================================
echo  [完成] 全流程复现结束。
echo  论文图在 results\figures ; 运行数据在 results\runs
echo ============================================================
goto donemenu

:failed
echo.
echo ============================================================
echo  [中断] 某一步运行失败，请向上查看报错信息。
echo  常见原因：依赖缺失、原始Excel未放回 data\raw、API密钥/网络问题。
echo ============================================================

:donemenu
echo.
set "back="
set /p back=输入 r 返回菜单，输入 0 退出:
if "%back%"=="r" goto menu
if "%back%"=="0" goto end
goto donemenu

:end
endlocal
exit /b 0
