@echo off
cd /d "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64"
echo Arkham geo-11 HALF-SBS packer ON (upscaling=1 + upscale.ini)
echo No dxgi (Fatal on this AMD). Projector: Half SBS. Ctrl+F1 / F3-F6.
set "STEAM=C:\Program Files (x86)\Steam\steam.exe"
if exist "%STEAM%" ("%STEAM%" -applaunch 208650) else (start "" steam://rungameid/208650)
exit /b 0