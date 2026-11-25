import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kb_store import Store


class CleanupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.s = Store(self.root, create=True)
        self.addCleanup(self.s.close)

    def put(self, source, key, text):
        return self.s.put(source, key, text.encode(), [('P1', text)])['status']

    def counts(self):
        names = ('sources', 'ignored', 'versions', 'originals', 'passages', 'passage_fts')
        return {n: self.s._db.execute('SELECT count(*) FROM ' + n).fetchone()[0] for n in names}

    def test_delete_ignore_restore_clear(self):
        s = self.s
        s.register('empty')
        self.assertEqual(s.classify('file', 'doc', b'x'), 'new')
        self.put('file', 'doc', '共同材料')
        self.put('folder', 'doc', '共同材料')
        old = next(r['citation'] for r in s.search('共同材料') if r['source'] == 'folder')
        self.assertEqual(s.classify('folder', 'doc', '共同材料'.encode()), 'unchanged')
        self.assertEqual(s.classify('folder', 'doc', b'new'), 'changed')
        self.put('folder', 'doc', '独有新版')
        new = s.search('独有新版')[0]['citation']
        self.assertEqual(s.remove_doc('folder', 'doc')['versions'], 2)
        self.assertEqual(s.sources(), ['empty', 'file', 'folder'])
        self.assertEqual(s.classify('folder', 'doc', b'other'), 'ignored')
        self.assertEqual(self.put('folder', 'doc', '又更新'), 'ignored')
        self.assertEqual(self.counts(), dict(sources=3, ignored=1, originals=1, versions=1, passages=1, passage_fts=1))
        for citation in (old, new):
            with self.assertRaises(KeyError):
                s.read(citation)
        s.restore('folder', 'doc')
        self.assertEqual(self.put('folder', 'doc', '共同材料'), 'new')
        s.remove_doc('folder', 'doc')
        s.remove_source('folder')
        self.assertEqual(s.classify('folder', 'doc', b'x'), 'new')
        self.assertEqual(s.sources(), ['empty', 'file'])
        self.assertEqual(s.search('共同材料')[0]['source'], 'file')
        s.clear()
        self.assertFalse(any(self.counts().values()))
        with self.assertRaisesRegex(ValueError, 'Source removed'):
            s.put('file', 'doc', b'stale', [], require_registered=True)
        self.assertEqual(s.sources(), [])

    def test_failed_cleanup_rolls_back(self):
        self.put('src', 'key', '证据原文')
        self.s._db.execute("CREATE TRIGGER fail BEFORE DELETE ON versions BEGIN SELECT RAISE(ABORT, 'failure'); END")
        before = self.counts()
        with self.assertRaises(sqlite3.IntegrityError):
            self.s.remove_doc('src', 'key')
        self.assertEqual(self.counts(), before)
        self.assertEqual(len(self.s.search('证据原文')), 1)

    def test_concurrent_migration_and_refresh(self):
        self.put('single', 'key', '旧版材料')
        citation = self.s.search('旧版材料')[0]['citation']
        db = self.s._db
        with db:
            for stmt in ('DROP TABLE ignored', 'DROP TABLE sources', 'DROP INDEX version_digest', 'PRAGMA user_version=2'):
                db.execute(stmt)
        barrier = threading.Barrier(2)

        def worker(i):
            barrier.wait(timeout=5)
            s = Store(self.root)
            try:
                self.assertEqual(s.sources(), ['single'])
                self.assertEqual(s.read(citation)['text'], '旧版材料')
                barrier.wait(timeout=5)
                if i:
                    s.remove_doc('single', 'key')
                else:
                    s.put('single', 'key', b'changed', [('P2', '更新材料')])
            finally:
                s.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(worker, [0, 1]))
        self.assertEqual(self.s.classify('single', 'key', b'changed'), 'ignored')
        self.assertEqual(self.counts()['passage_fts'], 0)
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 3)


if __name__ == '__main__':
    unittest.main()
