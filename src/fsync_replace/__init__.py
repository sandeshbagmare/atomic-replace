"""Replace files atomically, and make sure the replacement survives a crash.

Writing a file in place means a crash, a full disk or a kill signal can leave it
half written. This package writes a temporary file next to the target, flushes it
to the disk with ``fsync``, renames it over the target, and then flushes the
directory entry as well, so a reader either sees the old file or the new one.

    >>> from fsync_replace import write_atomic
    >>> write_atomic("report.json", '{"ok": true}')  # doctest: +SKIP
    15

    >>> from fsync_replace import atomic_open
    >>> with atomic_open("report.json") as handle:   # doctest: +SKIP
    ...     handle.write('{"ok": true}')
"""

from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Union

__all__ = ["atomic_open", "write_atomic"]

__version__ = "0.1.2"

PathLike = Union[str, "os.PathLike[str]"]


def _fsync_directory(directory: Path) -> None:
    """Flush a directory entry so the rename itself is durable.

    Windows cannot open a directory for this, and does not need to: ``os.replace``
    is already durable there. Failing to open the directory is therefore not an
    error, but a failing ``fsync`` on an opened directory is.
    """
    if os.name == "nt":  # pragma: no cover - depends on the platform
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(str(directory), flags)
    except OSError:  # pragma: no cover - exotic filesystems
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _target_mode(target: Path) -> int | None:
    """The permission bits of the file being replaced, if it exists."""
    try:
        return stat.S_IMODE(os.stat(target).st_mode)
    except FileNotFoundError:
        return None


@contextmanager
def atomic_open(
    path: PathLike,
    mode: str = "w",
    encoding: str | None = "utf-8",
    *,
    fsync: bool = True,
    newline: str | None = None,
    preserve_mode: bool = True,
) -> Iterator[IO]:
    """Open a temporary file and move it over ``path`` if the block succeeds.

    The target is untouched when the block raises: the temporary file is removed
    and the exception propagates.
    """
    if "b" in mode and encoding is not None:
        encoding = None
    target = Path(path)
    parent = target.parent if str(target.parent) else Path(".")
    if not parent.is_dir():
        raise FileNotFoundError(f"directory does not exist: {parent}")

    existing_mode = _target_mode(target) if preserve_mode else None
    # Not opened with "with" here because the temporary name is needed first; the
    # block below still closes it.
    handle = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode=mode,
        encoding=encoding,
        newline=newline,
        dir=str(parent),
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            yield handle
            handle.flush()
            if fsync:
                os.fsync(handle.fileno())
        if existing_mode is not None:
            os.chmod(temp_path, existing_mode)
        os.replace(temp_path, target)
        if fsync:
            _fsync_directory(parent)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def write_atomic(
    path: PathLike,
    data: str | bytes,
    mode: str = "w",
    encoding: str | None = "utf-8",
    *,
    fsync: bool = True,
    newline: str | None = None,
    preserve_mode: bool = True,
) -> int:
    """Write ``data`` to ``path`` atomically and return the number of bytes written."""
    if "b" in mode:
        encoding = None
        if not isinstance(data, bytes):
            raise TypeError("binary mode needs bytes")
    elif isinstance(data, bytes):
        raise TypeError("text mode needs str; pass mode='wb' for bytes")
    with atomic_open(
        path,
        mode=mode,
        encoding=encoding,
        fsync=fsync,
        newline=newline,
        preserve_mode=preserve_mode,
    ) as handle:
        written = handle.write(data)
    return written if isinstance(written, int) else len(data)
