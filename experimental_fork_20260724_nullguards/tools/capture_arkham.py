import ctypes
import sys
from ctypes import wintypes

from windows_capture import Frame, InternalCaptureControl, WindowsCapture


class Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def find_largest_process_window(target_pid: int) -> tuple[int, str, int, int]:
    windows: list[tuple[int, int, str, int, int]] = []
    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )

    @enum_proc_type
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        window_pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(
            hwnd, ctypes.byref(window_pid)
        )
        if window_pid.value != target_pid:
            return True

        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(max(1, length + 1))
        if length:
            ctypes.windll.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        rect = Rect()
        if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            width = max(0, rect.right - rect.left)
            height = max(0, rect.bottom - rect.top)
            windows.append((width * height, hwnd, buffer.value, width, height))
        return True

    ctypes.windll.user32.EnumWindows(enum_proc, 0)
    if not windows:
        raise RuntimeError(f"No windows found for PID {target_pid}")
    _, hwnd, title, width, height = max(windows)
    return hwnd, title, width, height


output = sys.argv[1]
pid = int(sys.argv[2])
hwnd, original_title, width, height = find_largest_process_window(pid)
print(
    f"Capturing largest Arkham window: {width}x{height} {original_title!r}",
    flush=True,
)

capture = WindowsCapture(
    cursor_capture=False,
    draw_border=False,
    monitor_index=None,
    window_name=None,
    window_hwnd=hwnd,
)


@capture.event
def on_frame_arrived(
    frame: Frame, capture_control: InternalCaptureControl
) -> None:
    frame.save_as_image(output)
    print(f"Saved {frame.width}x{frame.height}: {output}", flush=True)
    capture_control.stop()


@capture.event
def on_closed() -> None:
    print("Capture session closed", flush=True)


capture.start()
