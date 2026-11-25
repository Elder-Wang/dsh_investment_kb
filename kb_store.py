"""Local versioned knowledge store (Python 3.9+, SQLite, no model).

Originals are immutable SQLite BLOBs keyed by SHA-256. Schema v4 migrates v2/v3 atomically and tracks
source registrations, refresh exclusions, source cursors, and version metadata. Search requires
SQLite with FTS5 trigram; opening fails explicitly if that is unavailable.
Search uses case-folded trigram candidates for terms of 3+ characters,
verifies every literal substring, and scans for short-only queries.
Citations address passages of specific versions, including superseded ones.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


_APP_ID = 0x4B425331
_SCHEMA = (
    'CREATE TABLE originals (digest TEXT PRIMARY KEY, raw BLOB NOT NULL)',
    '''CREATE TABLE versions (id INTEGER PRIMARY KEY, source TEXT NOT NULL,
       key TEXT NOT NULL, digest TEXT NOT NULL REFERENCES originals(digest))''',
    'CREATE INDEX version_lookup ON versions(source, key, id DESC)',
    '''CREATE TABLE passages (id INTEGER PRIMARY KEY, version INTEGER NOT NULL REFERENCES versions(id),
       pos INTEGER NOT NULL, citation TEXT NOT NULL UNIQUE, locator TEXT NOT NULL,
       text TEXT NOT NULL, UNIQUE(version, pos))''',
    "CREATE VIRTUAL TABLE passage_fts USING fts5(folded, tokenize='trigram case_sensitive 1')",
    '''CREATE TRIGGER drop_passage_index AFTER DELETE ON passages BEGIN
       DELETE FROM passage_fts WHERE rowid=OLD.id; END''',
)


class Store:
    def __init__(self, root, create=False):
        probe = sqlite3.connect(':memory:')
        try:
            probe.execute("CREATE VIRTUAL TABLE probe USING fts5(x, tokenize='trigram case_sensitive 1')")
        except sqlite3.OperationalError as exc:
            raise RuntimeError('SQLite with FTS5 trigram support is required') from exc
        finally:
            probe.close()
        root = Path(root).expanduser().resolve()
        if create:
            root.mkdir(parents=True, exist_ok=True)
        path = root / 'kb.sqlite3'
        fresh = False
        if path.is_symlink():
            raise ValueError('Knowledge database must not be a symbolic link')
        if not path.exists():
            if not create:
                raise FileNotFoundError(path)
            if any(root.iterdir()):
                raise ValueError('Creating a knowledge store requires an empty directory')
            path.touch(exist_ok=False)
            fresh = True
        if not path.is_file():
            raise ValueError('Expected a knowledge database file')
        db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                # Check the version *after* acquiring the writer lock: concurrent
                # first opens of a v2 store must not apply the migration twice.
                db.execute('BEGIN IMMEDIATE')
                if fresh:
                    for stmt in _SCHEMA:
                        db.execute(stmt)
                    db.execute('PRAGMA application_id=%d' % _APP_ID)
                    db.execute('PRAGMA user_version=2')
                version = db.execute('PRAGMA user_version').fetchone()[0]
                if db.execute('PRAGMA application_id').fetchone()[0] != _APP_ID or version not in (2, 3, 4):
                    raise ValueError('Not a supported knowledge store (expected schema v2, v3 or v4)')
                if version == 2:
                    db.execute('CREATE TABLE sources (source TEXT PRIMARY KEY NOT NULL)')
                    db.execute('INSERT INTO sources SELECT DISTINCT source FROM versions')
                    db.execute('CREATE TABLE ignored (source TEXT NOT NULL REFERENCES sources(source) '
                               'ON DELETE CASCADE, key TEXT NOT NULL, PRIMARY KEY(source,key))')
                    db.execute('CREATE INDEX version_digest ON versions(digest)')
                    db.execute('PRAGMA user_version=3')
                if version <= 3:
                    db.execute('CREATE TABLE cursors (source TEXT PRIMARY KEY NOT NULL REFERENCES '
                               'sources(source) ON DELETE CASCADE, cursor TEXT NOT NULL)')
                    db.execute('CREATE TABLE version_metadata (version INTEGER PRIMARY KEY REFERENCES '
                               'versions(id) ON DELETE CASCADE, payload TEXT NOT NULL)')
                    db.execute('PRAGMA user_version=4')
            db.execute('SELECT folded FROM passage_fts LIMIT 0')
            db.create_function('kb_fold', 1, str.casefold, deterministic=True)
            db.execute('SELECT v.id,v.source,v.key,o.digest,o.raw,p.pos,p.citation,'
                       'p.locator,p.text FROM versions v JOIN originals o ON '
                       'o.digest=v.digest JOIN passages p ON p.version=v.id LIMIT 0')
        except BaseException:
            db.close()
            raise
        self._db = db

    def close(self):
        self._db.close()

    @staticmethod
    def _check_names(*names):
        if not all(isinstance(s, str) and s.strip() for s in names):
            raise ValueError('source and key must be nonempty strings')

    @staticmethod
    def _digest(raw):
        if not isinstance(raw, bytes):
            raise TypeError('raw must be bytes')
        return hashlib.sha256(raw).hexdigest()

    def sources(self):
        return [r[0] for r in self._db.execute('SELECT source FROM sources ORDER BY source')]

    def register(self, source):
        self._check_names(source)
        with self._db:
            self._db.execute('INSERT OR IGNORE INTO sources VALUES (?)', (source,))
        return {'status': 'registered', 'source': source}

    def get_cursor(self, source):
        self._check_names(source)
        row = self._db.execute('SELECT cursor FROM cursors WHERE source=?', (source,)).fetchone()
        return None if row is None else row[0]

    def save_cursor(self, source, cursor):
        self._check_names(source)
        if not isinstance(cursor, str):
            raise ValueError('cursor must be a string')
        with self._db:
            changed = self._db.execute('INSERT INTO cursors(source,cursor) SELECT source,? '
                'FROM sources WHERE source=? ON CONFLICT(source) DO UPDATE SET cursor=excluded.cursor',
                (cursor, source)).rowcount
            if not changed:
                raise ValueError('Source removed before saving cursor')

    def _classify(self, source, key, digest):
        # One consistent statement snapshot for preview; put repeats it under lock.
        row = self._db.execute('''SELECT EXISTS(SELECT 1 FROM ignored WHERE source=?1 AND key=?2),
            v.id,v.digest FROM (SELECT 1) LEFT JOIN versions v ON v.id=(SELECT max(id)
            FROM versions WHERE source=?1 AND key=?2)''', (source,key)).fetchone()
        status = ('ignored' if row[0] else 'new' if row[1] is None else
                  'unchanged' if row[2] == digest else 'changed')
        return status, row[1]

    def classify(self, source, key, raw):
        self._check_names(source, key)
        return self._classify(source, key, self._digest(raw))[0]

    def restore(self, source, key):
        self._check_names(source, key)
        with self._db:
            changed = self._db.execute('DELETE FROM ignored WHERE source=? AND key=?', (source,key)).rowcount
        return {'status': 'restored' if changed else 'unchanged', 'source': source, 'key': key}

    def _purge(self, where, args):
        # where is a fixed internal clause, never user input. Delete passages
        # first so their delete trigger cleans matching FTS rows atomically.
        db = self._db
        db.execute('DELETE FROM passages WHERE version IN (SELECT id FROM versions' + where + ')', args)
        n = db.execute('DELETE FROM versions' + where, args).rowcount
        db.execute('DELETE FROM originals WHERE NOT EXISTS '
                   '(SELECT 1 FROM versions WHERE versions.digest=originals.digest)')
        return n

    def remove_doc(self, source, key):
        self._check_names(source, key)
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            n = self._purge(' WHERE source=? AND key=?', (source,key))
            if n:
                self._db.execute('INSERT OR IGNORE INTO ignored VALUES (?,?)', (source,key))
        return {'status': 'removed' if n else 'unchanged', 'source': source, 'key': key, 'versions': n}

    def remove_source(self, source):
        self._check_names(source)
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            n = self._purge(' WHERE source=?', (source,))
            removed = self._db.execute('DELETE FROM sources WHERE source=?', (source,)).rowcount
        return {'status': 'removed' if removed else 'unchanged', 'source': source, 'versions': n}

    def clear(self):
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            n = self._purge('', ())
            self._db.execute('DELETE FROM sources')
        return {'status': 'cleared', 'versions': n}

    def put(self, source: str, key: str, raw: bytes, parts: list, *, require_registered=False,
            metadata=None) -> dict:
        self._check_names(source, key)
        digest = self._digest(raw)
        db = self._db
        with db:
            db.execute('BEGIN IMMEDIATE')
            if require_registered and not db.execute('SELECT 1 FROM sources WHERE source=?', (source,)).fetchone():
                raise ValueError('Source removed before refresh completed')
            status, last = self._classify(source, key, digest)
            if status == 'ignored':
                return {'status': 'ignored'}
            if status == 'unchanged':
                return {'status': status, 'version': last}
            db.execute('INSERT OR IGNORE INTO sources VALUES (?)', (source,))
            db.execute('INSERT OR IGNORE INTO originals VALUES (?,?)', (digest, raw))
            version = db.execute('INSERT INTO versions(source,key,digest) VALUES (?,?,?)',
                                 (source, key, digest)).lastrowid
            if metadata is not None:
                if not isinstance(metadata, dict):
                    raise ValueError('metadata must be an object')
                payload = json.dumps(metadata, ensure_ascii=False, allow_nan=False)
                db.execute('INSERT INTO version_metadata VALUES (?,?)', (version, payload))
            for pos, (locator, text) in enumerate(parts):
                if not isinstance(locator, str) or not isinstance(text, str):
                    raise TypeError('locator and text must be strings')
                passage = db.execute('INSERT INTO passages(version,pos,citation,locator,text) '
                                     'VALUES (?,?,?,?,?)',
                                     (version, pos, 'kb:' + uuid4().hex, locator, text)).lastrowid
                db.execute('INSERT INTO passage_fts(rowid, folded) VALUES (?,?)',
                           (passage, text.casefold().replace('\x00', ' ')))
            return {'status': 'changed' if last else 'new', 'version': version}

    @staticmethod
    def _hit(row):
        hit = dict(row)
        hit['metadata'] = json.loads(hit['metadata']) if hit['metadata'] else {}
        return hit

    def search(self, query, limit=20, source=None):
        if not isinstance(limit, int) or limit < 0:
            raise ValueError('limit must be a nonnegative integer')
        terms = list(dict.fromkeys(query.casefold().split()))
        if not terms or not limit:
            return []
        indexed = [t for t in terms if len(t) >= 3 and '\x00' not in t]
        clauses = ['instr(kb_fold(p.text), ?) > 0' for _ in terms]
        params = list(terms)
        if source is not None:
            self._check_names(source)
            clauses.append('v.source=?')
            params.append(source)
        if indexed:
            # Every phrase is literal, including embedded quotes and FTS operators.
            phrases = ['"' + t.replace('"', '""') + '"' for t in indexed]
            clauses.insert(0, 'p.id IN (SELECT rowid FROM passage_fts WHERE passage_fts MATCH ?)')
            params.insert(0, ' AND '.join(phrases))
        rows = self._db.execute('''SELECT p.citation,p.text,v.source,v.key,p.locator,m.payload AS metadata
            FROM passages p JOIN versions v ON v.id=p.version LEFT JOIN version_metadata m ON m.version=v.id
            WHERE v.id=(SELECT max(w.id) FROM versions w WHERE w.source=v.source AND w.key=v.key)
            AND ''' + ' AND '.join(clauses) + ' ORDER BY v.id DESC,p.pos LIMIT ?', (*params, limit))
        return [self._hit(row) for row in rows]

    def read(self, citation):
        row = self._db.execute('''SELECT p.citation,p.text,v.source,v.key,p.locator,m.payload AS metadata
            FROM passages p JOIN versions v ON v.id=p.version LEFT JOIN version_metadata m ON m.version=v.id WHERE p.citation=?''',
                               (citation,)).fetchone()
        if row is None:
            raise KeyError(citation)
        return self._hit(row)

    def read_document(self, citation):
        """Resolve a passage citation to its immutable version, in passage order."""
        sql = '''SELECT v.id AS version,v.key,v.source,m.payload AS metadata,
                 p.citation,p.locator,p.text FROM passages anchor
                 JOIN versions v ON v.id=anchor.version
                 JOIN passages p ON p.version=v.id
                 LEFT JOIN version_metadata m ON m.version=v.id
                 WHERE anchor.citation=? ORDER BY p.pos'''
        rows = self._db.execute(sql, (citation,))
        doc = None
        for row in rows:
            if doc is None:
                doc = {k: row[k] for k in ('version', 'key', 'source')}
                doc['metadata'] = json.loads(row['metadata']) if row['metadata'] else {}
                doc['passages'] = []
            doc['passages'].append({k: row[k] for k in ('citation', 'locator', 'text')})
        if doc is None:
            raise KeyError(citation)
        return doc
