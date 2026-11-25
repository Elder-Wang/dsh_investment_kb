"""Preview and refresh a registered local directory. No background watcher."""
import os
from pathlib import Path
import sqlite3
import stat

from kb_formats import MAX_BYTES, parse


_EXT = {'.md', '.markdown', '.txt', '.html', '.htm', '.docx'}
_ERRORS = (OSError, ValueError, RuntimeError, sqlite3.Error)


def _scan(store, root, path, write):
    library = Path(root).expanduser().resolve()
    selected = Path(path).expanduser()
    if selected.is_symlink():
        raise ValueError('不能选择目录软链接')
    directory = selected.resolve(strict=True)
    if directory == library or library in directory.parents:
        raise ValueError('不能导入知识库目录或其子目录')
    if not directory.is_dir():
        raise NotADirectoryError(str(directory))
    source = str(directory)
    entries = []

    def record(key, status, reason=None):
        item = {'key': key, 'status': status}
        if reason:
            item['reason'] = reason
        entries.append(item)

    # POSIX dir_fd anchors child opens to the directory traversed. O_NOFOLLOW
    # also rejects a symlink swapped in between lstat and open.
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK

    def signature(st):
        return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns

    def visit(fd, prefix):
        for name in sorted(os.listdir(fd)):
            if name.startswith('.'):
                continue
            key = prefix + name
            if directory / key == library:
                continue
            try:
                before = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(before.st_mode):
                    record(key, 'unsupported', '跳过软链接')
                    continue
                if stat.S_ISDIR(before.st_mode):
                    child = os.open(name, directory_flags, dir_fd=fd)
                    try:
                        visit(child, key + '/')
                    finally:
                        os.close(child)
                    continue
                if not stat.S_ISREG(before.st_mode) or Path(name).suffix.lower() not in _EXT:
                    record(key, 'unsupported', '不支持此文件类型')
                    continue
                if before.st_size > MAX_BYTES:
                    raise ValueError('文件超过大小上限')
                with os.fdopen(os.open(name, file_flags, dir_fd=fd), 'rb') as stream:
                    opened = os.fstat(stream.fileno())
                    if not stat.S_ISREG(opened.st_mode) or signature(opened) != signature(before):
                        raise ValueError('扫描期间文件已更改，请重新刷新')
                    raw = stream.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES or signature(os.fstat(stream.fileno())) != signature(before):
                        raise ValueError('读取期间文件已更改或超过大小上限')
                status = store.classify(source, key, raw)
                if status not in ('ignored', 'unchanged', 'new', 'changed'):
                    raise ValueError('未知的资料状态')
                if status in ('new', 'changed'):
                    parts = parse(name, raw)
                    if write:
                        status = store.put(source, key, raw, parts, require_registered=True)['status']
                record(key, status)
            except _ERRORS as exc:
                record(key, 'error', str(exc))

    fd = os.open(directory, directory_flags)
    try:
        if write:
            store.register(source)
        visit(fd, '')
    finally:
        os.close(fd)
    return {'source': source, 'entries': entries}


def preview(store, root, path):
    """Read-only scan; does not register sources, put versions or delete archives."""
    return _scan(store, root, path, False)


def refresh(store, root, path):
    """Register the folder and import eligible changes; missing files stay archived."""
    return _scan(store, root, path, True)
