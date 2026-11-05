@echo off
chcp 65001 > NUL
cd /d "%~dp0"
title Installation des outils de la galerie Cachanax
set "PY312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY312%" goto outils
echo Installation de Python 3.12 (gratuit, quelques minutes)...
winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
if not exist "%PY312%" (
  echo.
  echo Python n'a pas pu etre installe automatiquement.
  echo Prevenez Claude en lui indiquant le message ci-dessus.
  pause
  exit /b 1
)
:outils
echo.
echo Installation des outils de retouche (environ 300 Mo)...
"%PY312%" -m pip install --upgrade pip
"%PY312%" -m pip install --upgrade pillow numpy opencv-python-headless onnxruntime rembg
if errorlevel 1 goto erreur
echo.
echo Telechargement du modele de detourage (environ 180 Mo)...
"%PY312%" -c "from rembg import new_session; new_session('isnet-general-use'); import retouche" 
if errorlevel 1 goto erreur
echo.
echo Installation terminee. Vous pouvez lancer "Mettre a jour la galerie".
pause
exit /b 0
:erreur
echo.
echo L'installation a echoue. Prevenez Claude en lui indiquant le message ci-dessus.
pause
exit /b 1
