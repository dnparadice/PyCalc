""" high DPI support, kept in its own module so main.py can call it before the (slow) UI import """
import sys


def enable():
    """ tells Windows that this process draws at the real resolution of the display. Without this, Windows draws the
    window at 96 DPI and stretches the picture on a scaled display (125%, 150%, ...), which makes all the text soft.

    Call before the first Tk window is created, later calls have no effect. Does nothing on macOS and Linux, they
    scale the window without help.
    """
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 1 = system DPI aware, Windows 8.1 and later
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()  # older Windows
    except Exception:
        pass  # the window still works, it is only drawn stretched
