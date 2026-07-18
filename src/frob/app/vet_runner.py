"""CLI wiring for `frob vet [path] [--json]` and `frob vet --hook '<command>'`
(docs/modules/vet.md).

Hook-mode exit-code contract: 0 = fine (or non-install command, exits fast
with no network), 2 = BLOCK (quarantine/typosquat hit), reason on stderr for
a Claude Code PreToolUse hook to surface to the agent.
"""

# frob:waive TEST005 reason="module line coverage 19.2%, debt T-0160"

from __future__ import annotations

import json
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.gates._models import Severity
from frob.logging import get_logger
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
# frob:waive TEST005 reason="run 25.0% branch cover, debt T-0160"
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
    blocked = False
    for name, version in packages:
        verdict = check_package(ecosystem, name, version, root=root)
        print(f"{verdict.ecosystem}/{verdict.package}: {verdict.message}")
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
    """Full lockfile pass: table (or `--json`) output; exit 1 on ERROR when enforced."""
    result = scan_tree(root)
    if result.is_err:
        _log.error("vet: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok
    cve_matches = _cve_matches_for(report, cfg)

    if cfg.vet_json:
        payload = json.loads(report.model_dump_json())
        payload["cve_matches"] = [m.model_dump(mode="json") for m in cve_matches]
        print(json.dumps(payload, indent=2))
    else:
        _print_table(report)
        if cve_matches:
            _print_cve_table(cve_matches)

    for note in report.skipped:
        _log.warning("vet: %s", note)

    if report.advisory_only:
        _log.warning("vet: declare [vet.allow] to enforce")
        sys.exit(0)

    has_errors = any(v.severity is Severity.ERROR for v in report.violations)
    if report.enforce and has_errors:
        sys.exit(1)
    sys.exit(0)


def _print_table(report) -> None:
    """Compact (package, ecosystem, verdict, notes) table for terminal output."""
    by_name: dict[str, list[str]] = {}
    for v in report.violations:
        for verdict in report.verdicts:
            if verdict.name in v.message:
                by_name.setdefault(verdict.name, []).append(f"{v.rule}:{v.severity}")

    if not report.verdicts:
        print("vet: no dependencies found")
        return

    header = f"{'package':<30} {'ecosystem':<10} {'verdict':<10} notes"
    print(header)
    print("-" * len(header))
    for verdict in report.verdicts:
        notes = by_name.get(verdict.name, [])
        status = "FAIL" if notes else "ok"
        print(
            f"{verdict.name:<30} {verdict.ecosystem:<10} {status:<10} "
            f"{', '.join(notes)}"
        )

    if report.violations:
        print()
        print("violations:")
        for v in report.violations:
            print(f"  [{v.severity}] {v.rule} {v.file}: {v.message}")


def _print_cve_table(matches: tuple[CveMatch, ...]) -> None:
    """T-0147: per-match CVE id, CVSS, status, and CWE catalog linkage."""
    print()
    print("cve matches:")
    for m in matches:
        cvss = (
            f"{m.cvss_score}/{m.cvss_severity}"
            if m.cvss_score is not None
            else "unscored"
        )
        print(f"  {m.cve_id} [{m.status}] {m.dependency}@{m.version} cvss={cvss}")
        if m.summary:
            print(f"    {m.summary}")
        for link in m.cwe_links:
            if link.disposition == "catalog":
                print(
                    f"    {link.cwe_id}: {link.title} (mitigation: {link.mitigation})"
                )
            elif link.disposition == "out_of_scope":
                print(f"    {link.cwe_id}: out of scope ({link.reason})")
            else:
                print(f"    {link.cwe_id}: unmapped")


__all__ = ["run"]
