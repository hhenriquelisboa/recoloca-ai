#!/usr/bin/env bash
# Launcher Unix/Linux/Mac para Recoloca-AI
# Uso: ./recoloca.sh [search|chat]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ $# -eq 0 ]]; then
    echo ""
    echo "  Recoloca-AI | Gilbert, o Sátiro Bardo Maestro"
    echo ""
    echo "  Uso: ./recoloca.sh [search|chat]"
    echo ""
    echo "    search  - Busca direta de vagas (usa perfil salvo)"
    echo "    chat    - Modo interativo: quiz + menu teatral"
    echo ""
    exit 1
fi

python3 gilbert.py "$1"