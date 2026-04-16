@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: =====================================================
:: AIB 일일 뉴스 수집기 (Windows)
:: Kimi CLI를 통해 AI 뉴스 브리프를 자동 생성합니다.
:: =====================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: 옵션 파싱
set "WEEKLY="
set "PROMPT_ONLY="
set "NO_GIT="
set "AUTO="
set "DATE_ARG="

:parse_args
if "%~1"=="" goto :done_args
if /i "%~1"=="--weekly" set "WEEKLY=1"
if /i "%~1"=="--prompt-only" set "PROMPT_ONLY=1"
if /i "%~1"=="--no-git" set "NO_GIT=1"
if /i "%~1"=="--auto" set "AUTO=1"
if /i "%~1"=="--date" (
    set "DATE_ARG=%~2"
    shift
)
shift
goto :parse_args
:done_args

:: Python 확인
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python이 설치되어 있지 않습니다.
    echo   설치: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 옵션 조합
set "OPTS="
if defined WEEKLY set "OPTS=%OPTS% --weekly"
if defined PROMPT_ONLY set "OPTS=%OPTS% --prompt-only"
if defined NO_GIT set "OPTS=%OPTS% --no-git"
if defined AUTO set "OPTS=%OPTS% --auto"
if defined DATE_ARG set "OPTS=%OPTS% --date %DATE_ARG%"

:: Python 스크립트 실행
python "%SCRIPT_DIR%\ai-daily.py" %OPTS%

if not defined AUTO (
    echo.
    pause
)
