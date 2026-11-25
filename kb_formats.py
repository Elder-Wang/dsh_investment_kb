"""Bounded, offline paragraph readers. Locators are relative to a document version."""
import io
import re
import zipfile
import zlib
from html.parser import HTMLParser
from pathlib import PurePath
from xml.etree import ElementTree as ET

MAX_BYTES = 8 * 1024 * 1024
MAX_XML = 12 * 1024 * 1024
MAX_PARAGRAPHS = 50000
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _decode(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig')


def _add(out, locator, text):
    text = text.strip()
    if text:
        if len(out) >= MAX_PARAGRAPHS:
            raise ValueError('too many paragraphs')
        out.append((locator, text))


def _plain(text, markdown):
    out, lines, heads = [], [], []
    start = 1

    def flush():
        if lines:
            locator = ' › '.join(h for _, h in heads)
            _add(out, ('%s · ' % locator if locator else '') + 'L%d' % start,
                 '\n'.join(lines))
            lines.clear()

    for n, line in enumerate(text.splitlines(), 1):
        heading = re.match(r'^ {0,3}(#{1,6})[ \t]+(.+)$', line) if markdown else None
        if heading:
            flush()
            level, title = len(heading[1]), heading[2].strip()
            while heads and heads[-1][0] >= level:
                heads.pop()
            heads.append((level, title[:120]))
            _add(out, 'L%d' % n, title)
        elif not line.strip():
            flush()
        else:
            if not lines:
                start = n
            lines.append(line)
    flush()
    return out


class _HTML(HTMLParser):
    skip = set('script style nav header footer aside noscript template iframe object svg head'.split())
    blocks = set('article section main div p pre blockquote li ul ol h1 h2 h3 h4 h5 h6 table tr th td br hr'.split())

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden, self.buf, self.out = [], [], []

    def flush(self):
        _add(self.out, 'html:p%d' % (len(self.out) + 1), ' '.join(''.join(self.buf).split()))
        self.buf.clear()

    def handle_starttag(self, tag, attrs):
        if tag in self.skip:
            self.hidden.append(tag)
        elif not self.hidden and tag in self.blocks:
            self.flush()

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
        elif tag in self.blocks:
            self.flush()

    def handle_data(self, data):
        if not self.hidden:
            self.buf.append(data)


def _docx(raw):
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo('word/document.xml')
            if info.file_size > MAX_XML:
                raise ValueError('DOCX document XML too large')
            with archive.open(info) as stream:
                xml = stream.read(MAX_XML + 1)
        if len(xml) > MAX_XML or b'<!DOCTYPE' in xml.replace(b'\x00', b''):
            raise ValueError('oversized XML or disallowed DTD')
        root = ET.fromstring(xml)
    except (zipfile.BadZipFile, KeyError, RuntimeError, ET.ParseError, EOFError,
            zlib.error, LookupError, NotImplementedError) as exc:
        raise ValueError('invalid or unsupported DOCX') from exc
    body = root.find(W + 'body')
    if body is None:
        raise ValueError('DOCX body missing')
    out = []

    def para(el, locator):
        _add(out, locator, ''.join(node.text or '' if node.tag == W + 't' else
             '\t' if node.tag == W + 'tab' else '\n' if node.tag in (W + 'br', W + 'cr') else ''
             for node in el.iter()))

    p = t = 0
    for el in body:
        if el.tag == W + 'p':
            p += 1
            para(el, 'docx:p%d' % p)
        elif el.tag == W + 'tbl':
            t += 1
            for r, row in enumerate(el.findall(W + 'tr'), 1):
                for c, cell in enumerate(row.findall(W + 'tc'), 1):
                    for i, item in enumerate(cell.iter(W + 'p'), 1):
                        para(item, 'docx:t%d/r%d/c%d/p%d' % (t, r, c, i))
    return out


def parse(name: str, raw: bytes) -> list[tuple[str, str]]:
    """Extract ordered (locator, text) pairs; text inputs use UTF-8 or BOM UTF-16."""
    if len(raw) > MAX_BYTES:
        raise ValueError('input too large')
    ext = PurePath(name).suffix.lower()
    if ext == '.docx':
        return _docx(raw)
    if ext in ('.md', '.markdown', '.txt'):
        return _plain(_decode(raw), ext != '.txt')
    if ext in ('.html', '.htm'):
        parser = _HTML()
        parser.feed(_decode(raw))
        parser.close()
        parser.flush()
        return parser.out
    raise ValueError('unsupported file extension: ' + ext)
