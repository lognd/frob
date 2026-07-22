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
`sys.stdout.write(...)` call in `src/frob/` outside `src/frob/render/`
fires RENDER001, with a per-line `frob:waive RENDER001 reason="..."` escape
hatch for the rare legitimate exception.

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
from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

#: This module's own file -- its docstring/prose above mentions every
#: flagged call shape by name, which would otherwise self-match.
_SELF_EXCLUDED_FILES = frozenset({"src/frob/gates/_render_lint.py"})

#: Path prefix exempt entirely: `frob.render` IS the sole sanctioned home
#: for these calls (module docstring) -- `Renderer._emit`'s own
#: `print(line, file=self.stream)` is the one legitimate call site.
_EXEMPT_PREFIX = "src/frob/render/"


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
def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- src/frob` under `root`, filtered to `.py`,
    root-relative POSIX paths, `()` on any git failure -- RENDER001 only
    scans frob's own package source (module docstring), mirroring
    `_walk_lint`'s degrade-don't-crash posture."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", "src/frob"))
    if spawned.is_err:
        _log.error("render_lint_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.error("render_lint_gate: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(".py")
    )


# frob:doc docs/modules/render.md#renderer
# frob:tests tests/test_gates.py::TestRenderLintGate.test_bare_print_fires
# frob:tests tests/test_gates.py::TestRenderLintGate.test_render_package_exempt
# frob:tests tests/test_gates.py::TestRenderLintGate.test_stderr_directed_print_is_silent  # noqa: E501
# frob:ticket T-0563
# frob:invariant INV-RENDER-SOLE-STDOUT
def render_lint_gate(root: Path) -> tuple[Violation, ...]:
    """RENDER001 (docs/modules/render.md#renderer): every git-tracked
    `src/frob/**/*.py` file (outside `src/frob/render/` itself) scanned for
    a bare `print`/`click.echo`/`sys.stdout.write` call that bypasses
    `frob.render.Renderer`. ERROR severity (T-0563: the T-0459 straggler
    list is fully migrated, so a new bare print now fails the build)."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        if rel_path in _SELF_EXCLUDED_FILES or rel_path.startswith(_EXEMPT_PREFIX):
            _log.debug("render_lint_gate: skipping exempt %s", rel_path)
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            _log.debug("render_lint_gate: skipping unparseable %s", rel_path)
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


__all__ = ["render_lint_gate"]
