import codecs
import itertools
import re
import string
import unicodedata

KEYS = {
    u'plus': unicodedata.name(u'+'),
    u'space': unicodedata.name(u' '),
    u'apostrophe': unicodedata.name(u"'"),
    u'parenleft': unicodedata.name(u'('),
    u'parenright': unicodedata.name(u'('),
    u'slash': unicodedata.name(u'\\'),
    u'less': unicodedata.name(u'<'),
    u'greater': unicodedata.name(u'>'),
    u'asciicircum': unicodedata.name(u'^'),
    u'grave': unicodedata.name(u'`'),
    u'comma': unicodedata.name(u','),
    u'minus': unicodedata.name(u'-'),
    u'asciitilde': unicodedata.name(u'~'),
    u'period': unicodedata.name(u'.'),
    u'equal': unicodedata.name(u'='),
    u'exclam': unicodedata.name(u'!'),
    u'question': unicodedata.name(u'?'),
    u'quotedbl': unicodedata.name(u'"'),
    u'quotedbl': unicodedata.name(u'"'),
    u'backslash': unicodedata.name(u'\\'),
    u'percent': unicodedata.name(u'%'),
    u'colon': unicodedata.name(u':')}

for c in unicode(string.letters + string.digits):
    KEYS[c] = unicodedata.name(c)



keyPattern = re.compile(r'(?<=<)[^>>]+(?=>)')
resultPattern = re.compile(r'\s*"([^"]+)" .* # .*$')



def readCompositions(path):
    """
    Read a I{Compose} file and yield usable results.

    Compositions that are not I{Multi_key} are ignored, as are compositions
    that contain unknown key names.

    @rtype: I{iterable} of C{(list, unicode)}
    @return: An iterable of pairs of a L{list} of L{unicode} characters and
        their composed U{unicode} result.
    """
    with codecs.open(path, 'r', 'utf-8') as fd:
        for line in fd:
            line = line.strip()
            if not line or line.startswith(u'#'):
                continue

            keys, result = line.split(u':', 1)
            keys = keyPattern.findall(keys)
            result = resultPattern.findall(result)
            if not keys or not result:
                continue

            first = keys.pop(0)
            if first != 'Multi_key':
                continue

            keys = map(KEYS.get, keys)
            if None in keys:
                continue

            keys = map(unicodedata.lookup, keys)
            if keys:
                yield keys, result[0]
