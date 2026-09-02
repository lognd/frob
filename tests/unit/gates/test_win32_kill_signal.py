"""Tests for frob.gates._win32_kill_signal -- PLATFORM002
(docs/modules/gates.md#platform002-os-kill-pid-0-outside-the-sanctioned-
liveness-probe-t-3696).

Fixture snippets below are synthetic `tempfile`-backed git repos, same
posture as `tests/test_walk_lint_gate.py`/`tests/test_pii_structural_gate.py`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._win32_kill_signal import win32_kill_signal_gate


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


# frob:waive DUP001 reason="the same tiny git-init-a-synthetic-tmp-repo fixture helper \
# repeated verbatim across ~15 sibling gate test modules (test_walk_lint_gate.py, \
# test_pii_structural_gate.py, test_secrets_gate.py, ...) -- an established \
# test-fixture convention, not real duplication worth a shared import across \
# independently-owned test files for this ticket"
def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str = "commit") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _write_offender(tmp_path: Path, src: str, filename: str = "offender.py") -> Path:
    pkg = tmp_path / "src" / "frob"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("")
    path = pkg / filename
    path.write_text(src)
    return path


class TestPlatform002:
    """PLATFORM002: `os.kill(<pid>, 0)` fires outside the sanctioned
    `frob.process._pid_liveness` module; a real signal never fires; the
    sanctioned module itself is allowlisted; an unparseable file fires
    PARSE001 rather than silently dropping; frob's own tree is clean."""

    # frob:tests src/frob/gates/_win32_kill_signal.py::win32_kill_signal_gate
    def test_zero_signal_kill_is_flagged(self, tmp_path: Path) -> None:
        """The T-3686 shape: a dotted `os.kill(pid, 0)` liveness probe
        outside the sanctioned module must fire PLATFORM002 -- proves
        this is not a check that always finds nothing."""
        _init_repo(tmp_path)
        _write_offender(
            tmp_path,
            "import os\n"
            "\n"
            "def pid_alive(pid: int) -> bool:\n"
            "    try:\n"
            "        os.kill(pid, 0)\n"
            "    except ProcessLookupError:\n"
            "        return False\n"
            "    return True\n",
        )
        _commit(tmp_path)

        violations = win32_kill_signal_gate(tmp_path)

        hits = [v for v in violations if v.rule == "PLATFORM002"]
        assert len(hits) == 1
        assert hits[0].file == "src/frob/offender.py"
        assert hits[0].line == 5

    # frob:tests src/frob/gates/_win32_kill_signal.py::win32_kill_signal_gate
    def test_real_signal_kill_is_not_flagged(self, tmp_path: Path) -> None:
        """Genuine signal delivery (`signal.SIGTERM`, not a liveness
        probe) must never flag -- proves this is not an "os.kill anywhere"
        nag rule."""
        _init_repo(tmp_path)
        _write_offender(
            tmp_path,
            "import os\n"
            "import signal\n"
            "\n"
            "def terminate(pid: int) -> None:\n"
            "    os.kill(pid, signal.SIGTERM)\n",
        )
        _commit(tmp_path)

        violations = win32_kill_signal_gate(tmp_path)

        assert not [v for v in violations if v.rule == "PLATFORM002"]

    # frob:tests src/frob/gates/_win32_kill_signal.py::win32_kill_signal_gate
    def test_sanctioned_module_is_allowlisted(self, tmp_path: Path) -> None:
        """`src/frob/process/_pid_liveness.py` -- the one sanctioned
        implementation -- must never self-flag its own legitimate POSIX
        `os.kill(pid, 0)` branch."""
        _init_repo(tmp_path)
        process_dir = tmp_path / "src" / "frob" / "process"
        process_dir.mkdir(parents=True)
        (tmp_path / "src" / "frob").mkdir(exist_ok=True)
        (tmp_path / "src" / "frob" / "__init__.py").write_text("")
        (process_dir / "__init__.py").write_text("")
        (process_dir / "_pid_liveness.py").write_text(
            "import os\n"
            "\n"
            "def pid_alive(pid: int) -> bool:\n"
            "    try:\n"
            "        os.kill(pid, 0)\n"
            "    except ProcessLookupError:\n"
            "        return False\n"
            "    return True\n"
        )
        _commit(tmp_path)

        violations = win32_kill_signal_gate(tmp_path)

        assert not [v for v in violations if v.rule == "PLATFORM002"]

    # frob:waive DUP002 reason="deliberately near-identical to \
    # test_zero_signal_kill_is_flagged -- same assertion shape proving the SAME rule \
    # fires for the dotted vs. bare-imported call spelling, which is the whole point \
    # of having both as separate cases rather than one parametrized test"
    # frob:tests src/frob/gates/_win32_kill_signal.py::win32_kill_signal_gate
    def test_bare_imported_kill_is_flagged(self, tmp_path: Path) -> None:
        """A `from os import kill` bare-name binding, proven via
        `_collect_kill_bindings`, must fire the same as the dotted form --
        not just the `os.kill(...)` spelling."""
        _init_repo(tmp_path)
        _write_offender(
            tmp_path,
            "from os import kill\n"
            "\n"
            "def pid_alive(pid: int) -> bool:\n"
            "    try:\n"
            "        kill(pid, 0)\n"
            "    except ProcessLookupError:\n"
            "        return False\n"
            "    return True\n",
        )
        _commit(tmp_path)

        violations = win32_kill_signal_gate(tmp_path)

        hits = [v for v in violations if v.rule == "PLATFORM002"]
        assert len(hits) == 1

    # frob:tests src/frob/gates/_win32_kill_signal.py::win32_kill_signal_gate
    def test_unparseable_file_is_parse001_not_silent(self, tmp_path: Path) -> None:
        """A file this gate cannot `ast.parse` fires PARSE001 rather than
        silently dropping out of the scan -- matches WALK001/PORT001's
        own convention."""
        _init_repo(tmp_path)
        _write_offender(tmp_path, "def broken(:\n    pass\n")
        _commit(tmp_path)

        violations = win32_kill_signal_gate(tmp_path)

        assert [v for v in violations if v.rule == "PARSE001"]
        assert not [v for v in violations if v.rule == "PLATFORM002"]

    def test_frob_itself_is_clean(self) -> None:
        """Positive control against this repo's own real tree (T-3686
        already delegated the one production pid-liveness call site to
        the sanctioned module): PLATFORM002 must report zero findings
        here, proving the exemption and the fix both hold together --
        not merely in isolation against a synthetic fixture.

        T-3698 disclosed residual: `frob.gates._fix_engine_shared.
        _pid_alive` is a second, still-live `os.kill(pid, 0)` call site
        this rule legitimately flags and a `frob:waive PLATFORM002`
        directive there keeps repo-wide `frob check` green until T-3698
        lands; this in-process assertion targets ONLY the scan surface
        this ticket actually changed, so it asserts zero raw hits
        (pre-waiver) against the two known, disclosed exceptions instead
        of the full repo count."""
        root = Path(__file__).resolve().parents[3]
        violations = win32_kill_signal_gate(root)
        unexpected = [
            v
            for v in violations
            if v.rule == "PLATFORM002"
            and v.file != "src/frob/gates/_fix_engine_shared.py"
        ]
        assert unexpected == []
