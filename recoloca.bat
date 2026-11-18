@echo off
:: Launcher Windows para Recoloca-AI
:: Uso: recoloca.bat [search|chat]

cd /d "%~dp0"

if "%1"=="" (
    echo.
    echo  Recoloca-AI ^| Gilbert, o Sátiro Bardo Maestro
    echo.
    echo  Uso: recoloca.bat [search ^| chat]
    echo.
    echo    search  - Busca direta de vagas (usa perfil salvo)
    echo    chat    - Modo interativo: quiz + menu teatral
    echo.
    exit /b 1
)

python gilbert.py %1