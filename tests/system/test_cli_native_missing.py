"""End-to-end litmus for T-0316: when a repo's `design/**` actually uses
`.strata` and the `strata_core` native extension is missing (the bare
`uv tool install frob` gotcha, FROBLEMS aprog-public), `frob check` and
`frob sys audit` must FAIL LOUDLY -- a clear nonzero exit naming the
missing extension and the exact remediation -- never silently degrade to
an unwaived-looking pass. A repo with no `.strata` files at all must be
completely unaffected by the same missing extension (T-0134/T-0135's
opt-in posture): `sys_gate` must never even import `frob.strata` for such
a repo, so it cannot regress just because natives are absent.

`tests/fixtures/fake_no_native/strata_core.py` shadows the real compiled
extension via `PYTHONPATH` order, so this exercises the real subprocess
CLI path end to end (`python -m frob ...`), not a monkeypatched import --
the strongest available proof for this repo's `uv build --wheel` /
`uv tool install` gap, since actually uninstalling the compiled wheel from
this worktree's own `.venv` would break every other test that runs after.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.system.conftest import git as _git

FROB = [sys.executable, "-m", "frob"]

_FAKE_NATIVE_DIR = str(Path(__file__).parent.parent / "fixtures" / "fake_no_native")

_CLEAN_MODEL = """\
module m
node evil : foreign
node api : trusted
flow f1 : evil -> api { rate 5 req/s; }
"""


def _run_with_faked_missing_native(
    *args: str, cwd: Path
) -> subprocess.CompletedProcess:
    """Run `frob <args>` in a subprocess whose `PYTHONPATH` shadows the real
    `strata_core` with the raise-on-import fixture, so the process sees
    exactly what a natives-less `uv tool install frob` sees.

    `FROB_AGENT`/`FROB_WORKTREE` are stripped from the child's env (T-0708):
    this subprocess runs `frob check`/`frob sys audit` against a throwaway
    `tmp_path` fixture repo, not the dispatching agent's own worktree --
    inheriting `FROB_AGENT=1` from a dispatched-agent host process makes the
    bare, unchunked `frob check` call below hit section 3b's unrelated
    full-check refusal (`ERROR: frob check: refusing a full/unchunked run
    under FROB_AGENT`) instead of exercising the SYS004 contract this test
    actually verifies -- a real false failure observed when this suite runs
    under `frob ticket evidence`/`close`, which propagate the dispatching
    agent's own env into every subprocess it spawns."""
    env = dict(os.environ)
    env.pop("FROB_AGENT", None)
    env.pop("FROB_WORKTREE", None)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        _FAKE_NATIVE_DIR
        if not existing
        else f"{_FAKE_NATIVE_DIR}{os.pathsep}{existing}"
    )
    return subprocess.run(
        FROB + list(args), cwd=cwd, capture_output=True, text=True, env=env
    )


def _init_design_repo(tmp_path: Path, model: str) -> Path:
    """A minimal frob-enabled repo with one `.strata` design file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "tickets.md").write_text("# Tickets\n")
    (repo / "pyproject.toml").write_text('[project]\nname = "m"\nversion = "0.1.0"\n')
    (repo / "design").mkdir()
    (repo / "design" / "m.strata").write_text(model)
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


def _init_no_design_repo(tmp_path: Path) -> Path:
    """A minimal frob-enabled repo with no `design/` dir at all -- must be
    completely unaffected by a missing native extension (T-0135 opt-in)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "tickets.md").write_text("# Tickets\n")
    (repo / "pyproject.toml").write_text('[project]\nname = "p"\nversion = "0.1.0"\n')
    (repo / "frob.toml").write_text(
        "[gates.severity]\n"
        'COV001 = "warn"\nTEST001 = "warn"\nTEST002 = "warn"\n'
        'TEST003 = "warn"\nTEST005 = "warn"\nTEST006 = "warn"\n'
    )
    src_dir = repo / "src" / "p"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text(
        "def add(x: int, y: int) -> int:\n    return x + y\n"
    )
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


class TestNativeMissingFailsLoud:
    def test_sys_audit_fails_loud_when_strata_present(self, tmp_path: Path) -> None:
        """`frob sys audit` on a repo that actually has `.strata` files must
        exit nonzero and name the missing extension + remediation, never
        silently degrade to an unwaived SYS004 pass."""
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        r = _run_with_faked_missing_native("sys", "audit", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "NativeExtensionUnavailable" in out or "native extension" in out, out

    def test_check_fails_loud_with_sys004_when_strata_present(
        self, tmp_path: Path
    ) -> None:
        """`frob check` on a repo with `.strata` under `design/` must exit
        nonzero, naming SYS004, instead of silently reporting a clean pass
        because the design model degraded to zero errors it forgot to
        report."""
        repo = _init_design_repo(tmp_path, _CLEAN_MODEL)
        r = _run_with_faked_missing_native("check", str(repo), cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "SYS004" in out, out
        assert "native extension" in out, out

    def test_check_unaffected_when_no_strata_files(self, tmp_path: Path) -> None:
        """T-0135: a repo that never opted into `design/**` must pass `frob
        check` exactly the same with or without the native extension --
        `sys_gate` never even imports `frob.strata` for such a repo."""
        repo = _init_no_design_repo(tmp_path)
        r = _run_with_faked_missing_native(
            "check", str(repo), "--skip-tests", "--skip-exports", cwd=repo
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "SYS004" not in out
