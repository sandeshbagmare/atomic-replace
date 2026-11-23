<p align="center">
  <img src="https://raw.githubusercontent.com/sandeshbagmare/fsync-replace/main/assets/banner.svg" width="100%" alt="fsync-replace: replace a file so a crash cannot leave it half-written">
</p>

<p align="center">
  <a href="https://pypi.org/project/fsync-replace/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/fsync-replace.svg"></a>
  <a href="https://pypi.org/project/fsync-replace/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/fsync-replace.svg"></a>
  <a href="https://pypi.org/project/fsync-replace/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/fsync-replace.svg"></a>
  <a href="https://github.com/sandeshbagmare/fsync-replace/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/sandeshbagmare/fsync-replace/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/sandeshbagmare/fsync-replace/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/fsync-replace.svg"></a>
  <a href="https://sandeshbagmare.github.io/fsync-replace/"><img alt="docs" src="https://img.shields.io/badge/docs-online-2ea44f.svg"></a>
  <a href="https://pypi.org/project/fsync-replace/"><img alt="zero dependencies" src="https://img.shields.io/badge/dependencies-0-2ea44f.svg"></a>
</p>

<h3 align="center">replace a file so a crash cannot leave it half-written</h3>
<p align="center"><em>Standard library only. No runtime dependencies. Python 3.9+.</em></p>

<p align="center">
  <img src="https://raw.githubusercontent.com/sandeshbagmare/fsync-replace/main/assets/how.svg" width="720" alt="how fsync-replace fits in">
</p>

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

The suite covers every line of the package (`pytest --cov --cov-branch`), and the
examples in the docstrings run as tests through `--doctest-modules`.

## License

MIT.
