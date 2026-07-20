"""End-to-end tests for `frob graph` and `frob ack` (docs/modules/graph.md)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    _git("init", "-q", cwd=tmp_path)
    _git("config", "user.email", "test@example.com", cwd=tmp_path)
    _git("config", "user.name", "Test", cwd=tmp_path)
    src = tmp_path / "pkg.py"
    src.write_text(
        "def add(x: int, y: int) -> int:\n"
        "    # frob:doc docs/x.md#add\n"
        "    return x + y\n"
    )
    _git("add", "-A", cwd=tmp_path)
    _git("commit", "-q", "-m", "init", cwd=tmp_path)
    return tmp_path


def _commit_all(tmp_path: Path, message: str) -> None:
    _git("add", "-A", cwd=tmp_path)
    _git("commit", "-q", "-m", message, cwd=tmp_path)


class TestGraphBuild:
    def test_build_reports_stats(self, tmp_path):
        _init_repo(tmp_path)
        r = run("graph", "build", str(tmp_path))
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "symbols=" in out
        assert "edges=" in out


class TestGraphQuery:
    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_query_known_ref(self, tmp_path):
        _init_repo(tmp_path)
        run("graph", "build", str(tmp_path))
        r = run("graph", "query", "pkg.py::add", str(tmp_path))
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "add" in out

    def test_query_unknown_ref_exits_1(self, tmp_path):
        _init_repo(tmp_path)
        run("graph", "build", str(tmp_path))
        r = run("graph", "query", "pkg.py::does_not_exist", str(tmp_path))
        assert r.returncode != 0


class TestGraphWhy:
    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_why_unacked_ref(self, tmp_path):
        _init_repo(tmp_path)
        run("graph", "build", str(tmp_path))
        r = run("graph", "why", "pkg.py::add", str(tmp_path))
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "add" in out

    def test_why_unknown_ref_exits_1(self, tmp_path):
        _init_repo(tmp_path)
        run("graph", "build", str(tmp_path))
        r = run("graph", "why", "pkg.py::nope", str(tmp_path))
        assert r.returncode != 0


class TestAck:
    def test_ack_then_requery_clean(self, tmp_path):
        _init_repo(tmp_path)
        run("graph", "build", str(tmp_path))
        r = run("ack", "pkg.py::add", "--path", str(tmp_path))
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        lock = tmp_path / "frob.lock"
        assert lock.exists()
        assert "add" in lock.read_text()

    def test_ack_then_drift_after_change(self, tmp_path):
        _init_repo(tmp_path)
        run("graph", "build", str(tmp_path))
        ack = run("ack", "pkg.py::add", "--path", str(tmp_path))
        assert ack.returncode == 0, ack.stdout + ack.stderr

        (tmp_path / "pkg.py").write_text(
            "def add(x: int, y: int, z: int) -> int:\n"
            "    # frob:doc docs/x.md#add\n"
            "    return x + y + z\n"
        )
        _commit_all(tmp_path, "change signature")
        run("graph", "build", str(tmp_path))
        r = run("graph", "why", "pkg.py::add", str(tmp_path))
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "STALE" in out or "stale" in out.lower()

    def test_ack_unknown_ref_exits_1(self, tmp_path):
        _init_repo(tmp_path)
        run("graph", "build", str(tmp_path))
        r = run("ack", "pkg.py::totally_unknown", "--path", str(tmp_path))
        assert r.returncode != 0
