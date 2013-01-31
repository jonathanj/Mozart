import codecs, re, string, sys, unicodedata

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
    u'colon': unicodedata.name(u':'),
    }

for c in unicode(string.letters + string.digits):
    KEYS[c] = unicodedata.name(c)

pattern = re.compile(ur'<Multi_key> <(.*?)> <(.*?)>\s+:.*? # (.*)$')

out = codecs.open(sys.argv[2], 'wb', 'utf-8')

for line in codecs.open(sys.argv[1], 'r', 'utf-8'):
    match = pattern.match(line)
    if match is not None:
        a, b, r = match.groups()
        a, b = KEYS.get(a), KEYS.get(b)
        if None not in (a, b):
            out.write(u'<%s> <%s> <%s>\n' % (a, b, r))
