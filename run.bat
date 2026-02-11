@echo off
setlocal
:: 한글 인코딩 문제 해결 (UTF-8)
chcp 65001 >nul
title 대한민국 근로기준법 상담 챗봇 (Minu Style)

echo ======================================================
echo   대한민국 근로기준법 상담 챗봇 (Wage Arrears MVP)
echo   [미누(Minu) 방식 설계 적용됨]
echo ======================================================

:: 1. .env 파일 확인
if not exist ".env" (
    echo [ERROR] .env 파일이 존재하지 않습니다. 
    echo OPENAI_API_KEY가 포함된 .env 파일을 먼저 생성해주세요.
    pause
    exit /b 1
)

:: 2. 필수 패키지 설치 확인 (선택 사항)
echo [1/2] 필수 패키지 설치 확인 중...
pip install -r requirements.txt --quiet

:: 3. 챗봇 실행
echo [2/2] 챗봇을 시작합니다...
echo ------------------------------------------------------
python -m app.main

pause
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 챗봇 실행 중 오류가 발생했습니다.
    pause
)

endlocal
