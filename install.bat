@echo off
echo ============================================================
echo   INSTALADOR - FÁBRICA DE CONTEÚDO AUTOMATIZADO
echo ============================================================
echo.

:: Verifica se o Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado! Instale o Python 3.11+ e adicione ao PATH.
    pause
    exit /b 1
)

echo [1/3] Criando ambiente virtual (venv)...
python -m venv venv

echo [2/3] Instalando dependencias do requirements.txt...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] Configurando arquivo de variaveis de ambiente (.env)...
if not exist "config\.env" (
    copy "config\.env.example" "config\.env"
    echo Arquivo config/.env criado!
) else (
    echo Arquivo config/.env ja existe. Mantido sem alteracoes.
)

echo.
echo ============================================================
echo   🎉 INSTALAÇÃO CONCLUÍDA!
echo ============================================================
echo   Instrucoes:
echo   1. Preencha suas chaves no arquivo: config/.env
echo   2. Coloque as credenciais do YouTube (client_secrets.json) em config/
echo   3. Execute o script de autenticação do YouTube:
echo      python src/core/youtube_auth.py
echo   4. Execute a fabrica rodando o arquivo: run.bat
echo ============================================================
echo.
pause
