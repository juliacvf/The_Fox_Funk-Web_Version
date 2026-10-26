@echo off
setlocal
cd /d "%~dp0"
set "FOX_PYTHON="
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "FOX_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not defined FOX_PYTHON for %%P in (python.exe) do set "FOX_PYTHON=%%~$PATH:P"
if not defined FOX_PYTHON (
    echo Instale o Python 3 para iniciar o servidor local.
    pause
    exit /b 1
)
if not exist "index.html" (
    echo A versao web ainda precisa ser gerada. Veja o README.
    pause
    exit /b 1
)
echo The Fox Funk - abra http://127.0.0.1:8000
echo Mantenha esta janela aberta enquanto joga.
start "" /b "%FOX_PYTHON%" -c "import time, webbrowser; time.sleep(1); webbrowser.open('http://127.0.0.1:8000')"
"%FOX_PYTHON%" -m http.server 8000 --bind 127.0.0.1 --directory .
pause
