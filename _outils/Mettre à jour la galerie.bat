@echo off
chcp 65001 > NUL
title Mise a jour de la galerie Cachanax
where python > NUL 2> NUL
if %errorlevel%==0 (python "%~dp0mettre_a_jour_galerie.py" %*) else (py "%~dp0mettre_a_jour_galerie.py" %*)
