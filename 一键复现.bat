@echo off
setlocal enableextensions
title Underground Flood Crowd Evacuation - One-Click Reproduction
rem ROOT is automatically set to the folder containing this .bat (portable; no hard-coded paths)
set "ROOT=%~dp0"
rem Use the Python on your PATH; activate your conda/venv (with requirements.txt) before running.
set "PY=python"
set "SOLARA=solara"
set "PATH=%LOCALAPPDATA%\Programs\Python;%PATH%"
cd /d "%ROOT%"

:menu
cls
echo ============================================================
echo    Underground Flood Crowd Evacuation Platform - Reproduce
echo ============================================================
echo.
echo   [1] Quick evacuation demo (offline, about 1 min)
echo   [2] Web visualization platform (real-time animation)
echo   [3] Full process (heuristic/offline, no API cost, long)
echo   [4] Full process + real LLM (API cost, optional)
echo   [5] Environment self-check (Python / packages / LLM link)
echo   [0] Exit
echo.
set "choice="
set /p choice=Enter the option number and press Enter:
if "%choice%"=="1" goto quick
if "%choice%"=="2" goto web
if "%choice%"=="3" goto full
if "%choice%"=="4" goto full_llm
if "%choice%"=="5" goto check
if "%choice%"=="0" goto end
goto menu

:quick
cls
echo ===== Quick evacuation demo (SCN-001, offline) =====
"%PY%" code\26_mesa_engine.py --sid SCN-001 --n 40 --steps 360
goto donemenu

:web
cls
echo ===== Web visualization platform =====
echo Opening http://127.0.0.1:8767
echo Close this window or press Ctrl+C to stop. If the page does not open, visit the address manually.
start "" http://127.0.0.1:8767
"%SOLARA%" run code\28_viz.py --host 127.0.0.1 --port 8767
goto donemenu

:check
cls
echo ===== Environment self-check =====
"%PY%" code\00_env_check.py
echo.
echo ===== LLM connectivity (one real call; skip if you have no API key) =====
"%PY%" code\01_llm_check.py
goto donemenu

rem NOTE: cleaned/processed data is already shipped in data\, so the pipeline starts at
rem ontology / extraction and does not re-run the raw-data cleaning step (06_clean).
:full
cls
echo ===== Full process (heuristic/offline, no API cost) =====
echo This runs many steps and may take a long time. Please be patient and do not close the window.
echo.
echo --- [1] Ontology ---
"%PY%" code\09_ontology.py || goto failed
echo --- [2] Scenario element extraction ---
"%PY%" code\10_extract.py || goto failed
echo --- [3] Extraction audit ---
"%PY%" code\11_audit.py || goto failed
echo --- [4] Controlled vocabulary ---
"%PY%" code\12_controlled_vocab.py || goto failed
echo --- [5] Water depth parameterization ---
"%PY%" code\13_depth_param.py || goto failed
echo --- [6] Scenario library ---
"%PY%" code\14_scenario_lib.py || goto failed
echo --- [7] First-stage audit ---
"%PY%" code\16_scenario_audit.py || goto failed
echo --- [8] Space-flood environment ---
"%PY%" code\22_space_env.py || goto failed
echo --- [9] Population profiles ---
"%PY%" code\23_profiles.py || goto failed
echo --- [10] Knowledge base ---
"%PY%" code\24_knowledge_base.py || goto failed
echo --- [11] Case replay calibration ---
"%PY%" code\31_case_replay.py || goto failed
echo --- [12] Classic effects ---
"%PY%" code\32_classic_effects.py || goto failed
echo --- [13] Holdout cases ---
"%PY%" code\33_holdout.py || goto failed
echo --- [14] Robustness analysis ---
"%PY%" code\34_robustness.py || goto failed
echo --- [15] LHS experiment design ---
"%PY%" code\35_experiment_design.py || goto failed
echo --- [16] Batch model runs (1920 runs, long) ---
"%PY%" code\36_batch_run.py || goto failed
echo --- [17] Batch results summary ---
"%PY%" code\38_batch_summary.py || goto failed
echo --- [18] Feature construction ---
"%PY%" code\42_build_features.py || goto failed
echo --- [19] Descriptive analysis ---
"%PY%" code\43_descriptive.py || goto failed
echo --- [20] Association rule mining ---
"%PY%" code\44_association_rules.py || goto failed
echo --- [21] Machine learning models ---
"%PY%" code\45_ml_models.py || goto failed
echo --- [22] SHAP interpretation ---
"%PY%" code\46_shap.py || goto failed
echo --- [23] Cross validation ---
"%PY%" code\47_cross_validate.py || goto failed
echo --- [24] Sandbox thresholds ---
"%PY%" code\48_sandbox_thresholds.py || goto failed
echo --- [25] Sensitivity and intermediate conditions (Table 4) ---
"%PY%" code\66_sensitivity.py || goto failed
echo --- [26] Sensitivity addon (rescue capacity; branch-B sweep) ---
"%PY%" code\67_sensitivity_addon.py || goto failed
goto success

:full_llm
cls
echo ============================================================
echo  [NOTE] This makes real DeepSeek / Qwen API calls and costs money.
echo  It runs the offline pipeline, then real-LLM spot checks.
echo ============================================================
set "ok="
set /p ok=Type yes and press Enter to continue:
if /i not "%ok%"=="yes" goto menu
call :full || goto failed
echo --- [Extra 1] Real LLM spot check ---
"%PY%" code\41_llm_spotcheck.py || goto failed
echo --- [Extra 2] Qwen agent replication ---
"%PY%" code\50_qwen_replicate.py --k 16 || goto failed
goto success

:success
echo.
echo ============================================================
echo  [DONE] All steps completed.
echo  Figures in results\figures ; data tables in results\runs
echo ============================================================
goto donemenu

:failed
echo.
echo ============================================================
echo  [ABORT] A step failed. Check the messages above.
echo  Common causes: missing dependencies (pip install -r requirements.txt),
echo  API key/network issues for LLM steps.
echo ============================================================

:donemenu
echo.
set "back="
set /p back=Type r to return to the menu, 0 to exit:
if "%back%"=="r" goto menu
if "%back%"=="0" goto end
goto donemenu

:end
endlocal
exit /b 0
