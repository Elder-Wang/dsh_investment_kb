from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import kb_folders as f


class FakeStore:
    def __init__(self):
        self.registered, self.puts, self.data, self.ignored = [], [], {}, set()

    def register(self, source):
        self.registered.append(source)

    def classify(self, source, key, raw):
        if key in self.ignored:
            return 'ignored'
        if (source, key) not in self.data:
            return 'new'
        return 'unchanged' if self.data[source, key] == raw else 'changed'

    def put(self, source, key, raw, parts, *, require_registered):
        assert require_registered and source in self.registered
        status = self.classify(source, key, raw)
        self.puts.append(key)
        self.data[source, key] = raw
        return {'status': status}


class FolderTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name).resolve()
        self.library = self.folder / 'library'
        self.library.mkdir()
        self.store = FakeStore()

    def statuses(self, fn):
        result = fn(self.store, self.library, self.folder)
        self.assertEqual(result['source'], str(self.folder))
        return {entry['key']: entry['status'] for entry in result['entries']}

    def test_refresh_lifecycle_no_resurrection(self):
        sub = self.folder / '跟踪'; sub.mkdir()
        note = sub / '甲.md'; note.write_bytes(b'# review')
        b = self.folder / 'ignored.txt'; b.write_bytes(b'private')
        self.store.ignored.add('ignored.txt')
        expected = {'跟踪/甲.md': 'new', 'ignored.txt': 'ignored'}
        self.assertEqual(self.statuses(f.preview), expected)
        self.assertEqual((self.store.registered, self.store.puts), ([], []))
        self.assertEqual(self.statuses(f.refresh), expected)
        self.assertEqual(self.statuses(f.refresh)['跟踪/甲.md'], 'unchanged')
        note.write_bytes(b'# new'); b.write_bytes(b'changed private')
        self.assertEqual(self.statuses(f.preview)['跟踪/甲.md'], 'changed')
        self.assertEqual(self.statuses(f.refresh)['跟踪/甲.md'], 'changed')
        self.assertEqual(self.store.puts, ['跟踪/甲.md', '跟踪/甲.md'])
        note.unlink()
        self.assertEqual(self.statuses(f.refresh), {'ignored.txt': 'ignored'})
        self.assertEqual(self.store.data[str(self.folder), '跟踪/甲.md'], b'# new')

    def test_boundaries_and_errors(self):
        (self.library / 'private.md').write_bytes(b'x')
        (self.folder / '.secret').mkdir(); (self.folder / '.secret' / 'p.md').write_bytes(b'x')
        (self.folder / 'link').symlink_to(self.library, target_is_directory=True)
        (self.folder / 'bad.md').write_bytes(b'\xff')
        (self.folder / 'x.pdf').write_bytes(b'x')
        (self.folder / 'large.txt').write_bytes(b'12345')
        with patch.object(f, 'MAX_BYTES', 4):
            self.assertEqual(self.statuses(f.refresh), {'link': 'unsupported', 'bad.md': 'error',
                             'x.pdf': 'unsupported', 'large.txt': 'error'})
        for folder in [self.library, self.folder / 'link', self.folder / 'missing']:
            with self.assertRaises((ValueError, OSError)):
                f.refresh(self.store, self.library, folder)
        self.assertFalse(self.store.puts)


if __name__ == '__main__':
    unittest.main()
