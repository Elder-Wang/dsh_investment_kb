"""Local JSON CLI for the investment knowledge base. Python 3.9+."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from kb_formats import MAX_BYTES, parse
from kb_store import Store
from kb_folders import preview, refresh


def parser():
    p = argparse.ArgumentParser(description='投研资料库（本地，无模型）')
    p.add_argument('--library', type=Path, required=True, help='独立知识库目录')
    sub = p.add_subparsers(required=True, dest='action')
    sub.add_parser('init', help='在空目录建库')
    for cmd in ('preview-file', 'import-file'):
        sub.add_parser(cmd).add_argument('path', type=Path)
    query = sub.add_parser('search', help='按关键词检索当前版本')
    query.add_argument('query')
    query.add_argument('--limit', type=int, default=20, choices=range(1, 101), metavar='1..100')
    sub.add_parser('read', help='回读指定版本的引文').add_argument('citation')
    for cmd in ('preview-folder', 'refresh-folder'):
        sub.add_parser(cmd).add_argument('path', type=Path)
    sub.add_parser('sources', help='列出已登记的来源')
    for cmd in ('remove-doc', 'remove-source', 'clear', 'restore-doc'):
        action = sub.add_parser(cmd)
        if cmd != 'clear':
            action.add_argument('source', help='来源标识，使用 sources 返回的精确值')
        if cmd in ('remove-doc', 'restore-doc'):
            action.add_argument('key', help='来源内的文档标识')
        action.add_argument('--confirm', action='store_true', help='确认执行此操作')
    return p


def run(args):
    root = args.library.expanduser().resolve()
    store = Store(root, create=args.action == 'init')
    try:
        if args.action == 'init':
            return {'library': str(root), 'ready': True}
        if args.action == 'sources':
            return store.sources()
        if args.action in ('preview-folder', 'refresh-folder'):
            operation = preview if args.action == 'preview-folder' else refresh
            return operation(store, root, args.path.expanduser())
        if args.action in ('remove-doc', 'remove-source', 'clear', 'restore-doc'):
            if not args.confirm:
                raise ValueError('操作未执行：请核对资料库、来源及文档后添加 --confirm')
            if args.action == 'clear':
                return store.clear()
            if args.action == 'remove-source':
                return store.remove_source(args.source)
            if args.action == 'restore-doc':
                return store.restore(args.source, args.key)
            return store.remove_doc(args.source, args.key)
        if args.action in ('preview-file', 'import-file'):
            path = args.path.expanduser().resolve(strict=True)
            if not path.is_file() or root in path.parents:
                raise ValueError('请选择知识库目录以外的普通文件')
            with path.open('rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('单文件不能超过 8 MiB')
            status = store.classify(str(path), path.name, raw)
            if status in ('ignored', 'unchanged'):
                return {'status': status, 'source': str(path), 'key': path.name}
            parts = parse(path.name, raw)
            if args.action == 'preview-file':
                return {'status': status, 'source': str(path), 'key': path.name, 'passages': len(parts)}
            return store.put(str(path), path.name, raw, parts)
        if args.action == 'search':
            if not args.query.strip():
                raise ValueError('请输入关键词')
            return store.search(args.query, limit=args.limit)
        try:
            return store.read(args.citation)
        except KeyError:
            raise ValueError('引用不可用：资料可能已清理，或该引用不属于当前库') from None
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
