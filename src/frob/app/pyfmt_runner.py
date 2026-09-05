"""CLI wiring for `frob format [path ...] [--code] [--directives] [--check]
[--json] [--select-imports-only] [--include-test-corpora]` (T-3906,
docs/modules/app.md#runners): the consolidated formatting verb.

T-3906 folded the former `frob fmt` (T-0441: `frob:` directive comment
canonical-form wrap/unwrap) into this verb as its `--directives` half,
alongside the pre-existing `--code` half (T-2251: `ruff check --fix` +
`ruff format`). Both names were literally the word "format"/"fmt" for two
different operations, distinguishable only by reading the source -- and only
`fmt` had `--check`, so the code half could only ever run destructively.
`frob fmt` survives as a deprecated alias (`frob.app.fmt_runner`, sunset
2026-12-01, ticket T-3911) for `frob format --directives`, following the
`explore`/`quality`/`design`/`ops` precedent (T-1238/T-1567/T-1568/T-1569) of
keeping every consolidated member usable standalone.

T-2251 found `frob.check._python._run_ruff_autofix`/`_run_ruff` already built
(T-2320/T-2252, exposed as `frob check --fix-ruff`) -- the exact full-rule-set
write and check-only passes the code half's default (no `--select-imports-
only`) path needs. Rather than duplicate that subprocess plumbing, this
module CALLS them directly for the default case and adds only the
`--select-imports-only` narrowing (`ruff check [--fix] --select I`) neither
upstream helper has -- see `_run_ruff_check_fix_select_imports`,
`_run_ruff_check_select_imports_no_fix`, `_ruff_format_write_only`,
`_ruff_format_check_only`.

T-3312 folded in: `format_paths`/`fmt_paths` (this module's CLI dest names,
confusingly close to but distinct from `frob.gates._fmt_directives.
format_paths`, the directive-canonicalization function) take a LIST of
paths, not one -- FMT001's own remediation hint already implied a list."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.check._python import _run_ruff, _run_ruff_autofix
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
# frob:ticket T-3906
# frob:doc docs/modules/app.md#runners
# frob:tests \
# tests/unit/test_pyfmt_runner.py::TestRun.test_select_imports_only_uses_dash_dash_sele\
# ct_i
# frob:tests \
# tests/unit/test_pyfmt_runner.py::TestRun.test_default_delegates_to_run_ruff_autofix
# frob:tests tests/unit/test_pyfmt_runner.py::TestRun.test_nonzero_exit_propagates
# frob:tests \
# tests/unit/test_pyfmt_runner.py::TestRunCheckModeDoesNotWrite.test_check_mode_does_no\
# t_write
# frob:tests \
# tests/unit/test_pyfmt_runner.py::TestRunScopeFlags.test_directives_only_skips_ruff
# frob:tests \
# tests/unit/test_pyfmt_runner.py::TestRunScopeFlags.test_code_only_skips_directives
def run(cfg: AppConfig) -> None:
    """`frob format`: `--code` runs `ruff check --fix` (all rules by
    default, or `--select I` only when `cfg.format_select_imports_only`)
    followed by `ruff format`; `--directives` runs the `frob:` directive
    canonical-form pass (T-0441). Neither flag given runs both (the
    consolidated default). `--check` previews without writing for
    whichever half(ves) ran and exits nonzero if anything is
    non-canonical/unformatted -- T-3906 closed the prior gap where only the
    directive half could do this. Iterates `cfg.format_paths` (T-3312:
    a list, not one path)."""
    do_code, do_directives = _resolve_scope(cfg.format_code, cfg.format_directives)
    paths = [Path(p) for p in (cfg.format_paths or ["."])]

    code_results: list[ToolResult] = []
    if do_code:
        for path in paths:
            code_results.extend(_run_code_half(path.resolve(), cfg))

    directive_changes: list = []  # frob.gates._fmt_directives.FmtChange
    if do_directives:
        from frob.gates._fmt_directives import format_paths as canonicalize_directives

        for path in paths:
            report = canonicalize_directives(
                path.resolve(),
                check_only=cfg.format_check,
                include_test_corpora=cfg.format_include_test_corpora,
            )
            directive_changes.extend(report.changes)

    if cfg.format_json:
        import json

        payload = {
            "code": [r.model_dump() for r in code_results] if do_code else None,
            "directives": (
                {"changes": [c.model_dump() for c in directive_changes]}
                if do_directives
                else None
            ),
        }
        _log.info(json.dumps(payload, indent=2, default=str))
    else:
        _render_human(cfg, code_results, directive_changes, do_code, do_directives)

    code_failed = any(not r.passed for r in code_results)
    directives_failed = bool(cfg.format_check and directive_changes)
    if code_failed or directives_failed:
        sys.exit(1)


# frob:ticket T-3906
def _resolve_scope(format_code: bool, format_directives: bool) -> tuple[bool, bool]:
    """T-3906: `--code`/`--directives` scope which half of `frob format`
    runs. Neither flag set means "run both" (the pre-consolidation
    default, and the only way to reach the old `lint-fix:`-equivalent
    all-in-one behavior); either flag set alone means "only that half"."""
    if not format_code and not format_directives:
        return True, True
    return format_code, format_directives


# frob:ticket T-3906
def _run_code_half(root: Path, cfg: AppConfig) -> list[ToolResult]:
    """The ruff (code) half of `frob format` for one resolved `root`:
    write-mode (the pre-T-3906 behavior) unless `cfg.format_check`, in
    which case nothing is written and a non-clean tree is reported instead
    -- the capability T-3906 closed (`frob format` previously had no
    check-only mode at all)."""
    if cfg.format_select_imports_only:
        if cfg.format_check:
            return [
                _run_ruff_check_select_imports_no_fix(root),
                _ruff_format_check_only(root),
            ]
        return [
            _run_ruff_check_fix_select_imports(root),
            *_ruff_format_write_only(root),
        ]
    if cfg.format_check:
        return _run_ruff(root, None)
    return _run_ruff_autofix(root)


# frob:ticket T-3906
def _render_human(
    cfg: AppConfig,
    code_results: list[ToolResult],
    directive_changes: list,
    do_code: bool,
    do_directives: bool,
) -> None:
    """Human-readable `frob format` report covering whichever half(ves)
    ran, replacing the two separate `frob fmt`/`frob format` headings with
    one (T-3906)."""
    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    r.write.heading("frob format")
    r.blank()
    if do_code:
        for result in code_results:
            if result.passed:
                r.write.good(f"{result.tool}: {result.summary or 'ok'}")
            else:
                r.write.critical(f"{result.tool}: {result.summary or 'failed'}")
                for diag in result.diagnostics:
                    r.write.kv("  ", diag.message)
        r.blank()
    if do_directives:
        if not directive_changes:
            r.write.good("all frob: directive lines already canonical")
        for change in directive_changes:
            verb = "would rewrite" if cfg.format_check else "rewrote"
            r.write.kv(f"  {verb}", change.path)
        verb = "would change" if cfg.format_check else "changed"
        r.line(f"{len(directive_changes)} directive file(s) {verb}")
    r.blank()


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


# frob:ticket T-3906
# frob:tests tests/unit/test_pyfmt_runner.py::TestRunRuffCheckSelectImportsNoFix.test_missing_binary_yields_typed_result  # noqa: E501
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob fmt` reports it \
# unchanged), same unwrappable shape as the sibling directive lines above in this file \
# (T-2251's TestRunRuffCheckFixSelectImports)"
def _run_ruff_check_select_imports_no_fix(root: Path) -> ToolResult:
    """`ruff check --select I` (no `--fix`) against `root` -- the
    check-only counterpart of `_run_ruff_check_fix_select_imports`, closing
    T-3906's `--check` gap for the `--select-imports-only` scope."""
    try:
        run_result = guarded_subprocess_run(
            ["ruff", "check", "--select", "I", str(root)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return tool_unavailable_result("ruff-check", "ruff")
    if run_result.is_err:
        return tool_disabled_result("ruff-check", EXEC_KILL_SWITCH_ENV)
    proc = run_result.danger_ok
    msg = (proc.stdout + proc.stderr).strip()
    return ToolResult(
        tool="ruff-check",
        exit_code=proc.returncode,
        summary=msg or "no import-sort violations",
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


# frob:ticket T-3906
# frob:tests tests/unit/test_pyfmt_runner.py::TestRuffFormatCheckOnly.test_missing_binary_yields_typed_result  # noqa: E501
# frob:waive FMT001 reason="single-line frob:tests directive naming a long test node \
# id -- already at frob fmt's own canonical form (verified: `frob fmt` reports it \
# unchanged), same unwrappable shape as the sibling directive lines above in this file \
# (T-2251's TestRuffFormatWriteOnly)"
def _ruff_format_check_only(root: Path) -> ToolResult:
    """The `ruff format --check` counterpart of `_ruff_format_write_only`,
    for the `--select-imports-only --check` path -- closes T-3906's
    `--check` gap for that scope."""
    try:
        run_result = guarded_subprocess_run(
            ["ruff", "format", "--check", str(root)], capture_output=True, text=True
        )
    except FileNotFoundError:
        return tool_unavailable_result("ruff-format", "ruff")
    if run_result.is_err:
        return tool_disabled_result("ruff-format", EXEC_KILL_SWITCH_ENV)
    proc = run_result.danger_ok
    msg = (proc.stdout + proc.stderr).strip()
    return ToolResult(
        tool="ruff-format",
        exit_code=proc.returncode,
        summary=msg or "all files formatted",
    )
