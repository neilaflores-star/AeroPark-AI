@echo off
title AeroPark AI - Servidor Backend
cd /d "%~dp0"
echo ====================================================
echo   Iniciando Servidor Backend de AeroPark AI
echo ====================================================
echo.

set PYTHON_PATH="C:\Users\Nacho\AppData\Local\Programs\Python\Python312\python.exe"
set PYTHON_PATH2="C:\Users\nflores\AppData\Local\Programs\Python\Python312\python.exe"

if exist %PYTHON_PATH% (
    echo [INFO] Usando Python 3.12 desde %PYTHON_PATH%
    set PY=%PYTHON_PATH%
) else if exist %PYTHON_PATH2% (
    echo [INFO] Usando Python 3.12 desde %PYTHON_PATH2%
    set PY=%PYTHON_PATH2%
) else (
    echo [INFO] Usando 'python' del PATH del sistema.
    set PY=python
)


echo.
echo [1/2] Verificando e instalando dependencias (fastapi, uvicorn)...
%PY% -m pip install fastapi uvicorn
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] No se pudo ejecutar pip con %PY%. Asegurate de tener Python instalado.
    pause
    exit /b
)
echo.
echo [2/2] Iniciando servidor FastAPI con Uvicorn en http://127.0.0.1:8000 ...
echo (Presiona Ctrl+C para detener el servidor)
echo.
%PY% -m uvicorn backend.main:app --reload
pause
