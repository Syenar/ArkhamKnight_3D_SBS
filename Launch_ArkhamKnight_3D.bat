@echo off
cd /d "D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64"
echo Arkham Knight 3D - stable geo-11 baseline
echo Projector: set SBS after packing is proven
if not exist "d3d11.dll" (echo ERROR missing d3d11.dll & pause & exit /b 1)
set "STEAM=C:\Program Files (x86)\Steam\steam.exe"
if exist "3DMigoto Loader.exe" if exist "%STEAM%" (
  tasklist /FI "IMAGENAME eq steam.exe" | find /I "steam.exe" >nul || start "" "%STEAM%"
  timeout /t 2 /nobreak >nul
  start "" /wait "3DMigoto Loader.exe"
  exit /b 0
)
if exist "%STEAM%" (
  "%STEAM%" -applaunch 208650
) else (
  start "" steam://rungameid/208650
)
exit /b 0