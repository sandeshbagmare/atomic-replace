# Changelog

- 0.1.2 — ship a `py.typed` marker; the docstring examples now run in the test suite.

## 0.1.1

- Badges in the README, shared by the GitHub and PyPI pages.

## 0.1.0

First release.

- `write_atomic` writes str or bytes through a temporary file, fsyncs it, renames it
  over the target and fsyncs the directory entry.
- `atomic_open` is the context manager form: it leaves the target untouched when the
  block raises.
- Existing permission bits are kept, and `preserve_mode=False` opts out.
