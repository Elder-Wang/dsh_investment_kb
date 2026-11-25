import io
import unittest
import zipfile
from unittest.mock import patch

import kb_formats as f


def docx(xml):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml', xml)
    return buf.getvalue()


class FormatTests(unittest.TestCase):
    def test_text(self):
        self.assertEqual(f.parse('Notes.TXT', '甲\r\n乙\r\n\r\n丙'.encode('utf-16')),
                         [('L1', '甲\n乙'), ('L4', '丙')])

    def test_markdown(self):
        self.assertEqual(f.parse('x.md', b'# Root\n## Child\nline\n\nnext')[-1],
                         ('Root › Child · L5', 'next'))

    def test_html(self):
        html = '<head><title>skip</title></head><nav>menu</nav><p>A<b>B</b> &amp; C</p><script src="https://invalid">no</script><p>D</p>'
        self.assertEqual(f.parse('a.html', html.encode()), [('html:p1', 'AB & C'), ('html:p2', 'D')])

    def test_word(self):
        p = '<w:p><w:r><w:t>甲</w:t><w:tab/><w:t>乙</w:t></w:r></w:p>'
        xml = '<w:document xmlns:w="%s"><w:body>%s<w:tbl><w:tr><w:tc>%s</w:tc></w:tr></w:tbl>%s</w:body></w:document>' % (f.W[1:-1], p, p, p)
        self.assertEqual(f.parse('a.docx', docx(xml)), [('docx:p1', '甲\t乙'),
                         ('docx:t1/r1/c1/p1', '甲\t乙'), ('docx:p2', '甲\t乙')])

    def test_invalid(self):
        for name, raw in [('x.pdf', b''), ('x.docx', b'bad'), ('x.txt', b'\xff'),
                          ('x.docx', docx('<!DOCTYPE x><x/>'))]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                f.parse(name, raw)

    def test_limits(self):
        with patch.object(f, 'MAX_BYTES', 3), self.assertRaises(ValueError):
            f.parse('x.txt', b'abcd')
        with patch.object(f, 'MAX_XML', 100), self.assertRaises(ValueError):
            f.parse('x.docx', docx(' ' * 500))
        with patch.object(f, 'MAX_PARAGRAPHS', 1), self.assertRaises(ValueError):
            f.parse('x.txt', b'one\n\ntwo')


if __name__ == '__main__':
    unittest.main()
