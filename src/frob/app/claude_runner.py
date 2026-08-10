"""CLI wiring for `frob claude sync [--check]` (T-1808): fold the loose
`.claude/hooks/sync-claude-config.py` script into a real frob verb, and
(`drift_warning`) surface drift automatically on every `frob` invocation.

T-1719 item 1 cut this into its own ticket: a verb that reads a managed-
file manifest and replaces the loose script, writing each destination
behind the do-not-edit banner atomically, `--check` naming every drifted
path, never syncing global -> repo.

NO DUPLICATION: `.claude/hooks/sync-claude-config.py` stays the canonical,
dependency-free implementation (stdlib only -- the SessionStart hook in
`.claude/settings.json` invokes it with a bare `python3` before any `frob`
venv is necessarily on `PYTHONPATH`). This module is a thin adapter that
loads that script by file path (its hyphenated name blocks a normal
`import`) and calls its public `MANAGED`/`plan()`/`main()` -- there is
exactly one implementation of the sync/drift logic, never two that can
desync.

STANDING DESIGN DIRECTIVE this module answers to directly: "a command
requires knowledge of the command" -- so this verb is the MECHANISM, not
the user-facing answer. The user-facing answer is `drift_warning`, wired
into `frob.__main__.main()` next to `stale_install_warning`/
`stale_binary_warning`: detection is automatic on every invocation,
surfaced where an operator already looks (stderr on every `frob` command),
with no write. Auto-writing into `~/.claude/` on every invocation was
rejected -- it is a destructive-ish action outside the repo, and a command
people run constantly is the wrong place for a surprising, hard-to-reverse
mutation of the operator's home directory. The WRITE stays this explicit
verb; only the DETECTION is automatic. `frob check`'s own gate (T-1809)
is the pre-land enforcement half of the same signal.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_HOOK_REL = Path(".claude") / "hooks" / "sync-claude-config.py"


def _load_sync_module(repo_root: Path) -> ModuleType | None:
    """Load `.claude/hooks/sync-claude-config.py` from `repo_root` by file
    path -- its hyphenated filename blocks a normal `import`, and it must
    STAY hyphenated so the SessionStart hook's own `python3 .claude/hooks/
    sync-claude-config.py` invocation keeps working unmodified. `None` if
    `repo_root` has no such file (not every repo using frob owns this
    script -- this is a no-op there, not an error)."""
    path = repo_root / _HOOK_REL
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("_frob_claude_sync", path)
    if spec is None or spec.loader is None:  # pragma: no cover -- defensive
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# frob:ticket T-1808
# frob:doc docs/modules/cli.md#frob-claude-sync-t-1808
# frob:tests \
# tests/unit/test_claude_runner.py::TestDriftReport.test_reports_drifted_and_missing
def drift_report(repo_root: Path) -> tuple[list[str], list[str]] | None:
    """`(drifted_entries, missing_sources)` for `repo_root`'s
    `sync-claude-config.py`-managed files, or `None` if `repo_root` has no
    such script at all -- matches `stale_install_warning`'s own "not this
    repo" `None` convention (`frob.app._config_meta`)."""
    module = _load_sync_module(repo_root)
    if module is None:
        return None
    actions, missing = module.plan()
    return [entry for entry, _dest, _want in actions], missing


# frob:ticket T-1808
# frob:tests \
# tests/unit/test_claude_runner.py::TestDriftWarning.test_warns_when_managed_file_diffe\
# rs
# frob:tests tests/unit/test_claude_runner.py::TestDriftWarning.test_none_when_in_sync
def drift_warning(repo_root: Path) -> str | None:
    """A loud, one-line warning if any `sync-claude-config.py`-managed file
    has drifted from its `~/.claude/` materialized copy -- the T-1808
    "surfaced where the operator already looks" answer (mirrors
    `stale_install_warning`/`stale_binary_warning`): detection runs on
    every `frob` invocation, the WRITE stays the explicit `frob claude
    sync` call below. `None` when there is nothing to warn about, or the
    probe itself fails (best-effort startup check, never fatal)."""
    try:
        report = drift_report(repo_root)
    except Exception as exc:  # noqa: BLE001 -- best-effort startup probe, never fatal
        _log.debug("drift_warning: unresolvable drift probe failed: %s", exc)
        return None
    if report is None:
        return None
    drifted, missing = report
    if not drifted and not missing:
        return None
    return (
        f"Claude config DRIFT: {len(drifted)} managed file(s) differ from "
        f"~/.claude, {len(missing)} source(s) missing -- reconcile with "
        "`frob claude sync`"
    )


# frob:ticket T-1808
# frob:doc docs/modules/cli.md#frob-claude-sync-t-1808
# frob:tests tests/unit/test_claude_runner.py::TestRun.test_check_mode_exits_1_on_drift
# frob:tests tests/unit/test_claude_runner.py::TestRun.test_sync_writes_managed_files
def run(cfg: AppConfig) -> None:
    """`frob claude sync [--check]`: materialize this repo's git-tracked
    Claude config out to `~/.claude/` (default), or report drift without
    writing (`--check`, exits 1 if any managed file differs or is
    missing)."""
    if cfg.claude_command != "sync":
        _log.error(
            "usage: frob claude sync [--check] (got action=%r)", cfg.claude_command
        )
        sys.exit(1)
    root = Path.cwd()
    module = _load_sync_module(root)
    if module is None:
        _log.error(
            "frob claude sync: no %s in %s -- this repo does not own a "
            "managed Claude config",
            _HOOK_REL,
            root,
        )
        sys.exit(1)
    exit_code = module.main(["--check"] if cfg.claude_check else [])
    if exit_code:
        sys.exit(exit_code)
