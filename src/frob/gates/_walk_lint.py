"""WALK001: gate against unpruned filesystem traversals (T-0471,
docs/modules/gates.md#walk001-unpruned-traversal-t-0471).

`frob.excludes` already carries the one shared prune-aware walk machinery
(`_should_prune_dir` / `walk_pruned` / `iter_files`, established by T-0335
for `os.walk` sites and extended by T-0471 with the `git ls-files` fast
path), but nothing stopped a NEW `Path.rglob(...)`/`os.walk(...)`/
`glob.glob("**"...)` call from bypassing it -- exactly the mistake T-0453
made (`_repo_files`'s `root.rglob("*")` walked the entire tree, including
`.git`, `.venv`, and ~129 stale `.claude/worktrees/` checkouts, making
`frob ticket doable` take minutes). This module turns that mistake class
into a static check so it cannot recur silently: every raw recursive
traversal call in `src/frob/` fires WALK001 unless it is the shared helper
itself, with a per-line `frob:waive WALK001 reason="..."` escape hatch for
a genuinely small, bounded-scope walk (e.g. `design_dir.rglob("*.strata")`
over a directory that is never large enough to matter).

Detection is AST-based (Python's own `ast` module), matching this
package's existing structural-gate precedent (`frob.gates._pii_structural`
scans the same way, for the same reason: a lexical/regex scan over
`rglob(` would both over- and under-fire on multi-line calls, aliased
imports, and string content that merely mentions the word, where a real
`ast.Call` match does not).
"""

# frob:ticket T-0471
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

#: This module's own path, plus the shared helper's implementation file --
#: both legitimately contain a raw `os.walk`/no-op-looking call the gate
#: must not flag (the helper file `walk_pruned` wraps `os.walk` itself, and
#: this file's own docstring/prose mentions the flagged call shapes).
_SELF_EXCLUDED_FILES = frozenset(
    {
        "src/frob/gates/_walk_lint.py",
        "src/frob/excludes.py",
    }
)

#: Dotted-attribute names (the RIGHTMOST `.attr`) that are unbounded
#: recursive walks regardless of arguments -- `Path.rglob(...)` always
#: recurses the whole subtree no matter what pattern it is given (unlike
#: `Path.glob`, which is only recursive when the pattern itself contains
#: `**`).
_ALWAYS_RECURSIVE_ATTRS = frozenset({"rglob"})

#: Dotted-attribute names whose recursiveness depends on a `"**"` glob
#: pattern in the first argument.
_CONDITIONALLY_RECURSIVE_ATTRS = frozenset({"glob", "iglob"})


@dataclass(frozen=True)
class _WalkSite:
    """One raw-traversal call site WALK001 flags: its line and remedy text."""

    lineno: int
    call_desc: str


def _attr_name(node: ast.expr) -> str | None:
    """The `.attr` of an `ast.Attribute` call target, or `None` for anything
    else (a bare `Name` call, e.g. a module-level `walk(...)` import)."""
    return node.attr if isinstance(node, ast.Attribute) else None


def _dotted_prefix(node: ast.expr) -> str | None:
    """The dotted-name text of an `Attribute`/`Name` chain (`os.walk` ->
    `"os.walk"`), or `None` for anything else -- local unparse, same shape
    as `frob.gates._pii_structural._dotted_prefix` (small enough that
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


def _first_arg_literal(call: ast.Call) -> str | None:
    """The literal string value of `call`'s first positional argument, or
    `None` if absent/non-literal."""
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _is_recursive_glob_call(call: ast.Call, attr: str) -> bool:
    """Whether a `.glob`/`.iglob`-shaped call (`attr` already matched) is
    actually recursive -- only when its pattern argument contains `"**"`, a
    literal-only check (a non-literal/dynamic pattern is treated as
    POTENTIALLY recursive, deny-by-default like `_pii010`'s unknown-
    category default, since a dynamic pattern cannot be proven bounded)."""
    literal = _first_arg_literal(call)
    if literal is None:
        return True
    return "**" in literal


def _site_call_desc(func: ast.expr, attr: str) -> str:
    """A human-readable description of the flagged call for the violation
    message (`"Path.rglob(...)"`, `"os.walk(...)"`)."""
    dotted = _dotted_prefix(func)
    return f"{dotted}(...)" if dotted else f"{attr}(...)"


def _method_call_site(call: ast.Call) -> _WalkSite | None:
    """A flagged `_WalkSite` for a `.rglob`/`.glob`/`.iglob` method call, or
    `None` if `call` doesn't match any of those shapes."""
    attr = _attr_name(call.func)
    if attr is None:
        return None
    if attr in _ALWAYS_RECURSIVE_ATTRS:
        return _WalkSite(call.lineno, _site_call_desc(call.func, attr))
    if attr in _CONDITIONALLY_RECURSIVE_ATTRS and _is_recursive_glob_call(call, attr):
        return _WalkSite(call.lineno, _site_call_desc(call.func, attr))
    return None


@dataclass(frozen=True)
class _ImportBindings:
    """The local names, in ONE module, that are actually bound to `os.walk`
    / `glob.glob` / `glob.iglob` via a `from X import Y [as Z]` -- built
    once per file so a bare `walk(...)` call only fires when it demonstrably
    reaches `os.walk` and not, say, a locally-defined recursive tree-walker
    function that happens to share the name (a real false positive this
    module's own dogfooding run against `frob.vet._capability` caught: a
    local `def walk(node): ...` tree-sitter-node walker is NOT a filesystem
    traversal)."""

    walk_names: frozenset[str]
    glob_names: frozenset[str]


def _collect_import_bindings(tree: ast.Module) -> _ImportBindings:
    """Every local name bound to `os.walk`/`glob.glob`/`glob.iglob` by a
    top-level or nested `from os import ...`/`from glob import ...`
    statement in `tree` (alias-aware: `from os import walk as w` binds
    `"w"`, not `"walk"`)."""
    walk_names: set[str] = set()
    glob_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module == "os":
            for alias in node.names:
                if alias.name == "walk":
                    walk_names.add(alias.asname or alias.name)
        elif node.module == "glob":
            for alias in node.names:
                if alias.name in ("glob", "iglob"):
                    glob_names.add(alias.asname or alias.name)
    return _ImportBindings(
        walk_names=frozenset(walk_names), glob_names=frozenset(glob_names)
    )


def _bare_call_site(call: ast.Call, bindings: _ImportBindings) -> _WalkSite | None:
    """A flagged `_WalkSite` for a bare-name call whose name is DEMONSTRABLY
    bound to `os.walk`/`glob.glob`/`glob.iglob` in this module (`bindings`)
    -- a same-named local function/variable is never flagged."""
    if not isinstance(call.func, ast.Name):
        return None
    name = call.func.id
    if name in bindings.walk_names:
        return _WalkSite(call.lineno, f"{name}(...)")
    if name in bindings.glob_names and _is_recursive_glob_call(call, name):
        return _WalkSite(call.lineno, f"{name}(...)")
    return None


def _dotted_call_site(call: ast.Call) -> _WalkSite | None:
    """A flagged `_WalkSite` for a fully-dotted `os.walk(...)`/`glob.glob(
    "**"...)`/`glob.iglob("**"...)` call, or `None`."""
    dotted = _dotted_prefix(call.func)
    if dotted == "os.walk":
        return _WalkSite(call.lineno, "os.walk(...)")
    if dotted in ("glob.glob", "glob.iglob") and _is_recursive_glob_call(
        call, dotted.split(".")[-1]
    ):
        return _WalkSite(call.lineno, f"{dotted}(...)")
    return None


def _scan_python_walks(tree: ast.Module) -> tuple[_WalkSite, ...]:
    """Every unpruned-traversal call site in `tree` (module docstring:
    `Path.rglob`, recursive `Path.glob`/`.iglob`, `os.walk`, recursive
    `glob.glob`/`glob.iglob`, in either dotted or bare-imported form -- a
    bare form only counts when `_collect_import_bindings` proves the name
    actually came from `os`/`glob`, never a same-named local symbol)."""
    bindings = _collect_import_bindings(tree)
    sites: list[_WalkSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        site = (
            _method_call_site(node)
            or _bare_call_site(node, bindings)
            or _dotted_call_site(node)
        )
        if site is not None:
            sites.append(site)
    return tuple(sites)


def _walk001_violation(rel_path: str, site: _WalkSite) -> Violation:
    """The WALK001 `Violation` for one raw traversal call site."""
    _log.warning(
        "WALK001: %s:%d unpruned traversal %s", rel_path, site.lineno, site.call_desc
    )
    return Violation(
        rule="WALK001",
        severity=Severity.WARN,
        file=rel_path,
        line=site.lineno,
        message=(
            f"WALK001: {rel_path}:{site.lineno} raw unpruned traversal "
            f"{site.call_desc} walks the whole subtree before any filter runs "
            f"(descends into .git/.venv/node_modules/.claude/worktrees/build/"
            f"dist/target/__pycache__ before pruning) -- route through "
            f"frob.excludes.iter_files / frob.excludes.walk_pruned so it "
            f'prunes before descending, or `frob:waive WALK001 reason="..."` '
            f"if this is a genuinely small, bounded-scope walk"
        ),
    )


def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- src/frob` under `root`, filtered to `.py`,
    root-relative POSIX paths, `()` on any git failure -- WALK001 only scans
    frob's own package source (module docstring), mirroring
    `_pii_structural`'s degrade-don't-crash posture. A directory pathspec
    (not a `**` glob -- plain `git ls-files` pathspecs don't expand `**`
    without glob magic) already matches every file at any depth under it."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", "src/frob"))
    if spawned.is_err:
        _log.error("walk_lint_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.error("walk_lint_gate: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(".py")
    )


# frob:doc docs/modules/gates.md#walk001-unpruned-traversal-t-0471
# frob:tests tests/test_walk_lint_gate.py::TestRglob.test_raw_rglob_fires
# frob:tests tests/test_walk_lint_gate.py::TestHelper.test_helper_call_is_silent
# frob:tests tests/test_walk_lint_gate.py::TestSelfMatchExclusion.test_own_files_not_scanned  # noqa: E501
# frob:invariant INV-005
def walk_lint_gate(root: Path) -> tuple[Violation, ...]:
    """WALK001 (docs/modules/gates.md#walk001-unpruned-traversal-t-0471):
    every git-tracked `src/frob/**/*.py` file scanned for a raw recursive
    traversal call that bypasses `frob.excludes`' shared prune-aware
    helpers. Self-excludes this module and `frob/excludes.py` (module
    docstring)."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_python_files(root):
        if rel_path in _SELF_EXCLUDED_FILES:
            _log.debug("walk_lint_gate: skipping self-excluded %s", rel_path)
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            _log.debug("walk_lint_gate: skipping unparseable %s", rel_path)
            continue
        scanned += 1
        violations.extend(
            _walk001_violation(rel_path, site) for site in _scan_python_walks(tree)
        )

    _log.info(
        "walk_lint_gate: scanned %d tracked src/frob .py file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = ["walk_lint_gate"]
