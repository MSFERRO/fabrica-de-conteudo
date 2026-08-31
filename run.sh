#!/bin/bash

echo "============================================================"
echo "  INICIALIZANDO A FÁBRICA DE CONTEÚDO AUTOMATIZADO..."
echo "============================================================"
echo ""

if [ ! -d "venv" ]; then
    echo "[ERRO] Ambiente virtual venv não encontrado. Rode ./install.sh primeiro!"
    exit 1
fi

source venv/bin/activate
python3 src/main.py
