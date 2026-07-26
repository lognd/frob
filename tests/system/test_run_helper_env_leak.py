"""
T-0880 regression coverage: the shared `run()` helper in
`tests/system/conftest.py` must strip `FROB_AGENT`/`FROB_WORKTREE` from its
own base environment before merging, so a dispatched worktree agent's own
shell-level lease env (set per the agent playbook, for `frob check`/`frob
ticket` gate commands) never leaks into a system test's subprocess. These
tests simulate an end user invoking the CLI directly, never a dispatched
agent.
"""

from pathlib import Path

from tests.system.conftest import git, git_init_and_config, run

PY_SOURCE = "def add(x: int, y: int) -> int:\n    return x + y\n"


def _make_project(tmp_path: Path, source: str, pkg: str = "mypkg") -> Path:
    """Build a minimal git-tracked Python frob project at `tmp_path` for a
    `frob check` subprocess call (mirrors `test_cli_check.py`'s own
    `_make_project` fixture shape, T-0806/T-0750: a real `pyproject.toml`
    and a committed git repo, so `frob check` recognizes the project type
    and its diff-scoped gates do not error on a git-less/uncommitted
    tree)."""
    git_init_and_config(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "{pkg}"\nversion = "0.1.0"\n'
        '[tool.ruff.lint]\nselect = ["E", "F", "W"]\n'
    )
    src_dir = tmp_path / "src" / pkg
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text(source)
    git("add", "-A", cwd=tmp_path)
    git("commit", "-q", "-m", "init", cwd=tmp_path)
    return tmp_path


class TestRunHelperEnvLeak:
    """`run()` must not let a dispatching agent's own FROB_AGENT/
    FROB_WORKTREE leak into the CLI subprocess it spawns for a test."""

    # frob:ticket T-0880
    def test_run_strips_dispatch_agent_env_vars(self, tmp_path, monkeypatch):
        # frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_strips_dispatch_agent_env_vars  # noqa: E501
        monkeypatch.setenv("FROB_AGENT", "1")
        monkeypatch.setenv("FROB_WORKTREE", str(tmp_path))
        _make_project(tmp_path, PY_SOURCE)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            "--only",
            "lint",
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "FROB_AGENT" not in out

    # frob:ticket T-0880
    def test_run_explicit_env_can_still_set_frob_agent(self, tmp_path):
        # frob:tests tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak.test_run_explicit_env_can_still_set_frob_agent  # noqa: E501
        _make_project(tmp_path, PY_SOURCE)
        r = run(
            "check",
            str(tmp_path),
            "--skip-tests",
            env={"FROB_AGENT": "1"},
        )
        out = r.stdout + r.stderr
        assert r.returncode == 1, out
        assert "FROB_AGENT" in out
