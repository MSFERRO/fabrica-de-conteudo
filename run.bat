@echo off
echo ============================================================
echo   INICIALIZANDO A FÁBRICA DE CONTEÚDO AUTOMATIZADO...
echo ============================================================
echo.

if not exist "venv\" (
    echo [ERRO] Ambiente virtual venv nao encontrado. Rode install.bat primeiro!
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python src/main.py
pause
