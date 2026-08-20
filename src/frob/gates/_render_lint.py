"""RENDER001: gate against bare stdout writes outside `frob.render`
(T-0459, docs/modules/render.md#renderer).

INV-RENDER-SOLE-STDOUT (docs/modules/render.md#renderer): a command runner
must produce human-facing stdout ONLY through `frob.render.Renderer` -- the
T-0448 output layer's whole point is a single home for color/TTY decisions
and a stable element vocabulary, and that concentration only holds if
nothing else can quietly reach stdout directly. This module turns that
invariant into a static check, the same shape `frob.gates._walk_lint`
already uses for a different mistake class (AST-based, so it structurally
cannot mis-fire on a multi-line call, an aliased import, or a string that
merely mentions `print`): every bare `print(...)`, `click.echo(...)`, or
`sys.stdout.write(...)` call in `src/frob/`, `.claude/hooks/`, or
`scripts/fleet_status.py` fires RENDER001, except the paths in
`_EXEMPT_PREFIXES` -- `src/frob/render/` (the one sanctioned home for
these calls) and, as of T-2719, `.claude/hooks/` and
`scripts/fleet_status.py` themselves (standalone scripts that must run
with no `frob.*` import at all, so `frob.render.Renderer` is structurally
unreachable there, not merely unused -- a directory/file exemption
instead of the growing set of individually-honest per-line
`frob:waive RENDER001 reason="..."` directives that constraint used to
require). The per-line waiver escape hatch remains for any other genuine
exception outside these paths.

A call explicitly directed at stderr (a `file=` keyword whose value's
dotted name ends in `.stderr`, e.g. `print(x, file=sys.stderr)` or the
`_sys.stderr` alias form `frob/__main__.py` uses) is NOT flagged --
INV-RENDER-SOLE-STDOUT governs stdout only, `frob.logging` already governs
the stderr-routed diagnostic path.

ERROR severity (T-0563): the T-0459 straggler list (`test_runner`,
`check_runner`'s own final report line, `clean_runner`, `debt_runner`,
`gitlog_runner`, `registry_runner`, `doctor_runner` -- 14 bare
print/stdout call sites total) is now fully migrated to `frob.render`/
`_log.info`, so a NEW bare print regresses the build immediately, matching
PII/SEC's fail-closed posture, instead of degrading silently to a warning.
"""

# frob:ticket T-0459
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._parse_failures import local_parse001_violation
from frob.gates._walk_lint import tracked_python_files_for_gate
from frob.logging import get_logger

_log = get_logger(__name__)

#: This module's own file -- its docstring/prose above mentions every
#: flagged call shape by name, which would otherwise self-match.
_SELF_EXCLUDED_FILES = frozenset({"src/frob/gates/_render_lint.py"})

#: Path prefixes exempt entirely (T-2719, widened from the original single
#: `src/frob/render/` string): `str.startswith` accepts a tuple directly,
#: so this stays a one-site check just like the original.
#:
#: - `src/frob/render/`: `frob.render` IS the sole sanctioned home for
#:   these calls (module docstring) -- `Renderer._emit`'s own
#:   `print(line, file=self.stream)` is the one legitimate call site.
#: - `.claude/hooks/`: Claude Code hook scripts run standalone, before any
#:   venv/native-extension build exists, and MUST NOT import `frob.*` --
#:   `frob.render.Renderer` is therefore structurally unreachable from
#:   them, not merely unused. T-1614's waive audit found 11 individually
#:   honest `frob:waive RENDER001` directives across 5 files in this
#:   directory alone, all citing exactly this constraint; a directory
#:   exemption replaces that growing per-line-waiver debt.
#: - `scripts/fleet_status.py`: the same standalone, no-frob-import
#:   constraint, for the identical reason (a fleet-diagnostic script that
#:   must run without a built venv) -- named as a single file, NOT a
#:   `scripts/` prefix, because sibling scripts (e.g. `bump_version.py`)
#:   DO import `frob.*` and remain fully subject to RENDER001.
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "src/frob/render/",
    ".claude/hooks/",
    "scripts/fleet_status.py",
)

#: Extra `git ls-files` pathspecs scanned in addition to the historical
#: `src/frob` default (T-2719): `.claude/hooks` and the single
#: `scripts/fleet_status.py` file, matching `_EXEMPT_PREFIXES` above --
#: scanned (rather than left entirely unscanned) so the exemption is a
#: real, testable no-op instead of dead code that merely happens to never
#: run, and so a FUTURE non-exempt file added under either path is caught
#: by RENDER001 rather than silently invisible to it.
_EXTRA_SCAN_PATHSPECS: tuple[str, ...] = (
    ".claude/hooks",
    "scripts/fleet_status.py",
)


# frob:ticket T-0459
@dataclass(frozen=True)
class _PrintSite:
    """One flagged bare-stdout-write call site: its line and remedy text."""

    lineno: int
    call_desc: str


# frob:ticket T-0459
def _dotted_prefix(node: ast.expr) -> str | None:
    """The dotted-name text of an `Attribute`/`Name` chain (`sys.stdout.write`
    -> `"sys.stdout.write"`), or `None` for anything else -- same local
    unparse `frob.gates._walk_lint._dotted_prefix` uses (small enough that
    importing across gate modules for one helper is not worth the coupling;
    see that module's docstring for the same call)."""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


# frob:ticket T-0459
def _stderr_directed(call: ast.Call) -> bool:
    """Whether `call` carries a `file=...` keyword whose dotted value ends
    in `.stderr` (any `sys`/`_sys`-style alias) -- INV-RENDER-SOLE-STDOUT
    governs stdout only, so a deliberately stderr-routed `print` is never
    flagged."""
    for kw in call.keywords:
        if kw.arg != "file":
            continue
        dotted = _dotted_prefix(kw.value)
        if dotted is not None and dotted.endswith(".stderr"):
            return True
    return False


# frob:ticket T-0459
def _click_echo_site(call: ast.Call) -> _PrintSite | None:
    """A flagged `_PrintSite` for a `click.echo(...)` (or bare `echo(...)`
    imported from `click`) call, or `None`."""
    dotted = _dotted_prefix(call.func)
    if dotted == "click.echo":
        return _PrintSite(call.lineno, "click.echo(...)")
    return None


# frob:ticket T-0459
def _stdout_write_site(call: ast.Call) -> _PrintSite | None:
    """A flagged `_PrintSite` for a `sys.stdout.write(...)`-shaped call
    (any `sys` alias), or `None`."""
    dotted = _dotted_prefix(call.func)
    if dotted is not None and dotted.endswith("stdout.write"):
        return _PrintSite(call.lineno, "sys.stdout.write(...)")
    return None


# frob:ticket T-0459
def _print_site(call: ast.Call) -> _PrintSite | None:
    """A flagged `_PrintSite` for a bare builtin `print(...)` call (never a
    same-named local/imported symbol -- `ast.Name` with `id == "print"` is
    unambiguously the builtin unless shadowed, which `_scan_python_prints`
    does not attempt to disprove; a repo shadowing the `print` builtin
    itself would be a stranger problem than this gate), or `None` when
    `call` is stderr-directed."""
    if not (isinstance(call.func, ast.Name) and call.func.id == "print"):
        return None
    if _stderr_directed(call):
        return None
    return _PrintSite(call.lineno, "print(...)")


# frob:ticket T-0459
def _scan_python_prints(tree: ast.Module) -> tuple[_PrintSite, ...]:
    """Every bare stdout-write call site in `tree` (module docstring:
    `print(...)` not directed at stderr, `click.echo(...)`,
    `sys.stdout.write(...)` in either dotted or aliased form)."""
    sites: list[_PrintSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        site = _print_site(node) or _click_echo_site(node) or _stdout_write_site(node)
        if site is not None:
            sites.append(site)
    return tuple(sites)


# frob:ticket T-0459
# frob:ticket T-0563
# frob:enforces CHK-GATE-RENDER001
def _render001_violation(rel_path: str, site: _PrintSite) -> Violation:
    """The RENDER001 `Violation` for one bare-stdout-write call site."""
    _log.warning(
        "RENDER001: %s:%d bare stdout write %s", rel_path, site.lineno, site.call_desc
    )
    return Violation(
        rule="RENDER001",
        severity=Severity.ERROR,
        file=rel_path,
        line=site.lineno,
        message=(
            f"RENDER001: {rel_path}:{site.lineno} bare stdout write "
            f"{site.call_desc} bypasses frob.render (INV-RENDER-SOLE-STDOUT, "
            f"docs/modules/render.md#renderer) -- route human-facing output "
            f"through a Renderer (`Renderer.for_stream(sys.stdout).line(...)` "
            f"or the matching `RenderWriter` element), or "
            f'`frob:waive RENDER001 reason="..."` if this is a genuine '
            f"exception"
        ),
    )


# frob:ticket T-0459
# frob:ticket T-0897
def _parse001_violation(rel_path: str, reason: str) -> Violation:
    """PARSE001 `Violation` for a file this gate's own read/`ast.parse`
    could not get through (T-0897): delegates to `frob.gates._parse_failures.
    local_parse001_violation` (extracted T-0861) with this gate's own
    capability-loss clause so RENDER001's message stays distinct while the
    rule id/severity/message shape is the ONE shared home."""
    return local_parse001_violation(
        rel_path, reason, "RENDER001 cannot inspect it for a bare stdout write"
    )


# frob:ticket T-0459
# frob:ticket T-0861
# frob:ticket T-2719
def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """RENDER001's own thin wrapper around `frob.gates._walk_lint.
    tracked_python_files_for_gate` (T-0861: this was a byte-identical
    private copy of WALK001's own `_tracked_python_files`, now the shared
    home), pinning `log_prefix="render_lint_gate"` so every existing
    caller in this module keeps calling a zero-arg helper. T-2719: unions
    the historical `src/frob` default with `_EXTRA_SCAN_PATHSPECS`
    (`.claude/hooks`, `scripts/fleet_status.py`) so those paths are
    genuinely scanned-then-exempted rather than silently never reached --
    de-duplicated and order-stable in case a future pathspec ever
    overlaps."""
    seen: set[str] = set()
    files: list[str] = []
    for pathspec in ("src/frob", *_EXTRA_SCAN_PATHSPECS):
        for rel_path in tracked_python_files_for_gate(
            root, log_prefix="render_lint_gate", pathspec=pathspec
        ):
            if rel_path not in seen:
                seen.add(rel_path)
                files.append(rel_path)
    return tuple(files)


# frob:doc docs/modules/render.md#renderer
# frob:waive AFFECT001 reason="T-2740 adds this predicate as an exposed reuse of \
# render_lint_gate's own membership logic; render.md#renderer already documents \
# RENDER001's scan/exemption rules this function is derived from verbatim -- no new \
# behavior for that anchor's prose to describe, only a new caller"
# frob:waive WIRE001 reason="T-2740: wired via frob.app.ticket_runner._waive_audit's \
# _LIVENESS_SCAN_CHECKERS dict-dispatch (same shape as _load_family_reporters' \
# archgate/perf/strata/graph/vet entries in frob.gates._coverage_sites, which carry an \
# identical WIRE001 waiver for the identical reason) -- static call-graph analysis of \
# a dict-value assignment cannot see the real runtime caller" follow_up="T-2057"
# frob:ticket T-2740
# frob:tests \
# tests/test_gates.py::TestRenderLintGate.test_render001_scans_true_for_a_real_scanned_\
# file kind="unit"
# frob:tests \
# tests/test_gates.py::TestRenderLintGate.test_render001_scans_false_for_an_exempt_pat\
# h kind="unit"
# frob:tests \
# tests/test_gates.py::TestRenderLintGate.test_render001_scans_false_for_a_path_outside\
# _any_pathspec kind="unit"
def render001_scans(root: Path, rel_path: str) -> bool:
    """True iff RENDER001's own scan set would actually examine `rel_path`
    for a bare stdout write -- the exact membership test `render_lint_gate`
    itself uses (self-exclusion, `_EXEMPT_PREFIXES`, and real git-tracked
    pathspec membership via `_tracked_python_files`), exposed as a public
    predicate so a waiver-liveness classifier (`frob.app.ticket_runner.
    _waive_audit`) can ask "does this rule even look at this file" without
    re-deriving or hardcoding RENDER001's pathspec a second time -- T-2719's
    own root cause (a hardcoded `src/frob` scan root, silently unscanning
    `.claude/hooks/` and `scripts/fleet_status.py`) is exactly the class of
    bug a second, independent hardcoded copy of this membership test would
    risk reintroducing."""
    if rel_path in _SELF_EXCLUDED_FILES or rel_path.startswith(_EXEMPT_PREFIXES):
        return False
    return rel_path in _tracked_python_files(root)


# frob:doc docs/modules/render.md#renderer
# frob:tests tests/test_gates.py::TestRenderLintGate.test_bare_print_fires
# frob:tests tests/test_gates.py::TestRenderLintGate.test_render_package_exempt
# frob:tests tests/test_gates.py::TestRenderLintGate.test_stderr_directed_print_is_silent  # noqa: E501
# frob:tests tests/test_gates.py::TestRenderLintGate.test_unparseable_file_fires_parse001  # noqa: E501
# frob:tests tests/test_gates.py::TestRenderLintGate.test_claude_hooks_dir_exempt
# frob:tests tests/test_gates.py::TestRenderLintGate.test_fleet_status_file_exempt
# frob:tests tests/test_gates.py::TestRenderLintGate.test_exemption_is_file_scoped_not_dir_scoped  # noqa: E501
# frob:tests tests/test_gates.py::TestRenderLintGate.test_scan_now_covers_hooks_and_fleet_status  # noqa: E501
# frob:ticket T-2719
# frob:ticket T-0563
# frob:ticket T-0897
# frob:invariant INV-RENDER-SOLE-STDOUT
def render_lint_gate(root: Path) -> tuple[Violation, ...]:
    """RENDER001 (docs/modules/render.md#renderer): every git-tracked
    `src/frob/**/*.py` file, plus `.claude/hooks/**/*.py` and
    `scripts/fleet_status.py` (T-2719), scanned for a bare `print`/
    `click.echo`/`sys.stdout.write` call that bypasses `frob.render.
    Renderer` -- except `_EXEMPT_PREFIXES` (`src/frob/render/` itself,
    plus the same `.claude/hooks/`/`scripts/fleet_status.py` paths just
    added to the scan: standalone scripts that must run with no `frob.*`
    import, so `frob.render.Renderer` is structurally unreachable from
    them, not merely unused). ERROR severity (T-0563: the T-0459 straggler
    list is fully migrated, so a new bare print now fails the build). A
    file this gate cannot read/parse fires PARSE001 instead of silently
    dropping out of the scan (T-0897)."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        if rel_path in _SELF_EXCLUDED_FILES or rel_path.startswith(_EXEMPT_PREFIXES):
            _log.debug("render_lint_gate: skipping exempt %s", rel_path)
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            violations.append(_parse001_violation(rel_path, str(exc)))
            continue
        scanned += 1
        violations.extend(
            _render001_violation(rel_path, site) for site in _scan_python_prints(tree)
        )

    _log.info(
        "render_lint_gate: scanned %d tracked src/frob .py file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = ["render_lint_gate", "render001_scans"]
