import ctypes, sys
from ctypes import wintypes
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

def find_hwnd(pid, min_w=800, min_h=450):
    cands = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid or not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(max(1, length + 1))
        if length:
            user32.GetWindowTextW(hwnd, buf, len(buf))
        title = buf.value
        r = RECT(); user32.GetClientRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w < min_w or h < min_h:
            return True
        score = w * h
        if 'Arkham' in title or 'Batman' in title or score > 500000:
            cands.append((score, hwnd, title, w, h))
        return True
    user32.EnumWindows(cb, 0)
    if not cands:
        raise SystemExit(f'no large hwnd for {pid}')
    score, hwnd, title, w, h = max(cands)
    print(f'hwnd={hwnd} {w}x{h} {title!r}', flush=True)
    return hwnd, w, h

out, pid = sys.argv[1], int(sys.argv[2])
hwnd, w, h = find_hwnd(pid)
hdc_win = user32.GetDC(hwnd)
hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
gdi32.SelectObject(hdc_mem, hbmp)
user32.PrintWindow(hwnd, hdc_mem, 2)

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]
bih = BITMAPINFOHEADER(); bih.biSize=ctypes.sizeof(BITMAPINFOHEADER); bih.biWidth=w; bih.biHeight=-h; bih.biPlanes=1; bih.biBitCount=32; bih.biCompression=0
buf = (ctypes.c_char * (w*h*4))()
gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bih), 0)
img = Image.frombuffer('RGB', (w, h), bytes(buf), 'raw', 'BGRX', 0, 1)
img.save(out)
print(f'Saved {w}x{h}: {out}', flush=True)
user32.ReleaseDC(hwnd, hdc_win); gdi32.DeleteObject(hbmp); gdi32.DeleteDC(hdc_mem)
