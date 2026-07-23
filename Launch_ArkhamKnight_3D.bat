@echo off
REM Launch Batman: Arkham Knight with geo-11 via 3DMigoto Loader.
REM Prefer this over Steam alone on modern AMD/NVIDIA drivers (avoids AppHang).
set "WIN64=D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64"
if not exist "%WIN64%\3DMigoto Loader.exe" (
  echo ERROR: 3DMigoto Loader.exe not found in:
  echo   %WIN64%
  echo Install the HelixMod geo-11 fix + loader first. See README.md
  pause
  exit /b 1
)
cd /d "%WIN64%"
echo Launching Arkham Knight via 3DMigoto Loader (SBS geo-11)...
start "" "%WIN64%\3DMigoto Loader.exe"
