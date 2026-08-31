#!/bin/bash

echo "============================================================"
echo "  INSTALADOR - FÁBRICA DE CONTEÚDO AUTOMATIZADO"
echo "============================================================"
echo ""

# Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python 3 não encontrado! Instale o Python 3.11+."
    exit 1
fi

echo "[1/3] Criando ambiente virtual (venv)..."
python3 -m venv venv

echo "[2/3] Instalando dependências..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/3] Configurando arquivo de variáveis (.env)..."
if [ ! -f "config/.env" ]; then
    cp config/.env.example config/.env
    echo "Arquivo config/.env criado!"
else
    echo "Arquivo config/.env já existe. Mantido."
fi

echo ""
echo "============================================================"
echo "  🎉 INSTALAÇÃO CONCLUÍDA!"
echo "============================================================"
echo "  Instruções:"
echo "  1. Preencha suas chaves no arquivo: config/.env"
echo "  2. Coloque as credenciais do YouTube (client_secrets.json) em config/"
echo "  3. Execute o script de autenticação do YouTube:"
echo "     python3 src/core/youtube_auth.py"
echo "  4. Execute a fábrica rodando: ./run.sh"
echo "============================================================"
echo ""
chmod +x run.sh 2>/dev/null || true
