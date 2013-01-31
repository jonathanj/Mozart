import ctypes

from mozart.win32.constants import (WCHAR, CHAR, LLKHF_UP, LLKHF_INJECTED,
    VK_LSHIFT, VK_RSHIFT, VK_SHIFT, VK_PACKET, VK_ESCAPE, INPUT_KEYBOARD,
    KEYEVENTF_UNICODE, KEYEVENTF_KEYUP)
from mozart.win32.api import INPUT, user32
from mozart.win32.hlapi import Hook


def isKeyDown(flags):
    return flags & LLKHF_UP == 0


def isKeyUp(flags):
    return not isKeyDown(flags)


class ComposeHook(Hook):
    """
    Keyboard hook to emulate a compose key.

    When the hotkey is pressed, the hook waits for two none-modifier key
    presses and consults C{compositions} to find the relevant compose
    sequence.  If a valid sequence is found then the composed character is
    emitted in the place of the compose sequence keys, otherwise a system beep
    is emitted.

    Nested compositions are supported, that is, pressing the hotkey while
    already in a composition sequence will result in a nested composition
    sequence, the output of which will be the input for the outer sequence.
    This can be useful for creating logical compositions that do not require
    that all the components appear on the user's keyboard.
    """
    def __init__(self, hotKey, compositions, callback=None):
        """
        Initialise the composition hook.

        Hook states are::

            C{start}::
                The compose sequence has been initiated.

            C{done}::
                The composition is finished.

            C{key}::
                A key was pressed during the composition sequence.

        @type hotKey: C{int}
        @param hotKey: Virtual-key code of the key that should initiate a
            a composition

        @type compositions: C{dict} mapping a C{2-tuple} to C{int}
        @param compositions: A mapping of 2-tuples of ordinals for composition
            sequences to composition ordinals

        @type callback: C{callable} taking C{unicode}
        @param callback: A callback that is fired with the state name whenever
            the hook changes state
        """
        self.hotKey = hotKey
        self.compositions = compositions
        self.callback = callback

        self.keyboardState = (CHAR * 256)()
        user32.GetKeyboardState(self.keyboardState)

        self.targetWindow = None
        self.composeDepth = 0
        self.composition = []
        self.composeKeys = []
        self._lastKey = None

    def setShift(self, hookStruct):
        """
        Sanitise keyboard shift state.
        """
        vkCode = hookStruct.vkCode
        keyboardState = self.keyboardState
        if vkCode in (VK_LSHIFT, VK_RSHIFT):
            if isKeyDown(hookStruct.flags):
                keyboardState[vkCode] = chr(LLKHF_UP)
            else:
                keyboardState[vkCode] = chr(0)
            keyboardState[VK_SHIFT] = chr(ord(keyboardState[VK_LSHIFT]) | ord(keyboardState[VK_RSHIFT]))

    def sendInput(self):
        """
        Send buffered compositions as keyboard input.

        The composition buffer is cleared once the input has been sent.
        """
        numInputs = len(self.composition) * 2
        if not numInputs:
            return

        inputs = (INPUT * numInputs)()
        i = 0
        for c in self.composition:
            a, b = inputs[i], inputs[i + 1]
            i += 2

            a.type = b.type = INPUT_KEYBOARD
            a.ki.wScan = b.ki.wScan = c
            a.ki.dwFlags = b.ki.dwFlags = KEYEVENTF_UNICODE
            a.ki.dwExtraInfo = user32.GetMessageExtraInfo()

            b.ki.dwFlags |= KEYEVENTF_KEYUP
            b.ki.dwExtraInfo = user32.GetMessageExtraInfo()

        user32.SendInput(numInputs, inputs, ctypes.sizeof(INPUT))
        self.composition = []

    def translateKey(self, (vkCode, scanCode)):
        """
        Attempt to translate a virtual-key/scan code pair into an ordinal.

        If the pair can not be translated the virtual-key code is returned.

        @type vkCode: C{int}
        @param vkCode: The key's virtual-key code

        @type scanCode: C{int}
        @param scanCode: The key's scan code

        @rtype: C{(int, bool)}
        @return: C{(ordinal, True)} or if the translation was unsucessful
            C{(vkCode, False)} is returned instead
        """
        # XXX: This is just an arbitrary limitation.
        bufSize = 4
        buf = (WCHAR * bufSize)()

        if vkCode == VK_PACKET:
            return scanCode, True
        else:
            rv = user32.ToUnicode(vkCode, scanCode, self.keyboardState, buf, bufSize, 0)
            if rv == 0:
                return vkCode, False
            return ord(buf.value[:rv]), True

    def compose(self):
        """
        Compose buffered keys and buffer the composition.

        If the composition is invalid a beep is sounded.  In either case, the
        C{done} event is triggered.
        """
        if self.composeKeys:
            comp = self.compositions.get(tuple(self.composeKeys))
        else:
            comp = None

        if comp is not None:
            self.composition.append(comp)
        else:
            user32.MessageBeep(-1)

        self.doneComposing()

    def startComposing(self):
        """
        Begin trapping keys for a composition sequence.

        The C{start} event is triggered.
        """
        # Trash the old composing state before starting a new one.
        self.stopComposing()
        self.targetWindow = user32.GetForegroundWindow()
        self.composeKeys = []
        self.composeDepth += 1
        if self.callback is not None:
            self.callback(u'start')

    def doneComposing(self):
        """
        Finish trapping keys and send any composed input.

        The C{start} event is triggered.
        """
        self.composeKeys = []
        self.composeDepth -= 1
        self.sendInput()
        if self.callback is not None and self.composeDepth == 0:
            self.callback(u'done')

    def stopComposing(self):
        """
        Stop trapping keys and ditch any buffered input.

        The C{done} event is triggered.
        """
        self.composeKeys = []
        self.composition = []
        self.composeDepth = 0
        if self.callback is not None:
            self.callback(u'done')

    def proc(self, hookStruct):
        self.setShift(hookStruct)

        vkCode = hookStruct.vkCode
        scanCode = hookStruct.scanCode
        key = (vkCode, scanCode)
        tkey, translated = self.translateKey(key)

        # We were composing but then the focus changed, so we abort.
        if self.composeDepth and self.targetWindow != user32.GetForegroundWindow():
            self.stopComposing()
            return False

        # We can ignore keys that are going up if we're already captured them.
        if isKeyUp(hookStruct.flags) and (key == self._lastKey or tkey in self.composeKeys):
            return True

        # If we receive an injected character and we're still composing, it was
        # probably a direct result of our composing, so we hang on to it.
        if hookStruct.flags & LLKHF_INJECTED:
            if self.composeDepth:
                self.composeKeys.append(tkey)
                return True
            return False

        self._lastKey = key

        if vkCode == self.hotKey:
            self.startComposing()
            return True

        # Keys that could not be translated (i.e. keys that are probably
        # not letters or digits or similar) are almost certainly keys
        # we don't want to use.
        if translated and self.composeDepth:
            if vkCode == VK_ESCAPE:
                self.stopComposing()
            else:
                if self.callback is not None:
                    self.callback(u'key')
                self.composeKeys.append(tkey)
                # XXX: don't hardcode this
                if len(self.composeKeys) == 2:
                    self.compose()

            return True

        # If we're not going to handle this key, they we should not swallow the
        # key up event.
        self._lastKey = None
        return False
