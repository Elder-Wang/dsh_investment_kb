import sqlite3
import tempfile
import unittest
from pathlib import Path

from kb_store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.s = Store(self.root, create=True)
        self.addCleanup(self.s.close)

    def test_dedup_and_historical_citation(self):
        for source in ['local', 'stars']:
            self.assertEqual(self.s.put(source, '稿', b'one', [('P1', '旧版光模块')])['status'], 'new')
        self.assertEqual(self.s.put('local', '稿', b'one', [])['status'], 'unchanged')
        results = self.s.search('光模块'); self.assertEqual(len(results), 2)
        old = next(r['citation'] for r in results if r['source'] == 'local')
        self.assertEqual(self.s.put('local', '稿', b'two', [('P2', '新版铜缆')])['status'], 'changed')
        self.assertEqual([r['source'] for r in self.s.search('光模块')], ['stars'])
        with sqlite3.connect(self.root / 'kb.sqlite3') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM originals').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM passage_fts WHERE passage_fts MATCH ?',
                                        ('"光模块"',)).fetchone()[0], 2)
        reopened = Store(self.root)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.read(old)['locator'], 'P1')
        self.assertEqual(reopened.read(old)['text'], '旧版光模块')

    def test_short_mixed_quotes_and_case(self):
        self.s.put('local', 'A', b'1', [('a', '光模块 降价 Straße A"Bc'), ('b', '光模块涨')])
        self.assertEqual([r['locator'] for r in self.s.search('价')], ['a'])
        self.assertEqual([r['locator'] for r in self.s.search('光模块 价')], ['a'])
        self.assertEqual([r['locator'] for r in self.s.search('STRASSE a"bc')], ['a'])
        self.assertEqual(self.s.search('光模块 or'), [])
        self.assertEqual(self.s.search('光模块', 0), [])
        self.assertEqual(self.s.search(''), [])


if __name__ == '__main__':
    unittest.main()
