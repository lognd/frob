"""CLI wiring for `frob vet [path] [--json]` and `frob vet --hook '<command>'`
(docs/modules/vet.md).

Hook-mode exit-code contract: 0 = fine (or non-install command, exits fast
with no network), 2 = BLOCK (quarantine/typosquat hit), reason on stderr for
a Claude Code PreToolUse hook to surface to the agent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from frob.app._style import style_fail, style_ok, style_rule
from frob.app.config import AppConfig
from frob.gates._models import Severity
from frob.logging import get_logger
from frob.render import Renderer
from frob.vet import (
    CveMatch,
    Dependency,
    check_package,
    match_dependencies_against_mirror,
    parse_hook_command,
    scan_tree,
)

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:tests tests/test_vet.py::TestVetRunnerLockArg.test_run_lockfile_arg
# frob:tests tests/test_vet.py::TestVetRunnerLockArg.test_run_unsupp_nonzero
def run(cfg: AppConfig) -> None:
    """Dispatch to hook mode (`--hook`) or a full lockfile scan."""
    root = (cfg.vet_path or Path(".")).resolve()
    if cfg.vet_hook is not None:
        _run_hook(root, cfg.vet_hook)
    else:
        _run_scan(root, cfg)


def _run_hook(root: Path, command: str) -> None:
    """Parse `command`; non-install commands exit 0 silently and fast (no network)."""
    parsed = parse_hook_command(command)
    if parsed is None:
        _log.debug("vet: hook: %r is not an install command; fast-exit 0", command)
        sys.exit(0)

    ecosystem, packages = parsed
    renderer = Renderer.for_stream(sys.stdout)
    blocked = False
    for name, version in packages:
        verdict = check_package(ecosystem, name, version, root=root)
        renderer.line(f"{verdict.ecosystem}/{verdict.package}: {verdict.message}")
        if verdict.blocked:
            blocked = True
            print(f"BLOCKED: {verdict.message}", file=sys.stderr)

    if blocked:
        sys.exit(2)
    sys.exit(0)


def _cve_matches_for(report, cfg: AppConfig) -> tuple[CveMatch, ...]:
    """T-0147: CVE mirror matches for `report`'s verdicts, or `()` when no
    mirror is configured -- a silent no-op (docs/modules/vet.md "CVE mirror
    matching"). A configured-but-unreadable mirror is a loud typed failure
    (`sys.exit(1)`), never a silent empty result."""
    if cfg.vet_cve_mirror is None:
        _log.debug("vet: cve: no mirror configured ([tool.frob].vet_cve_mirror); skip")
        return ()
    deps = tuple(
        Dependency(ecosystem=v.ecosystem, name=v.name, version=v.version)
        for v in report.verdicts
    )
    result = match_dependencies_against_mirror(deps, cfg.vet_cve_mirror)
    if result.is_err:
        _log.error("vet: cve: %s", result.danger_err)
        sys.exit(1)
    return result.danger_ok


def _run_scan(root: Path, cfg: AppConfig) -> None:
    """Full lockfile pass: table (or `--json`) output; exit 1 on ERROR when enforced.

    T-0251: `cfg.vet_timeout`/`cfg.vet_jobs` (from `--timeout`/`--jobs`)
    plumb through to `scan_tree`; `jobs` defaults to 1 (untouched behavior)
    when unset.
    """
    result = scan_tree(root, timeout=cfg.vet_timeout, jobs=cfg.vet_jobs or 1)
    if result.is_err:
        _log.error("vet: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok
    cve_matches = _cve_matches_for(report, cfg)

    if cfg.vet_json:
        payload = json.loads(report.model_dump_json())
        payload["cve_matches"] = [m.model_dump(mode="json") for m in cve_matches]
        Renderer.for_stream(sys.stdout).line(json.dumps(payload, indent=2))
    else:
        _print_table(report)
        if cve_matches:
            _print_cve_table(cve_matches)

    for note in report.skipped:
        _log.warning("vet: %s", note)

    sys.exit(_exit_code_for_report(report))


# frob:ticket T-0361
def _exit_code_for_report(report) -> int:  # noqa: ANN001
    """`_run_scan`'s final exit-status decision: 0 for an advisory-only
    report (with a warning to declare `[vet.allow]`), 1 only when the
    report both enforces and has an ERROR-severity violation, else 0;
    split out of `_run_scan`'s tail (T-0361)."""
    if report.advisory_only:
        _log.warning("vet: declare [vet.allow] to enforce")
        return 0
    has_errors = any(v.severity is Severity.ERROR for v in report.violations)
    if report.enforce and has_errors:
        return 1
    return 0


def _print_table(report) -> None:
    """Compact (package, ecosystem, verdict, notes) table for terminal output."""
    from frob.logging.color import should_color

    color = should_color(sys.stdout)
    renderer = Renderer.for_stream(sys.stdout)

    if not report.verdicts:
        renderer.line("vet: no dependencies found")
        return

    by_name = _notes_by_verdict_name(report)
    header = f"{'package':<30} {'ecosystem':<10} {'verdict':<10} notes"
    renderer.line(header)
    renderer.line("-" * len(header))
    for verdict in report.verdicts:
        _print_verdict_row(renderer, verdict, by_name.get(verdict.name, []), color)

    if report.violations:
        renderer.blank()
        renderer.line("violations:")
        for v in report.violations:
            renderer.line(
                f"  [{v.severity}] {style_rule(v.rule, color)} {v.file}: {v.message}"
            )


# frob:ticket T-0361
def _notes_by_verdict_name(report) -> dict[str, list[str]]:  # noqa: ANN001
    """`verdict.name -> [rule:severity, ...]` note strings for every violation
    whose message names that verdict; split out of `_print_table`'s
    grouping phase (T-0361)."""
    by_name: dict[str, list[str]] = {}
    for v in report.violations:
        for verdict in report.verdicts:
            if verdict.name in v.message:
                by_name.setdefault(verdict.name, []).append(f"{v.rule}:{v.severity}")
    return by_name


# frob:ticket T-0361
def _print_verdict_row(
    renderer: Renderer, verdict, notes: list[str], color: bool
) -> None:  # noqa: ANN001
    """Print one `_print_table` row for `verdict`, with a plain-text-width-padded
    ok/FAIL status so ANSI styling never shifts column alignment (T-0179);
    split out of `_print_table`'s row loop (T-0361)."""
    status = "FAIL" if notes else "ok"
    painted = style_fail(status, color) if notes else style_ok(status, color)
    pad = " " * max(0, 10 - len(status))
    renderer.line(
        f"{verdict.name:<30} {verdict.ecosystem:<10} {painted}{pad} {', '.join(notes)}"
    )


def _print_cve_table(matches: tuple[CveMatch, ...]) -> None:
    """T-0147: per-match CVE id, CVSS, status, and CWE catalog linkage."""
    renderer = Renderer.for_stream(sys.stdout)
    renderer.blank()
    renderer.line("cve matches:")
    for m in matches:
        cvss = (
            f"{m.cvss_score}/{m.cvss_severity}"
            if m.cvss_score is not None
            else "unscored"
        )
        renderer.line(
            f"  {m.cve_id} [{m.status}] {m.dependency}@{m.version} cvss={cvss}"
        )
        if m.summary:
            renderer.line(f"    {m.summary}")
        for link in m.cwe_links:
            if link.disposition == "catalog":
                renderer.line(
                    f"    {link.cwe_id}: {link.title} (mitigation: {link.mitigation})"
                )
            elif link.disposition == "out_of_scope":
                renderer.line(f"    {link.cwe_id}: out of scope ({link.reason})")
            else:
                renderer.line(f"    {link.cwe_id}: unmapped")


__all__ = ["run"]
