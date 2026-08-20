"""CLI wiring for `frob format [path] [--select-imports-only]` (T-2251,
docs/modules/app.md#runners): a write-mode ruff autofix + ruff format pass,
the frob-native replacement for the Makefile's `format`/`lint-fix`/`all`
targets (T-1382's own 21-target classification -- see T-2251's ticket body).

Named `pyfmt_runner`/`frob format` rather than reusing `frob fmt` (T-0441,
`src/frob/app/fmt_runner.py`) because the two are different concerns: `frob
fmt` canonicalizes `frob:` directive comment line-wrapping, this module runs
`ruff check --fix` + `ruff format` against real Python source.

T-2251 found `frob.check._python._run_ruff_autofix` already built (T-2320/
T-2252, exposed as `frob check --fix-ruff`) -- the exact full-rule-set
`ruff check --fix` + `ruff format` write pass this module's default
(no-flag) path needs. Rather than duplicate that subprocess plumbing, this
module CALLS it directly for the default case and adds only the one thing
`_run_ruff_autofix` does not have: a `--select-imports-only` narrowing of
the `ruff check --fix` stage to `--select I` (the Makefile `format:`
target's scope, vs `lint-fix:`'s full-rule-set scope) -- see
`_run_ruff_check_fix_select_imports`."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.check._python import _run_ruff_autofix
from frob.logging import get_logger
from frob.process._guard import EXEC_KILL_SWITCH_ENV, guarded_subprocess_run
from frob.process.parsers.common import (
    ToolResult,
    tool_disabled_result,
    tool_unavailable_result,
)
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-2251
# frob:doc docs/modules/app.md#runners
# frob:tests tests/unit/test_pyfmt_runner.py::TestRun.test_select_imports_only_uses_dash_dash_select_i  # noqa: E501
# frob:tests tests/unit/test_pyfmt_runner.py::TestRun.test_default_delegates_to_run_ruff_autofix  # noqa: E501
# frob:tests tests/unit/test_pyfmt_runner.py::TestRun.test_nonzero_exit_propagates  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob format`: `ruff check --fix` (all rules by default, or `--select
    I` only when `cfg.format_select_imports_only`) followed by `ruff
    format`, both write-mode. Delegates the default (all-rules) case to the
    existing `frob.check._python._run_ruff_autofix` (T-2320/T-2252) rather
    than re-issuing the same two subprocess calls -- see this module's
    docstring. Replaces the Makefile's `format`/`lint-fix` targets: `format:`
    becomes `frob format --select-imports-only`, `lint-fix:` becomes plain
    `frob format` (T-2251's ticket body). Exits nonzero if either stage
    fails."""
    root = (cfg.format_path or Path(".")).resolve()
    if cfg.format_select_imports_only:
        results = [
            _run_ruff_check_fix_select_imports(root),
            *_ruff_format_write_only(root),
        ]
    else:
        results = _run_ruff_autofix(root)

    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    r.write.heading('frob format')
    r.blank()
    failed = False
    for result in results:
        if result.passed:
            r.write.good(f'{result.tool}: {result.summary or "ok"}')
        else:
            failed = True
            r.write.critical(f'{result.tool}: {result.summary or "failed"}')
            for diag in result.diagnostics:
                r.write.kv('  ', diag.message)
    r.blank()

    if failed:
        sys.exit(1)


# frob:ticket T-2251
# frob:tests tests/unit/test_pyfmt_runner.py::TestRunRuffCheckFixSelectImports.test_missing_binary_yields_typed_result  # noqa: E501
def _run_ruff_check_fix_select_imports(root: Path) -> ToolResult:
    """`ruff check --fix --select I` against `root` -- the narrower,
    import-sort-only fix scope the Makefile `format:` target uses
    (`--select-imports-only`, T-2251), as opposed to `lint-fix:`'s
    full-rule-set `_run_ruff_autofix`. A missing `ruff` binary or the exec
    kill-switch (T-0142/T-0200) is a typed failing `ToolResult`, mirroring
    `_run_ruff_autofix`'s own handling of its first stage."""
    try:
        run_result = guarded_subprocess_run(
            ["uv", "run", "ruff", "check", "--fix", "--select", "I", str(root)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return tool_unavailable_result("ruff-check-fix", "ruff")
    if run_result.is_err:
        return tool_disabled_result("ruff-check-fix", EXEC_KILL_SWITCH_ENV)
    proc = run_result.danger_ok
    msg = (proc.stdout + proc.stderr).strip()
    return ToolResult(
        tool="ruff-check-fix",
        exit_code=proc.returncode,
        summary=msg or "no fixable violations",
    )


# frob:ticket T-2251
# frob:tests tests/unit/test_pyfmt_runner.py::TestRuffFormatWriteOnly.test_missing_binary_yields_typed_result  # noqa: E501
def _ruff_format_write_only(root: Path) -> list[ToolResult]:
    """The `ruff format` (write mode) half of `_run_ruff_autofix`, reused
    standalone for the `--select-imports-only` path (T-2251) since that
    path's `ruff check --fix` stage above is not the full-rule-set one
    `_run_ruff_autofix` bundles its own format stage with. Same typed-
    failure handling as `_run_ruff_autofix`'s second stage."""
    try:
        run_result = guarded_subprocess_run(
            ["uv", "run", "ruff", "format", str(root)], capture_output=True, text=True
        )
    except FileNotFoundError:
        return [tool_unavailable_result("ruff-format-write", "ruff")]
    if run_result.is_err:
        return [tool_disabled_result("ruff-format-write", EXEC_KILL_SWITCH_ENV)]
    proc = run_result.danger_ok
    msg = (proc.stdout + proc.stderr).strip()
    return [
        ToolResult(
            tool="ruff-format-write",
            exit_code=proc.returncode,
            summary=msg or "no files reformatted",
        )
    ]
