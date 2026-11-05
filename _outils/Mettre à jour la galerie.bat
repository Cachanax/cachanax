@echo off
chcp 65001 > NUL
title Mise a jour de la galerie Cachanax
set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY312%" (
  echo Les outils ne sont pas installes.
  echo Lancez d'abord "Installer les outils.bat", dans ce meme dossier.
  pause
  exit /b 1
)
"%PY312%" "%~dp0mettre_a_jour_galerie.py" %*
if errorlevel 1 pause
