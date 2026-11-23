# fsync-replace

[![PyPI](https://img.shields.io/pypi/v/fsync-replace.svg)](https://pypi.org/project/fsync-replace/)
[![Python](https://img.shields.io/pypi/pyversions/fsync-replace.svg)](https://pypi.org/project/fsync-replace/)
[![tests](https://github.com/sandeshbagmare/fsync-replace/actions/workflows/ci.yml/badge.svg)](https://github.com/sandeshbagmare/fsync-replace/actions/workflows/ci.yml)
[![license](https://img.shields.io/pypi/l/fsync-replace.svg)](https://github.com/sandeshbagmare/fsync-replace/blob/main/LICENSE)

Write a file **once, completely, or not at all**.

```python
from fsync_replace import write_atomic

write_atomic("report.json", '{"ok": true}')
```

`write_atomic` writes to a temporary file next to the target, calls `fsync`, renames
it over the target with `os.replace`, and then `fsync`s the directory entry so the
rename itself is durable. A crash, a kill signal or a full disk leaves either the old
file or the new one — never half of each.

The context manager is the same thing with a file handle:

```python
from fsync_replace import atomic_open

with atomic_open("state.json", "w") as handle:
    handle.write('{"step": 3}')
    # if this block raises, state.json is untouched and the temp file is removed
```

Zero dependencies, Python 3.9+, works on Linux, macOS and Windows.

## Why not `os.replace` alone

`os.replace` is atomic, but a temporary file that was never flushed can still be
empty after a power loss, and the rename is only durable once the directory entry is
flushed too. Both are done here. `atomicwrites` stopped at the same problem in 2022
and does not `fsync` the directory.

## Install

```console
pip install fsync-replace
```

## API

### `write_atomic(path, data, mode="w", encoding="utf-8", *, fsync=True, newline=None, preserve_mode=True) -> int`

Writes `str` (text modes) or `bytes` (`mode="wb"`) and returns the number of
characters or bytes written.

- `fsync=False` skips both flushes, for scratch files where durability does not matter.
- `preserve_mode` copies the permission bits of the file being replaced, so a script
  that was `0700` stays `0700`. A new file keeps the default umask.
- A missing parent directory raises `FileNotFoundError` before anything is created.

### `atomic_open(path, mode="w", encoding="utf-8", *, fsync=True, newline=None, preserve_mode=True)`

Context manager yielding an open handle. On a clean exit the file is moved into
place; on an exception the temporary file is removed and the target is left as it
was. The exception is not swallowed.

## Limits

- Durability is per file. Replacing several files is not a transaction; if you need
  that, write a directory and swap it, or use a database.
- `fsync` on the directory is skipped on Windows, where `os.replace` is already
  durable and directories cannot be opened for writing.
- Temporary files are named `.<target>.<random>.tmp` in the same directory, because a
  rename across filesystems is not atomic. A crash in the middle leaves one behind.

## Development

```console
python -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/pytest
```

## License

MIT.
