$log = "C:\Users\samsa\Desktop\Workplace\Projects\Arkham 3D Projects\Arkham Knight 3D\crash_dumps\message_killer.log"
"$(Get-Date -Format o) killer start pid=$PID" | Set-Content $log
Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class WinMsg {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc c, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  public static string Dump(IntPtr hwnd) {
    var sb = new StringBuilder(4096);
    EnumChildWindows(hwnd, (h,l) => {
      var t = new StringBuilder(1024); var c = new StringBuilder(256);
      GetWindowText(h, t, 1024); GetClassName(h, c, 256);
      if (t.Length > 0) sb.AppendLine(c + ": " + t);
      return true;
    }, IntPtr.Zero);
    return sb.ToString();
  }
}
"@
while ($true) {
  try {
    Get-Process | Where-Object { $_.MainWindowTitle -eq "Message" } | ForEach-Object {
      $txt = ""
      try { $txt = [WinMsg]::Dump($_.MainWindowHandle) } catch { $txt = $_.Exception.Message }
      "$(Get-Date -Format o) KILL Message pid=$($_.Id) proc=$($_.ProcessName)`n$txt" | Add-Content $log
      Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
      Get-Process BatmanAK -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    }
  } catch {}
  Start-Sleep -Milliseconds 250
}
