import ctypes, random, string

from mozart.win32.api import (getModuleFilename, wstring, shell32, user32, kernel32, WindowProc,
    KeyboardProc, WNDCLASSEX, NOTIFYICONDATA, MSG, LPKBDLLHOOKSTRUCT, Win32Error, MENUITEMINFO,
    POINT, TimerProc)
from mozart.win32.constants import *


class Resource(object):
    """
    Abstract base class for a Windows resource.
    """
    def __init__(self, handle):
        self.handle = handle
        self.setUp()

    def setUp(self):
        """
        Prepare the resource.
        """

    def tearDown(self):
        """
        Cleanup any resource information.
        """


class Timer(Resource):
    """
    Windows timer resource.
    """
    def __init__(self, interval, callback):
        """
        Initialise the timer.

        @type interval: C{int}
        @param interval: The time, in milliseconds, between callbacks

        @type callback: C{callable}
        @param callback: The callback to fire, with no parameters, when
            C{interval} elapses
        """
        self.interval = interval
        self.callback = callback
        super(Timer, self).__init__(handle=None)

    def setUp(self):
        def _procstub(hwnd, msg, identifier, time):
            self.callback()

        self._proc = TimerProc(_procstub)
        self.reset()

    def tearDown(self):
        user32.KillTimer(None, self.handle)

    def reset(self, interval=None):
        """
        Reset the timer and trigger again C{interval} milliseconds later.

        If C{interval} is C{None} then the interval value passed to C{__init__}
        will be used instead.
        """
        if interval is None:
            interval = self.interval
        self.handle = user32.SetTimer(None, self.handle or 0, interval, self._proc)


def _menuItem(identifier):
    mii = MENUITEMINFO()
    mii.cbSize = ctypes.sizeof(MENUITEMINFO)
    mii.wID = identifier
    return mii


class MenuItem(object):
    """
    Encapsulation of a menu item and its state.

    @type mii: C{MENUITEMINFO}
    @ivar mii: Win32 menu item structure

    @type parent: L{Menu}
    @ivar parent: Reference to the parent menu of this item
    """
    def __init__(self, mii):
        self.mii = mii
        self.parent = None

    def _setItemInfo(self):
        if user32.SetMenuItemInfoW(self.parent.handle, self.mii.wID, False, ctypes.addressof(self.mii)) == 0:
            raise Win32Error(u'Unable to set menu item info')

    @classmethod
    def fromString(cls, identifier, text):
        """
        Create a string menu item.

        @type identifier: C{int}
        @param identifier: A menu item identifier

        @type text: C{string}
        @param text: The menu item's text

        @rtype: L{MenuItem}
        @return: The newly constructed menu item
        """
        mii = _menuItem(identifier)
        mii.fMask = MIIM_FTYPE | MIIM_STRING | MIIM_ID
        mii.fType = MFT_STRING
        mii.wID = identifier
        mii.dwTypeData = wstring(text)
        return MenuItem(mii)

    @property
    def checked(self):
        """
        Determine whether or not the menu item is checked.
        """
        return bool(self.mii.fState & MFS_CHECKED)

    def check(self):
        """
        Check the menu item.
        """
        self.mii.fMask |= MIIM_CHECKMARKS | MIIM_STATE
        self.mii.fState &= ~MFS_UNCHECKED
        self.mii.fState |= MFS_CHECKED
        self._setItemInfo()

    def uncheck(self):
        """
        Uncheck the menu item.
        """
        self.mii.fMask |= MIIM_CHECKMARKS | MIIM_STATE
        self.mii.fState &= ~MFS_CHECKED
        self.mii.fState |= MFS_UNCHECKED
        self._setItemInfo()


class Menu(Resource):
    """
    Encapsulation of a menu.

    @type items: C{dict} mapping C{int}s to L{MenuItem}s
    @ivar items: A map of menu item identifiers to MenuItems
    """
    @classmethod
    def popupMenu(cls):
        return Menu(handle=user32.CreatePopupMenu())

    def setUp(self):
        self.items = {}

    def tearDown(self):
        user32.DestroyMenu(self.handle)

    def insertMenuItem(self, item, itemBefore):
        """
        Insert a menu item into a menu.

        @type item: L{MenuItem}
        @param item: The menu item to insert

        @type itemBefore: L{MenuItem} or C{None}
        @param itemBefore: The menu item to insert the new item before or
            C{None} to append the item
        """
        if itemBefore is None:
            beforeID = -1
        else:
            beforeID = itemBefore.mii.wID

        if user32.InsertMenuItemW(self.handle, beforeID, False, ctypes.addressof(item.mii)) == 0:
            raise Win32Error(u'Could not insert menu item')

        item.parent = self
        self.items[item.mii.wID] = item

    def appendMenuItem(self, item):
        """
        Append a menu item to a menu.
        """
        self.insertMenuItem(item, None)

    def trackPopup(self, window, pos=None):
        """
        Pop-up a menu as a context menu.

        @type window: L{Window}
        @param window: The window to which the menu should belong

        @type pos: L{(int, int)} or C{None}
        @param: The C{x} and C{y} mouse coordinates where the menu should
            appear or C{None} to use the mouse cursor's position
        """
        if pos is None:
            pt = POINT()
            if user32.GetCursorPos(ctypes.addressof(pt)) == 0:
                raise Win32Error(u'Could not get cursor position')
            pos = pt.x, pt.y

        x, y = pos
        user32.SetForegroundWindow(window.handle)
        user32.TrackPopupMenu(self.handle, TPM_RIGHTALIGN | TPM_BOTTOMALIGN | TPM_RIGHTBUTTON, x, y, 0, window.handle, None)
        user32.PostMessageW(window.handle, WM_NULL, 0, 0)


class Icon(Resource):
    """
    Encapsulate an HICON handle.
    """
    def __init__(self, shared=False, **kw):
        """
        @type shared: C{bool}
        @param shared: Flag indicating whether this is a shared icon or not;
            shared icons are not destroyed when L{tearDown} is called
        """
        super(Icon, self).__init__(**kw)
        self.shared = shared

    @classmethod
    def fromSystem(cls, identifier, useSystemMetrics=False, size=None):
        """
        Construct an icon from a system icon identifier.
        """
        flags = LR_SHARED
        if useSystemMetrics:
            flags |= LR_DEFAULTSIZE
        if size is None:
            size = 0, 0
        w, h = size

        handle = user32.LoadImageW(None, identifier, IMAGE_ICON, w, h, flags)
        if handle is None:
            raise Win32Error(u'Unable to load system icon with identifier "%d"' % (identifier,))
        return Icon(shared=True, handle=handle)

    @classmethod
    def fromFile(cls, path, size=None):
        """
        Construct an icon from a file resource.
        """
        if size is None:
            size = 0, 0
        w, h, = size

        handle = user32.LoadImageW(None, path, IMAGE_ICON, w, h, LR_LOADFROMFILE)
        if handle is None:
            raise Win32Error(u'Unable to load icon from "%s"' % (path,))
        return Icon(handle=handle)

    @classmethod
    def fromLibrary(cls, path, iconIndex):
        """
        Construct an icon from an index within an icon library.
        """
        handle = shell32.ExtractIconW(None, path, iconIndex)
        if handle is None or handle == 1:
            raise Win32Error(u'Unable to load icon from "%s" at index %d' % (path, iconIndex))
        return Icon(handle=handle)

    def tearDown(self):
        if not self.shared:
            user32.DestroyIcon(self.handle)


class NotifyIcon(object):
    """
    Encapsulation of a notification area icon.
    """
    def __init__(self, window, messageID, icon, tooltip, notifyID=0):
        self.window = window
        self.icon = icon
        self.tooltip = tooltip
        self.messageID = messageID
        self.notifyID = notifyID

        self.setUp()

    def _notifyData(self):
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self.window.handle
        nid.uID = self.notifyID
        return nid

    def setIcon(self, icon):
        nid = self._notifyData()
        nid.uFlags = NIF_ICON
        nid.hIcon = icon.handle
        if shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.addressof(nid)) == 0:
            raise Win32Error(u'Failed to set notification icon')

        self.icon = icon

    def setUp(self):
        nid = self._notifyData()
        nid.uFlags = NIF_TIP | NIF_ICON | NIF_MESSAGE
        nid.hIcon = self.icon.handle
        maxTooltip = dict(NOTIFYICONDATA._fields_)['szTip']._length_
        nid.szTip = self.tooltip[:maxTooltip]
        nid.uCallbackMessage = self.messageID

        if shell32.Shell_NotifyIconW(NIM_ADD, ctypes.addressof(nid)) == 0:
            raise Win32Error(u'Failed to create notification item')

    def tearDown(self):
        nid = self._notifyData()
        if shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.addressof(nid)) == 0:
            raise Win32Error(u'Failed to delete notification icon')


class KeyboardHook(object):
    def __init__(self, hook):
        self.hook = hook
        self.setUp()

    def hookproc(self, nCode, wParam, lParam):
        """
        Hook procedure stub.

        Dispatch hook calls to L{hook.proc}, if it returns a true-value then
        no more hooks of this kind are called.
        """
        hookStruct = ctypes.cast(lParam, LPKBDLLHOOKSTRUCT).contents
        # According to the MSDN, if nCode is less than zero then we should
        # just call the next hook without any further processing.
        if nCode < 0:
            return user32.CallNextHookEx(self.hookHandle, nCode, wParam, lParam)

        # If our hook procedure returns True then we've processed the
        # message and nobody else should see it.
        if self.hook.proc(hookStruct):
            return True

        return user32.CallNextHookEx(self.hookHandle, nCode, wParam, lParam)

    def setUp(self):
        # We hang on to this so that it doesn't get garbage collected.
        self._internalProc = KeyboardProc(self.hookproc)

        moduleHandle = kernel32.GetModuleHandleW(getModuleFilename())
        self.hookHandle = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._internalProc, moduleHandle, 0)

    def tearDown(self):
        user32.UnhookWindowsHookEx(self.hookHandle)


class Hook(object):
    """
    Abstract base class for Windows hook callback handlers.
    """
    def proc(self, *a, **kw):
        """
        Hook procedure handler.
        """
        raise NotImplementedError('Subclasses must define a procedure handler')


class Window(object):
    def __init__(self, title, (x, y, width, height), parent=None):
        self.title = title
        self.pos = x, y
        self.size = width, height

        if parent is not None:
            if issubclass(type(parent), Window):
                parent = parent.handle

        self.parent = parent

        self.setUp()

    def _registerWindowClass(self):
        """
        Register the window class.
        """
        # Store a copy of this so that it doesn't get garbage collected.
        self._windowProc = WindowProc(self.proc)

        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.lpfnWndProc = self._windowProc
        wc.hInstance = self.hInstance
        wc.lpszClassName = wstring(self.windowClassName)

        classAtom = user32.RegisterClassExW(ctypes.addressof(wc))
        if classAtom == 0:
            raise Win32Error(u'Failed to register window class')

        return classAtom

    def _createWindow(self):
        """
        Create the window.
        """
        hwnd = user32.CreateWindowExW(
            0, self.windowClassName, self.title, WS_OVERLAPPEDWINDOW,
            self.pos[0], self.pos[1], self.size[0], self.size[1],
            self.parent, None, self.hInstance, None)
        if hwnd == None:
            raise Win32Error(u'Failed to create window')

        return hwnd

    def setUp(self):
        # Generate a random window class name, hopefully nothing else has the
        # same one.
        self.windowClassName = u''.join(random.sample(string.letters, 16))
        self.hInstance = kernel32.GetModuleHandleW(None)

        self.classAtom = self._registerWindowClass()
        self.handle = self._createWindow()

    def tearDown(self):
        user32.DestroyWindow(self.handle)
        user32.UnregisterClassW(self.windowClassName, self.hInstance)

    def proc(self, hwnd, msg, wParam, lParam):
        """
        Window procedure handler.

        Messages are passed to L{handleMessage} for handling, if
        L{DefaultProcedure} (the type) is returned then the default
        window handler is invoked.  Otherwise the return value from
        C{handleMessage} is returned.
        """
        rv = self.handleMessage(hwnd, msg, wParam, lParam)
        if rv is DefaultProcedure:
            return user32.DefWindowProcW(hwnd, msg, wParam, lParam)
        return rv

    def handleMessage(self, hwnd, msg, wParam, lParam):
        """
        Handle window messages.
        """
        return DefaultProcedure


class DefaultProcedure(object):
    """
    A special object, usually returned from L{Window.handleMessage}, indicating
    that the default window procedure should be called and its return value
    used.
    """


class MessageOnlyWindow(Window):
    """
    A window that has no visible user interface.
    """
    def __init__(self):
        super(MessageOnlyWindow, self).__init__(None, (0, 0, 0, 0), parent=HWND_MESSAGE)


class Application(object):
    """
    The primary message pumper and runner of things.
    """
    def __init__(self, window):
        self.window = window
        # XXX: hmmm
        self.window.application = self

        self.setUp()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def run(self):
        """
        Run the message loop.
        """
        msg = MSG()
        handle = None

        while True:
            rv = user32.GetMessageW(ctypes.addressof(msg), handle, 0, 0)
            if rv == 0:
                break
            elif rv == -1:
                raise Win32Error(u'Message loop error')

            user32.TranslateMessage(ctypes.addressof(msg))
            user32.DispatchMessageW(ctypes.addressof(msg))

        self.tearDown()

    def quit(self, returnValue=0):
        """
        Post a quit message to the message queue.
        """
        user32.PostQuitMessage(returnValue)


__all__ = [
    'Icon', 'NotifyIcon', 'KeyboardHook', 'Hook', 'Window', 'MessageOnlyWindow',
    'Application', 'DefaultProcedure', 'MenuItem', 'Menu', 'Timer',
    ]
