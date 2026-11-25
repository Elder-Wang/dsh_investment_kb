import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import kb_planet as p


class Store:
    def __init__(self):
        self.docs, self.cursors, self.sources = {}, {}, set()

    def register(self, source):
        self.sources.add(source)

    def get_cursor(self, source):
        return self.cursors.get(source)

    def save_cursor(self, source, value):
        self.cursors[source] = value

    def put(self, source, key, raw, parts, *, require_registered, metadata):
        assert require_registered and source in self.sources
        prev = self.docs.get(key)
        self.docs[key] = raw, parts, metadata
        return {'status': 'unchanged' if prev and prev[0] == raw else 'changed' if prev else 'new'}


def topic(n):
    return {'topic_id': n, 'create_time': '2026-01-%02dT12:00:00+08:00' % n,
            'type': 'talk', 'talk': {'text': '原文%d' % n, 'owner': {'name': '作者'}}}


class PlanetTests(unittest.TestCase):
    def test_backfill_and_incremental_gap(self):
        s = Store()
        groups = [[4, 3], [2, 1], [8, 7], [6, 5], [4, 3], []]
        pages = [[topic(n) for n in ns] for ns in groups]
        with patch.object(p, '_page', side_effect=pages) as fetch:
            results = [p.sync(s, '123', 'secret') for _ in pages]
        self.assertEqual([c.args[2] for c in fetch.call_args_list], [None, topic(3)['create_time'], None,
                         topic(7)['create_time'], topic(5)['create_time'], topic(1)['create_time']])
        self.assertEqual(p.planet_status(s, 123)['coverage'], results[-1]['coverage'])
        empty = Store()
        self.assertEqual(p.planet_status(empty, 123)['status'], 'not_synced')
        self.assertFalse(empty.sources)
        self.assertEqual(set(s.docs), {str(n) for n in range(1, 9)})
        self.assertTrue(results[-1]['coverage']['history_complete'])
        self.assertEqual(results[-1]['coverage']['start'], topic(1)['create_time'])
        self.assertEqual(results[-1]['coverage']['end'], topic(8)['create_time'])
        self.assertEqual(results[-2]['counts']['unchanged'], 2)
        self.assertNotIn('secret', repr((s.docs, s.cursors, results)))

    def test_mixed_sources_real_storage_and_compact_offset(self):
        import tempfile
        from kb_store import Store as Library
        with tempfile.TemporaryDirectory() as tmp:
            lib = Library(tmp, create=True)
            try:
                lib.put('本地笔记', 'A.md', b'local', [('L1', '光模块：我的判断')])
                post = topic(2)
                post['talk']['text'] = '光模块：他人判断'
                post['create_time'] = '2026-01-02T12:00:00.550+0800'
                with patch.object(p, '_page', return_value=[post]):
                    self.assertEqual(p.sync(lib, 123, 'mock')['status'], 'ok')
                self.assertEqual({r['source'] for r in lib.search('光模块')}, {'本地笔记', 'zsxq:123'})
                hit = lib.search('光模块', source='zsxq:123')[0]
                self.assertEqual(hit['metadata']['published'], post['create_time'])
                self.assertEqual(lib.read_document(hit['citation'])['passages'][0]['text'], post['talk']['text'])
            finally:
                lib.close()

    def test_partial_write_replay(self):
        s = Store()
        put = s.put
        def interrupt(*args, **kwargs):
            if args[1] == '1':
                raise RuntimeError('interrupted')
            return put(*args, **kwargs)
        with patch.object(p, '_page', return_value=[topic(2), topic(1)]):
            with patch.object(s, 'put', side_effect=interrupt), self.assertRaises(RuntimeError):
                p.sync(s, 1, 'valid')
            self.assertFalse(s.cursors)
            result = p.sync(s, 1, 'valid')
        self.assertEqual(result['counts']['unchanged'], 1)
        self.assertEqual(result['counts']['new'], 1)

    def test_transport_errors_are_sanitized(self):
        for code, status in [(302, 'redirect_refused'), (403, 'unauthorized'), (429, 'rate_limited')]:
            s = Store()
            with patch.object(p, 'build_opener') as opener:
                opener.return_value.open.side_effect = HTTPError('fake', code, 'secret', {}, io.BytesIO())
                result = p.sync(s, 1, 'secret')
                req = opener.return_value.open.call_args.args[0]
                self.assertNotIn('secret', req.full_url)
                self.assertNotIn('Cookie', req.headers)
                self.assertEqual(req.get_header('Cookie'), 'zsxq_access_token=secret')
                self.assertIsNone(opener.call_args.args[0].redirect_request())
            self.assertEqual(result['status'], status)
            self.assertNotIn('secret', repr(result))
            self.assertFalse(s.cursors)
        with patch.object(p, 'build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps({'code': 1059}).encode())
            self.assertEqual(p.sync(Store(), 1, 'valid')['status'], 'rate_limited')

    def test_stalled_pagination_not_complete(self):
        s = Store()
        with patch.object(p, '_page', return_value=[topic(2)]):
            p.sync(s, 1, 'valid')
            checkpoint = dict(s.cursors)
            result = p.sync(s, 1, 'valid')
        self.assertEqual(result['status'], 'cursor_stalled')
        self.assertEqual(s.cursors, checkpoint)
        self.assertFalse(result['coverage']['history_complete'])


if __name__ == '__main__':
    unittest.main()
