@echo off
cd /d "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64"
echo Arkham geo-11 STABLE baseline - Full SBS next after eye proof
echo No Helix / no dxgi / no nvapi - show_fps_monitor=false
set "STEAM=C:\Program Files (x86)\Steam\steam.exe"
if exist "%STEAM%" ("%STEAM%" -applaunch 208650) else (start "" steam://rungameid/208650)
exit /b 0