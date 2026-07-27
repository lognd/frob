"""CLI wiring for `frob natives` -- frob-owned native crate builds (T-0864).

`build` is the action wired today (`maturin develop` per declared
`[[native]]` rust crate, shared `CARGO_TARGET_DIR`); routed through `frob.render`/
`_log.info`/`_log.error` instead of a bare `print`, matching every other
runner (RENDER001 forbids bare stdout writes outside `frob.render`)."""

from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.natives import NativesError, build_natives

_log = get_logger(__name__)


# frob:ticket T-0864
# frob:doc docs/modules/cli.md#frob-natives-build-t-0864
# frob:tests \
# tests/unit/test_natives_build.py::TestNativesRunner.test_build_reports_success
def run(cfg: AppConfig) -> None:
    """`frob natives build`: build every declared rust `[[native]]` crate
    into the active venv, sharing one git-common-dir-keyed
    `CARGO_TARGET_DIR` across every worktree of this clone (T-0732). Exits
    non-zero (via `SystemExit`, the convention every other runner facing a
    hard failure uses) on an infrastructure-level failure or if any
    attempted crate failed to build; each failing crate's captured
    stdout/stderr is logged before exit so the failure is diagnosable
    without re-running by hand."""
    if cfg.natives_command != "build":
        _log.error("frob natives: unknown or missing action %r", cfg.natives_command)
        raise SystemExit(2)

    root = cfg.natives_path or Path(".")
    result = build_natives(root)
    if result.is_err:
        error = result.danger_err
        if error is NativesError.NoNatives:
            _log.info(
                "frob natives build: no [[native]] entries declared, nothing to do"
            )
            return
        _log.error("frob natives build: %s", error.value)
        raise SystemExit(1)

    report = result.danger_ok
    for crate in report.results:
        if crate.ok:
            _log.info("frob natives build: %s built cleanly", crate.name)
        else:
            _log.error(
                "frob natives build: %s failed (exit %d)\n%s",
                crate.name,
                crate.returncode,
                crate.stderr or crate.stdout,
            )
    if not report.results:
        _log.info(
            "frob natives build: no rust [[native]] crate had a matching "
            "directory under %s, nothing built",
            root,
        )
    if not report.ok:
        raise SystemExit(1)
