@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ========================================================
echo   Lancement Automatique de LogAI - Ollama + Gemini + Web
echo ========================================================
echo.

:: 1. gestion IA local
where ollama >nul 2>nul
if ERRORLEVEL 1 (
    echo [INFO] Ollama introuvable. Installation en cours...
    powershell -Command "irm https://ollama.com/install.ps1 | iex"
) else (
    echo [OK] Ollama est installe.
)

echo [INFO] Demarrage du service Ollama en arriere-plan...
start /B ollama serve >nul 2>nul
timeout /t 3 /nobreak >nul

echo [INFO] Verification du modele qwen2.5:3b...
ollama list | findstr "qwen2.5:3b" >nul
if ERRORLEVEL 1 (
    echo [INFO] Telechargement du modele - cela peut prendre quelques minutes...
    ollama pull qwen2.5:3b
) else (
    echo [OK] Modele qwen2.5:3b operationnel.
)

:: 2. Cle Gemini
echo.
if not exist .env (
    echo [ATTENTION] Aucune cle API Gemini detectee.
    set /p apikey="Veuillez coller votre cle API Gemini : "
    echo GEMINI_API_KEY=!apikey!> .env
    echo [OK] Fichier .env genere avec succes.
) else (
    echo [OK] Fichier .env detecte - Cle Gemini prete.
)

:: 3. Docker app.py
echo.
echo [INFO] Verification de Docker...
where docker >nul 2>nul
if ERRORLEVEL 1 (
    echo [ERREUR] Docker n'est pas installe ou n'est pas lance sur ce PC.
    echo Veuillez installer et lancer Docker Desktop pour continuer.
    pause
    exit /b
)

echo [INFO] Construction de l'environnement LogAI...
docker build -t logai-app .

echo [INFO] Lancement du serveur Web...
:: enlevement de l'ancien container
docker rm -f logai-container >nul 2>nul
docker run -d --name logai-container --env-file .env -p 5000:5000 logai-app

echo.
echo ========================================================
echo   SUCCES ! Le systeme est completement operationnel.
echo   Ouvrez votre navigateur sur : http://localhost:5000
echo ========================================================
pause