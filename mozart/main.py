import codecs, re, unicodedata

from mozart.win32 import (constants, Application, KeyboardHook, NotifyIcon,
    MessageOnlyWindow, Icon, DefaultProcedure, Menu, MenuItem, Timer)
from mozart.hooks import ComposeHook


NOTIFY_MESSAGE = constants.WM_USER + 1

IDM_EXIT = 1
IDM_ENABLED = 2


def compositionsFromFile(path):
    """
    Construct a composition map from a file.

    The composition map file should contain a single composition mapping per
    line; lines should contain exactly 3 atoms; each atom should be a unicode
    character name.

    For example::
        <PLUS SIGN> <PLUS SIGN> <NUMBER SIGN>
        <LATIN CAPITAL LETTER A> <LATIN CAPITAL LETTER T> <COMMERCIAL AT>

    @type path: C{str} or C{unicode}
    @param path: Path to composition map

    @rtype: C{dict} mapping a C{2-tuple} to C{int}
    @return: A mapping of 2-tuples of ordinals for composition
        sequences to composition ordinals
    """
    pattern = re.compile(r'<(.*?)>')
    compositions = {}
    for i, line in enumerate(codecs.open(path, 'r', 'utf-8')):
        v = re.findall(pattern, line)
        if len(v) != 3:
            raise ValueError(u'Line %d of "%s": Expected 3 composition items, found %d' % (i, path, len(v)))

        a = ord(unicodedata.lookup(v[0]))
        b = ord(unicodedata.lookup(v[1]))
        r = ord(unicodedata.lookup(v[2]))
        compositions[(a, b)] = r

    return compositions


class MozartWindow(MessageOnlyWindow):
    def setUp(self):
        super(MozartWindow, self).setUp()

        self.menu = menu = Menu.popupMenu()
        menu.appendMenuItem(MenuItem.fromString(IDM_ENABLED, u'&Enabled'))
        menu.appendMenuItem(MenuItem.fromString(IDM_EXIT, u'E&xit'))

        menu.items[IDM_ENABLED].check()

    def tearDown(self):
        self.menu.tearDown()
        super(MozartWindow, self).tearDown()

    def handleMessage(self, hwnd, msg, wParam, lParam):
        if msg == NOTIFY_MESSAGE:
            if lParam in (constants.WM_RBUTTONDOWN, constants.WM_CONTEXTMENU):
                self.menu.trackPopup(self)
                return 0
        elif msg == constants.WM_COMMAND:
            # Low-word of wParam is the command identifier.
            identifier = wParam & 0xffff

            if identifier == IDM_EXIT:
                self.application.quit()
            elif identifier == IDM_ENABLED:
                mi = self.menu.items[IDM_ENABLED]
                if mi.checked:
                    mi.uncheck()
                    self.application.disable()
                else:
                    mi.check()
                    self.application.enable()
            return 0

        return DefaultProcedure


class MozartApplication(Application):
    IDLE_TIMEOUT = 2 * 1000

    def setUp(self):
        # XXX: don't hardcode this
        self.hotkey = constants.VK_RMENU
        self.compositionMap = compositionsFromFile(u'resources/Compose')
        self.notifyMessageID = NOTIFY_MESSAGE

        self.installHook()

        self.icons = {
            u'main':     Icon.fromFile(u'resources/mozart-notify-main.ico'),
            u'disabled': Icon.fromFile(u'resources/mozart-notify-disabled.ico'),
            u'waiting':  Icon.fromFile(u'resources/mozart-notify-waiting.ico')}
        tip = u'Mozart'
        self.notifyIcon = NotifyIcon(self.window, self.notifyMessageID, self.icons[u'main'], tip)
        self.idleTimer = None

    def tearDown(self):
        self.uninstallHook()
        self.notifyIcon.tearDown()
        for icon in self.icons.itervalues():
            icon.tearDown()

    def idleCallback(self):
        self.stopComposing()

    def hookCallback(self, state):
        print 'state', state
        if state == u'done':
            self.setIcon(u'main')
            if self.idleTimer is not None:
                self.idleTimer.tearDown()
        elif state == u'start':
            self.setIcon(u'waiting')
            self.idleTimer = Timer(self.IDLE_TIMEOUT, self.idleCallback)
        elif state == u'key':
            self.idleTimer.reset()
        else:
            raise ValueError(u'Unrecognized hook state: %r' % (state,))

    def setIcon(self, name):
        self.notifyIcon.setIcon(self.icons[name])

    def stopComposing(self):
        self.keyboardHook.hook.stopComposing()

    def disable(self):
        self.stopComposing()
        self.uninstallHook()
        self.setIcon(u'disabled')

    def enable(self):
        self.installHook()
        self.setIcon(u'main')

    def installHook(self):
        hook = ComposeHook(self.hotkey, self.compositionMap, self.hookCallback)
        self.keyboardHook = KeyboardHook(hook)

    def uninstallHook(self):
        if getattr(self, 'keyboardHook', None) is not None:
            self.keyboardHook.tearDown()
            self.keyboardHook = None
