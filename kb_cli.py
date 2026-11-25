"""Local JSON CLI for the investment knowledge base. Python 3.9+."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from kb_formats import MAX_BYTES, parse
from kb_store import Store


def parser():
    p = argparse.ArgumentParser(description='投研资料库（本地，无模型）')
    p.add_argument('--library', type=Path, required=True, help='独立知识库目录')
    sub = p.add_subparsers(required=True, dest='action')
    sub.add_parser('init', help='在空目录建库')
    imp = sub.add_parser('import-file', help='导入单文件，再次执行即检查更新')
    imp.add_argument('path', type=Path)
    query = sub.add_parser('search', help='按关键词检索当前版本')
    query.add_argument('query')
    query.add_argument('--limit', type=int, default=20, choices=range(1, 101), metavar='1..100')
    sub.add_parser('read', help='回读指定版本的引文').add_argument('citation')
    return p


def run(args):
    root = args.library.expanduser().resolve()
    store = Store(root, create=args.action == 'init')
    try:
        if args.action == 'init':
            return {'library': str(root), 'ready': True}
        if args.action == 'import-file':
            path = args.path.expanduser().resolve(strict=True)
            if not path.is_file() or root in path.parents:
                raise ValueError('请选择知识库目录以外的普通文件')
            with path.open('rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('单文件不能超过 8 MiB')
            return store.put(str(path), path.name, raw, parse(path.name, raw))
        if args.action == 'search':
            if not args.query.strip():
                raise ValueError('请输入关键词')
            return store.search(args.query, limit=args.limit)
        return store.read(args.citation)
    finally:
        store.close()


def main():
    try:
        result = run(parser().parse_args())
    except (ValueError, OSError, sqlite3.Error, LookupError, RuntimeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
