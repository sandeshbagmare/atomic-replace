"""Tests for fsync_replace."""

import os
import stat
from pathlib import Path

import pytest

from fsync_replace import atomic_open, write_atomic


class TestWriteAtomic:
    def test_writes_text_and_returns_the_length(self, tmp_path):
        target = tmp_path / "report.txt"
        assert write_atomic(target, "hello") == 5
        assert target.read_text(encoding="utf-8") == "hello"

    def test_writes_bytes(self, tmp_path):
        target = tmp_path / "blob.bin"
        assert write_atomic(target, b"\x00\x01\x02", mode="wb") == 3
        assert target.read_bytes() == b"\x00\x01\x02"

    def test_replaces_an_existing_file(self, tmp_path):
        target = tmp_path / "report.txt"
        target.write_text("old", encoding="utf-8")
        write_atomic(target, "new and longer")
        assert target.read_text(encoding="utf-8") == "new and longer"

    @pytest.mark.skipif(os.name == "nt", reason="os.chmod only toggles read-only on Windows")
    def test_keeps_the_existing_permissions(self, tmp_path):
        target = tmp_path / "script.sh"
        target.write_text("old", encoding="utf-8")
        os.chmod(target, 0o600)
        write_atomic(target, "new")
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    @pytest.mark.skipif(os.name == "nt", reason="os.chmod only toggles read-only on Windows")
    def test_can_skip_the_mode_copy(self, tmp_path):
        target = tmp_path / "report.txt"
        target.write_text("old", encoding="utf-8")
        os.chmod(target, 0o600)
        write_atomic(target, "new", preserve_mode=False)
        assert stat.S_IMODE(target.stat().st_mode) != 0o600

    def test_leaves_no_temporary_file_behind(self, tmp_path):
        write_atomic(tmp_path / "report.txt", "hello")
        assert [p.name for p in tmp_path.iterdir()] == ["report.txt"]

    def test_newline_is_honoured(self, tmp_path):
        target = tmp_path / "lines.txt"
        write_atomic(target, "a\nb\n", newline="\r\n")
        assert target.read_bytes() == b"a\r\nb\r\n"

    def test_missing_directory_raises_before_touching_anything(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            write_atomic(tmp_path / "nope" / "report.txt", "hello")

    def test_binary_mode_rejects_text(self, tmp_path):
        with pytest.raises(TypeError):
            write_atomic(tmp_path / "x.bin", "text", mode="wb")

    def test_text_mode_rejects_bytes(self, tmp_path):
        with pytest.raises(TypeError):
            write_atomic(tmp_path / "x.txt", b"bytes", mode="w")


class TestDurability:
    def test_fsyncs_the_file_and_the_directory(self, tmp_path, monkeypatch):
        synced = []
        real_fsync = os.fsync
        real_open = os.open
        real_close = os.close

        monkeypatch.setattr(
            "fsync_replace.os.fsync", lambda fd: (synced.append(fd), real_fsync(fd))[1]
        )
        monkeypatch.setattr("fsync_replace.os.open", lambda *a, **k: real_open(*a, **k))
        monkeypatch.setattr("fsync_replace.os.close", lambda fd: real_close(fd))

        write_atomic(tmp_path / "report.txt", "hello")
        # One fsync for the file, and on POSIX one more for the directory entry.
        expected = 1 if os.name == "nt" else 2
        assert len(synced) == expected

    def test_fsync_can_be_turned_off(self, tmp_path, monkeypatch):
        def boom(fd):  # pragma: no cover - must not run
            raise AssertionError("fsync must not be called")

        monkeypatch.setattr("fsync_replace.os.fsync", boom)
        write_atomic(tmp_path / "report.txt", "hello", fsync=False)
        assert (tmp_path / "report.txt").read_text(encoding="utf-8") == "hello"


class TestAtomicOpen:
    def test_writes_when_the_block_succeeds(self, tmp_path):
        target = tmp_path / "report.txt"
        with atomic_open(target) as handle:
            handle.write("hello")
            handle.write(" there")
        assert target.read_text(encoding="utf-8") == "hello there"

    def test_leaves_the_target_alone_when_the_block_raises(self, tmp_path):
        target = tmp_path / "report.txt"
        target.write_text("keep me", encoding="utf-8")
        with pytest.raises(RuntimeError), atomic_open(target) as handle:
            handle.write("partial")
            raise RuntimeError("boom")
        assert target.read_text(encoding="utf-8") == "keep me"
        assert [p.name for p in tmp_path.iterdir()] == ["report.txt"]

    def test_creates_the_file_when_it_did_not_exist(self, tmp_path):
        target = tmp_path / "new.txt"
        with atomic_open(target) as handle:
            handle.write("fresh")
        assert target.read_text(encoding="utf-8") == "fresh"

    def test_binary_mode(self, tmp_path):
        target = tmp_path / "blob.bin"
        with atomic_open(target, "wb") as handle:
            handle.write(b"\x00\xff")
        assert target.read_bytes() == b"\x00\xff"

    def test_accepts_a_string_path(self, tmp_path):
        target = str(tmp_path / "report.txt")
        write_atomic(target, "hello")
        assert Path(target).read_text(encoding="utf-8") == "hello"
