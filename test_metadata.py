import tempfile
import unittest

from kb_store import Store


class MetadataTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.s = Store(tmp.name, create=True)
        self.addCleanup(self.s.close)

    def test_version_evidence_and_cleanup(self):
        s = self.s
        meta = dict(author='甲', published_at='2025-11-03', url='https://example.org/1',
                    collected_at='2025-11-06', extra={'tags': ['测试']})
        parts = [('导语', '回顾'), ('段落二', '需求预测')]
        s.put('星球', '1', b'old', parts, metadata=meta)
        s.put('本地', '1', b'other', parts)
        hit, = s.search('需求预测', source='星球')
        old = hit['citation']
        self.assertEqual(hit['metadata'], meta)
        self.assertEqual(s.search('预测', source='本地')[0]['metadata'], {})
        self.assertEqual(s.put('星球', '1', b'old', parts, metadata={'collected_at': 'later'})['status'], 'unchanged')
        s.put('星球', '1', b'new', [('唯一段', '不同预测')], metadata={'author': '乙'})
        self.assertEqual(s.read(old)['metadata'], meta)
        self.assertEqual(s.search('不同预测')[0]['metadata'], {'author': '乙'})
        doc = s.read_document(old)
        self.assertEqual((doc['key'], doc['source'], doc['metadata']), ('1', '星球', meta))
        self.assertEqual([(p['locator'], p['text']) for p in doc['passages']], parts)
        self.assertEqual(doc['passages'][1]['citation'], old)
        s.remove_doc('星球', '1')
        self.assertEqual(s._db.execute('SELECT count(*) FROM version_metadata').fetchone()[0], 0)
        with self.assertRaises(KeyError):
            s.read_document(old)

    def test_cursor_never_registers(self):
        s = self.s
        for action in (lambda: s.remove_source('x'), s.clear):
            s.register('x')
            self.assertIsNone(s.get_cursor('x'))
            for state in ('next page', ''):
                s.save_cursor('x', state)
                self.assertEqual(s.get_cursor('x'), state)
            action()
            self.assertIsNone(s.get_cursor('x'))
            with self.assertRaises(ValueError):
                s.save_cursor('x', 'stale')
            self.assertNotIn('x', s.sources())

    def test_v3_existing_citation_preserved(self):
        s = self.s
        s.put('source', 'file', b'original', [('1', '旧资料')])
        citation = s.search('旧资料')[0]['citation']
        with s._db:
            for sql in ('DROP TABLE cursors', 'DROP TABLE version_metadata', 'PRAGMA user_version=3'):
                s._db.execute(sql)
        migrated = Store(self.root)
        self.addCleanup(migrated.close)
        self.assertEqual(migrated.read_document(citation)['metadata'], {})
        self.assertEqual(migrated.sources(), ['source'])
        migrated.save_cursor('source', 'checkpoint')
        self.assertEqual(migrated.get_cursor('source'), 'checkpoint')


if __name__ == '__main__':
    unittest.main()
