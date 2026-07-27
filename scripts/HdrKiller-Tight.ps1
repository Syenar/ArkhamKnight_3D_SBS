# Tight HDR killer - runs alongside game
$src = @'
using System; using System.Runtime.InteropServices;
public static class HdrKill {
  const uint QDC=2; const int GET=9; const int SET=10; const int SETHDR=16;
  [StructLayout(LayoutKind.Sequential)] public struct LUID { public uint LowPart; public int HighPart; }
  [StructLayout(LayoutKind.Sequential)] public struct RATIONAL { public uint Numerator; public uint Denominator; }
  [StructLayout(LayoutKind.Sequential)] public struct HEADER { public int type; public int size; public LUID adapterId; public uint id; }
  [StructLayout(LayoutKind.Sequential)] public struct GETC { public HEADER header; public uint value; public uint colorEncoding; public uint bitsPerColorChannel; }
  [StructLayout(LayoutKind.Sequential)] public struct SETC { public HEADER header; public uint value; }
  [StructLayout(LayoutKind.Sequential)] public struct PS { public LUID adapterId; public uint id; public uint modeInfoIdx; public uint statusFlags; }
  [StructLayout(LayoutKind.Sequential)] public struct PT { public LUID adapterId; public uint id; public uint modeInfoIdx; public uint outputTechnology; public uint rotation; public uint scaling; public RATIONAL refreshRate; public uint scanLineOrdering; public bool targetAvailable; public uint statusFlags; }
  [StructLayout(LayoutKind.Sequential)] public struct PATH { public PS sourceInfo; public PT targetInfo; public uint flags; }
  [StructLayout(LayoutKind.Sequential, Size=64)] public struct MODE { public uint infoType; public uint id; public LUID adapterId; }
  [DllImport("user32.dll")] static extern int GetDisplayConfigBufferSizes(uint f, out uint np, out uint nm);
  [DllImport("user32.dll")] static extern int QueryDisplayConfig(uint f, ref uint np, [In,Out] PATH[] p, ref uint nm, [In,Out] MODE[] m, IntPtr t);
  [DllImport("user32.dll")] static extern int DisplayConfigGetDeviceInfo(ref GETC packet);
  [DllImport("user32.dll")] static extern int DisplayConfigSetDeviceInfo(ref SETC packet);
  public static int Kill() {
    uint np,nm; GetDisplayConfigBufferSizes(QDC,out np,out nm);
    var paths=new PATH[np]; var modes=new MODE[Math.Max(nm,1)];
    QueryDisplayConfig(QDC,ref np,paths,ref nm,modes,IntPtr.Zero);
    int n=0;
    for(int i=0;i<np;i++){
      var g=new GETC(); g.header.type=GET; g.header.size=Marshal.SizeOf(typeof(GETC));
      g.header.adapterId=paths[i].targetInfo.adapterId; g.header.id=paths[i].targetInfo.id;
      if(DisplayConfigGetDeviceInfo(ref g)!=0) continue;
      if((g.value&2)==0) continue;
      var s=new SETC(); s.header.type=SET; s.header.size=Marshal.SizeOf(typeof(SETC));
      s.header.adapterId=g.header.adapterId; s.header.id=g.header.id; s.value=0;
      if(DisplayConfigSetDeviceInfo(ref s)!=0){ s.header.type=SETHDR; DisplayConfigSetDeviceInfo(ref s);}
      n++;
    }
    return n;
  }
}
'@
if (-not ('HdrKill' -as [type])) { Add-Type -TypeDefinition $src }
$exe = 'D:\SteamLibrary\steamapps\common\Batman Arkham Knight\Binaries\Win64\BatmanAK.exe'
Set-ItemProperty 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -Name $exe -Value 'GpuPreference=2;AutoHDREnable=0;AppStatus=0;' -Force -EA SilentlyContinue
$end = (Get-Date).AddMinutes(4)
$flips = 0
while ((Get-Date) -lt $end) {
  $n = [HdrKill]::Kill()
  if ($n -gt 0) { $flips++; Add-Content 'C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D\hdr_kill_log.txt' "$(Get-Date -Format HH:mm:ss) killed=$n totalFlips=$flips" }
  if (-not (Get-Process BatmanAK -EA SilentlyContinue)) {
    # wait for game to appear up to 45s, then exit if never starts / after exit
    Start-Sleep 1
    if ($flips -gt 0 -or ((Get-Date) -gt $end.AddMinutes(-3.5))) { 
      if (-not (Get-Process BatmanAK -EA SilentlyContinue)) {
        # if we already saw the game die, stop
        if ($script:saw) { break }
      }
    }
  } else { $script:saw = $true }
  Start-Sleep -Milliseconds 500
}
