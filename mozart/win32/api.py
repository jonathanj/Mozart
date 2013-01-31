import ctypes

from mozart.win32.constants import *

### Libraries ###

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32


### Types ###

KeyboardProc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)
WindowProc = ctypes.WINFUNCTYPE(LRESULT, HANDLE, UINT, WPARAM, LPARAM)
TimerProc = ctypes.WINFUNCTYPE(None, HANDLE, UINT, UINT_PTR, DWORD)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [('vkCode',      DWORD),
                ('scanCode',    DWORD),
                ('flags',       DWORD),
                ('time',        DWORD),
                ('dwExtraInfo', ULONG_PTR)]

LPKBDLLHOOKSTRUCT = ctypes.POINTER(KBDLLHOOKSTRUCT)


class POINT(ctypes.Structure):
    _fields_ = [('x', LONG),
                ('y', LONG)]


class MSG(ctypes.Structure):
    _fields_ = [('hwnd',    HANDLE),
                ('message', UINT),
                ('wParam',  WPARAM),
                ('lParam',  LPARAM),
                ('time',    DWORD),
                ('pt',      POINT)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx',          LONG),
                ('dy',          LONG),
                ('mouseData',   DWORD),
                ('dwFlags',     DWORD),
                ('time',        DWORD),
                ('dwExtraInfo', ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk',         WORD),
                ('wScan',       WORD),
                ('dwFlags',     DWORD),
                ('time',        DWORD),
                ('dwExtraInfo', ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg',    DWORD),
                ('wParamL', WORD),
                ('wparamH', WORD)]


class _INPUTUnion(ctypes.Union):
    _fields_ = [('mi', MOUSEINPUT),
                ('ki', KEYBDINPUT),
                ('hi', HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [('type', DWORD),
                ('_input', _INPUTUnion)]
    _anonymous_ = ['_input']


class GUID(ctypes.Structure):
    _fields_ = [('Data1', ctypes.c_ulong),
                ('Data2', ctypes.c_ushort),
                ('Data3', ctypes.c_ushort),
                ('Data4', ctypes.c_byte)]


class _NOTIFYICONDATA_6Union(ctypes.Union):
    _fields_ = [('uTimeout', UINT),
                ('uVersion', UINT)]


class NOTIFYICONDATAW_6(ctypes.Structure):
    _fields_ = [('cbSize',           DWORD),
                ('hWnd',             HANDLE),
                ('uID',              UINT),
                ('uFlags',           UINT),
                ('uCallbackMessage', UINT),
                ('hIcon',            HANDLE),
                ('szTip',            WCHAR * 128),
                ('dwState',          DWORD),
                ('dwStateMask',      DWORD),
                ('szInfo',           WCHAR * 256),
                ('_union',           _NOTIFYICONDATA_6Union),
                ('szInfoTitle',      WCHAR * 64),
                ('dwInfoFlags',      DWORD),
                ('guidItem',         GUID),
                ('hBalloonIcon',     HANDLE)]
    _anonymous_ = ['_union']

NOTIFYICONDATA = NOTIFYICONDATAW_6


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [('cbSize', UINT),
                ('style', UINT),
                ('lpfnWndProc', WindowProc),
                ('cbClsExtra', ctypes.c_int),
                ('cbWndExtra', ctypes.c_int),
                ('hInstance', HANDLE),
                ('hIcon', HANDLE),
                ('hCursor', HANDLE),
                ('hbrBackground', HANDLE),
                ('lpszMenuName', LPWCHAR),
                ('lpszClassName', LPWCHAR),
                ('hIconSm', HANDLE)]

WNDCLASSEX = WNDCLASSEXW


class MENUITEMINFOW_5(ctypes.Structure):
    _fields_ = [('cbSize', UINT),
                ('fMask', UINT),
                ('fType', UINT),
                ('fState', UINT),
                ('wID', UINT),
                ('hSubMenu', HANDLE),
                ('hbmpChecked', HANDLE),
                ('hbmpUnchecked', HANDLE),
                ('dwItemData', DWORD),
                ('dwTypeData', LPWSTR),
                ('cch', UINT),
                ('hbmpItem', HANDLE)]

MENUITEMINFO = MENUITEMINFOW_5


### Wrappers ###

class Win32Error(WindowsError):
    def __init__(self, desc, errorCode=None):
        msg = ctypes.FormatError(errorCode).decode('ascii')
        WindowsError.__init__(self, (desc, msg))


def getModuleFilename(module=None):
    bufSize = MAX_PATH
    while True:
        buf = (WCHAR * bufSize)()
        numChars = kernel32.GetModuleFileNameW(module, buf, bufSize)
        if numChars == 0:
            errorCode = kernel32.GetLastError()
            if errorCode == ERROR_INSUFFICIENT_BUFFER:
                bufSize *= 2
                continue
            else:
                raise Win32Error(u'Could not get module filename', errorCode=errorCode)
        break

    return buf.value[:numChars]


wstring = ctypes.create_unicode_buffer
