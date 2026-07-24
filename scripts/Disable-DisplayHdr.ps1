# Force Windows display HDR OFF. Use -WatchSeconds to keep killing HDR while Batman runs
# (exclusive fullscreen / swap-chain often re-enables it).
param(
  [int]$WatchSeconds = 0
)
$ErrorActionPreference = 'Continue'

$src = @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class HdrOff {
  const uint QDC_ONLY_ACTIVE_PATHS = 2;
  const int GET_ADVANCED_COLOR_INFO = 9;
  const int SET_ADVANCED_COLOR_STATE = 10;
  const int SET_HDR_STATE = 16;

  [StructLayout(LayoutKind.Sequential)] public struct LUID { public uint LowPart; public int HighPart; }
  [StructLayout(LayoutKind.Sequential)] public struct RATIONAL { public uint Numerator; public uint Denominator; }
  [StructLayout(LayoutKind.Sequential)]
  public struct HEADER { public int type; public int size; public LUID adapterId; public uint id; }
  [StructLayout(LayoutKind.Sequential)]
  public struct GET_COLOR {
    public HEADER header; public uint value; public uint colorEncoding; public uint bitsPerColorChannel;
  }
  [StructLayout(LayoutKind.Sequential)]
  public struct SET_COLOR { public HEADER header; public uint value; }
  [StructLayout(LayoutKind.Sequential)]
  public struct PATH_SOURCE { public LUID adapterId; public uint id; public uint modeInfoIdx; public uint statusFlags; }
  [StructLayout(LayoutKind.Sequential)]
  public struct PATH_TARGET {
    public LUID adapterId; public uint id; public uint modeInfoIdx;
    public uint outputTechnology; public uint rotation; public uint scaling;
    public RATIONAL refreshRate; public uint scanLineOrdering;
    public bool targetAvailable; public uint statusFlags;
  }
  [StructLayout(LayoutKind.Sequential)]
  public struct PATH { public PATH_SOURCE sourceInfo; public PATH_TARGET targetInfo; public uint flags; }
  [StructLayout(LayoutKind.Sequential, Size = 64)]
  public struct MODE { public uint infoType; public uint id; public LUID adapterId; }

  [DllImport("user32.dll")] static extern int GetDisplayConfigBufferSizes(uint flags, out uint nPath, out uint nMode);
  [DllImport("user32.dll")] static extern int QueryDisplayConfig(uint flags, ref uint nPath, [In, Out] PATH[] paths, ref uint nMode, [In, Out] MODE[] modes, IntPtr topology);
  [DllImport("user32.dll")] static extern int DisplayConfigGetDeviceInfo(ref GET_COLOR packet);
  [DllImport("user32.dll")] static extern int DisplayConfigSetDeviceInfo(ref SET_COLOR packet);

  public static string DisableAll() {
    uint nPath, nMode;
    int rc = GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, out nPath, out nMode);
    if (rc != 0) return "GetDisplayConfigBufferSizes rc=" + rc;
    var paths = new PATH[nPath];
    var modes = new MODE[Math.Max(nMode, 1)];
    rc = QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS, ref nPath, paths, ref nMode, modes, IntPtr.Zero);
    if (rc != 0) return "QueryDisplayConfig rc=" + rc;

    int off = 0, already = 0, skip = 0;
    var sb = new StringBuilder();
    for (int i = 0; i < nPath; i++) {
      var get = new GET_COLOR();
      get.header.type = GET_ADVANCED_COLOR_INFO;
      get.header.size = Marshal.SizeOf(typeof(GET_COLOR));
      get.header.adapterId = paths[i].targetInfo.adapterId;
      get.header.id = paths[i].targetInfo.id;
      rc = DisplayConfigGetDeviceInfo(ref get);
      if (rc != 0) { skip++; continue; }
      bool supported = (get.value & 1) != 0;
      bool enabled = (get.value & 2) != 0;
      if (!supported) { skip++; continue; }
      if (!enabled) { already++; continue; }

      var set = new SET_COLOR();
      set.header.type = SET_ADVANCED_COLOR_STATE;
      set.header.size = Marshal.SizeOf(typeof(SET_COLOR));
      set.header.adapterId = paths[i].targetInfo.adapterId;
      set.header.id = paths[i].targetInfo.id;
      set.value = 0;
      int rc1 = DisplayConfigSetDeviceInfo(ref set);

      var set2 = new SET_COLOR();
      set2.header.type = SET_HDR_STATE;
      set2.header.size = Marshal.SizeOf(typeof(SET_COLOR));
      set2.header.adapterId = paths[i].targetInfo.adapterId;
      set2.header.id = paths[i].targetInfo.id;
      set2.value = 0;
      int rc2 = DisplayConfigSetDeviceInfo(ref set2);

      sb.AppendFormat("path{0}: forcedOff advanced={1} hdr={2}; ", i, rc1, rc2);
      if (rc1 == 0 || rc2 == 0) off++; else skip++;
    }
    if (sb.Length == 0) return "HDR already off on active displays (supported paths checked). alreadyOff=" + already + " skipped=" + skip;
    return sb.ToString() + "turnedOff=" + off + " alreadyOff=" + already;
  }
}
'@

if (-not ('HdrOff' -as [type])) { Add-Type -TypeDefinition $src -Language CSharp }

function Lock-AutoHdrOff {
  $exe = 'D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64\BatmanAK.exe'
  Set-ItemProperty 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -Name $exe -Value 'GpuPreference=2;AutoHDREnable=0;AppStatus=0;' -Type String -Force -EA SilentlyContinue
  Set-ItemProperty 'HKCU:\Software\Microsoft\DirectX\GraphicsSettings' -Name AutoHDROptOutApplicable -Value 1 -Type DWord -Force -EA SilentlyContinue
}

Lock-AutoHdrOff
Write-Host ([HdrOff]::DisableAll())

if ($WatchSeconds -gt 0) {
  Write-Host "Watching $($WatchSeconds)s - will force HDR off if the game re-enables it..."
  $deadline = (Get-Date).AddSeconds($WatchSeconds)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    Lock-AutoHdrOff
    $msg = [HdrOff]::DisableAll()
    if ($msg -match 'forcedOff|turnedOff=[1-9]') { Write-Host "$(Get-Date -Format HH:mm:ss) $msg" }
    # keep watching a bit after process appears; stop early if process exited after having started
    $p = Get-Process BatmanAK -EA SilentlyContinue
    if ($script:sawGame -and -not $p) { break }
    if ($p) { $script:sawGame = $true }
  }
  Write-Host "HDR watch done."
}
