import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CLI = Path(__file__).resolve().with_name('kb_cli.py')


class LocalLifecycle(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.library = self.root / '空白 资料库'

    def call(self, *args, success=True):
        proc = subprocess.run([sys.executable, '-E', '-s', str(CLI), '--library',
                               str(self.library), *args], cwd=self.root,
                              env={'PATH': os.defpath, 'HOME': str(self.root)},
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)
        self.assertNotEqual(proc.returncode, 0)
        return json.loads(proc.stderr)['error']

    def test_refresh_then_read_historical_citation(self):
        self.call('init')
        note = self.root / '研究 笔记.md'
        note.write_text('# 记录\n\n旧判断：光模块库存上升。', encoding='utf-8')
        self.assertEqual(self.call('import-file', str(note))['status'], 'new')
        old = self.call('search', '光模块')[0]['citation']
        self.assertEqual(self.call('import-file', str(note))['status'], 'unchanged')
        note.write_text('# 记录\n\n新判断：供给改善。', encoding='utf-8')
        self.assertEqual(self.call('import-file', str(note))['status'], 'changed')
        self.assertEqual(self.call('search', '光模块'), [])
        self.assertIn('供给改善', self.call('search', '供给改善')[0]['text'])
        self.assertIn('光模块库存上升', self.call('read', old)['text'])
        document = self.call('document', old)
        self.assertEqual([p['text'] for p in document['passages']], ['记录', '旧判断：光模块库存上升。'])
        self.assertEqual(self.call('search', '供给改善', '--source', 'zsxq:123'), [])
        self.assertEqual(len(self.call('search', '供给改善', '--source', document['source'])), 1)
        self.assertEqual(note.read_text(encoding='utf-8'), '# 记录\n\n新判断：供给改善。')

    def test_planet_sync_without_credentials_stays_local(self):
        self.call('init')
        error = self.call('sync-planet', '123', success=False)
        self.assertIn('ZSXQ_ACCESS_TOKEN', error)
        self.assertEqual(self.call('sources'), [])
        report = self.call('planet-status', '123')
        self.assertEqual(report['source'], 'zsxq:123')
        self.assertEqual(self.call('sources'), [])

    def test_folder_lifecycle_with_confirmation(self):
        self.call('init')
        folder = (self.root / '跟踪资料').resolve()
        folder.mkdir()
        note = folder / '每周.md'
        note.write_text('光模块周报', encoding='utf-8')
        self.assertEqual(self.call('preview-folder', folder)['entries'][0]['status'], 'new')
        self.assertEqual(self.call('sources'), [])
        self.call('refresh-folder', folder)
        cite = self.call('search', '光模块')[0]['citation']
        self.assertEqual(self.call('sources'), [str(folder)])
        self.call('remove-doc', folder, note.name, success=False)
        self.assertEqual(self.call('read', cite)['text'], '光模块周报')
        self.call('remove-doc', folder, note.name, '--confirm')
        self.assertEqual(self.call('refresh-folder', folder)['entries'][0]['status'], 'ignored')
        self.assertIn('引用不可用', self.call('read', cite, success=False))
        self.call('restore-doc', folder, note.name, '--confirm')
        self.call('refresh-folder', folder)
        self.assertEqual(len(self.call('search', '光模块')), 1)
        self.call('clear', '--confirm')
        self.assertEqual(self.call('sources'), [])
        self.assertEqual(self.call('search', '光模块'), [])
        self.assertEqual(note.read_text(encoding='utf-8'), '光模块周报')

    def test_reject_nonempty_library_and_unknown_format(self):
        self.library.mkdir()
        marker = self.library / 'private.txt'
        marker.write_bytes(b'untouched')
        self.call('init', success=False)
        self.assertEqual(marker.read_bytes(), b'untouched')
        self.library = self.root / 'new'
        self.call('init')
        other = self.root / 'old.doc'
        other.write_bytes(b'not docx')
        self.call('import-file', str(other), success=False)
        self.assertEqual(self.call('search', 'not'), [])


if __name__ == '__main__':
    unittest.main()
