# frob:waive LARGE001 reason="T-2944: this file crossed the 800-line threshold adding \
# two more PLATFORM001 shapes (a silent platform-string guard scan, a bare-restricted- \
# import scan) alongside the existing WALK001 scan and the original PLATFORM001 `X is \
# None` scan. WALK001 and PLATFORM001 ARE a genuine seam (two independently- testable \
# AST scans sharing this file only for one-pass-over-the-tree convenience, not because \
# they are the same concern) -- a real split is the right fix, but a new module was \
# outside T-2944's declared scope (src/frob/gates/_walk_lint.py, \
# src/frob/process/_reap.py, src/frob/tickets/_leases.py, two test files); filed as \
# its own scoped ticket (T-2962, renumbers on land) rather than expanding T-2944's \
# scope or leaving this undocumented"
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

PLATFORM001 (T-2919, docs/modules/gates.md#platform001-posix-only-
primitive-degrades-silently-t-2919) rides alongside WALK001 in this same
module -- same "one raw AST scan over `src/frob/**/*.py`, one static
mistake-class check" shape, same file (not a new dispatch-table stage;
`walk_lint_gate` below returns both rule ids' violations from one pass,
mirroring how NEGEXIST001 rides the "docblocks" stage). T-2917/T-2918
measured the shape directly: `frob.tickets._land`'s and `frob.app.
ticket_runner._rapid_sweep`'s `fcntl`-degrade sites all followed the same
`try: import fcntl / except ImportError: fcntl = None` convention, then
an `if fcntl is None:` guard that logged a WARNING and silently
proceeded as if nothing were wrong -- a real Windows-vs-POSIX
correctness gap (T-2918's own fix) that no test or type checker could
have caught, because both branches type-check and both branches pass a
Linux-only CI (T-2917's own finding: this repo's CI ran ubuntu-latest
only until this same ticket series added Windows/macOS). PLATFORM001
generalizes that ONE incident into a repo-wide static check so the NEXT
POSIX-only primitive someone adds cannot ship the same silent gap.

T-2944 widened PLATFORM001 to two more shapes the original `X is None`
scan missed: a `sys.platform`/`os.name`/`platform.system()` guard that
degrades completely silently (no log, no raise) rather than merely
logging (`_scan_platform_string_guards`), and a bare, unconditional
module-top-level `import <restricted-module>` with no guard idiom at
all (`_scan_bare_restricted_imports`, the T-2952 regression class).
"""

# frob:ticket T-0471
# frob:ticket T-2919
# frob:ticket T-2944
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


# frob:waive DUP001 reason="this module's own docstring states this local dotted-name \
# unparse is the same small shape as frob.gates._render_lint's and \
# frob.gates._pii_structural._env_access's siblings, kept local deliberately rather \
# than sharing a private helper across modules"
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


# frob:enforces CHK-GATE-WALK001
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


# frob:ticket T-0861
# frob:doc docs/modules/gates.md#rule-catalog
# frob:tests tests/test_walk_lint_gate.py::TestRglob.test_raw_rglob_fires
# frob:tests tests/test_gates.py::TestRenderLintGate.test_render_package_exempt
def tracked_python_files_for_gate(
    root: Path, *, log_prefix: str, pathspec: str = "src/frob"
) -> tuple[str, ...]:
    """`git ls-files -- <pathspec>` under `root`, filtered to `.py`,
    root-relative POSIX paths, `()` on any git failure -- shared by WALK001
    and RENDER001, which both only scan frob's own package source
    (T-0861 dup group: this was two byte-identical private copies,
    `_walk_lint.py::_tracked_python_files`/`_render_lint.py::
    _tracked_python_files`, differing only in `log_prefix`), mirroring
    `_pii_structural`'s degrade-don't-crash posture. A directory pathspec
    (not a `**` glob -- plain `git ls-files` pathspecs don't expand `**`
    without glob magic) already matches every file at any depth under it.

    T-2389 (child of T-2384): `pathspec` was a hardcoded `"src/frob"`
    literal -- exactly the class T-2384 exists to retarget, one layer
    below every caller that reuses this helper to enumerate tracked
    files at all (PORT001/WALK001/RENDER001 alike). Now an explicit,
    OPTIONAL keyword defaulting to the historical literal, so existing
    callers (`walk_lint_gate`/`render_lint_gate`, both genuinely,
    permanently about scanning THIS repo's own `src/frob/**` source --
    not a portability bug, the same class `_config_meta.py`'s self-check
    is) are unaffected. A new/retargeted caller (see
    `frob.lang.declared_source_prefixes`, T-2195) passes its own resolved
    pathspec explicitly instead of inheriting the default -- T-2388's
    `_port_selfcheck.py` is disclosed as NOT yet doing so (out of this
    ticket's own scope; a natural next step once this default-preserving
    shape exists to switch to).

    Logs at WARNING (T-0705), not ERROR: a git-less target (no `.git`,
    or `git` itself unavailable) is a supported, silently-empty scan --
    the same posture `ref_gate`/`doc004` already use for the identical
    condition (docs/modules/gates.md#git-less-target-contract-t-0705).
    `log_prefix` (e.g. `"walk_lint_gate"`/`"render_lint_gate"`) keeps each
    caller's own log line identity so a WARNING still names which gate hit
    the git failure."""
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", pathspec))
    if spawned.is_err:
        _log.warning("%s: git ls-files failed: %s", log_prefix, spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("%s: git ls-files exited %d", log_prefix, result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(".py")
    )


def _tracked_python_files(root: Path) -> tuple[str, ...]:
    """WALK001's own thin wrapper around `tracked_python_files_for_gate`
    (T-0861), pinning `log_prefix="walk_lint_gate"` so every existing
    caller in this module keeps calling a zero-arg helper."""
    return tracked_python_files_for_gate(root, log_prefix="walk_lint_gate")


#: Standard-library module names PLATFORM001 treats as "may not exist on
#: this interpreter/platform" -- POSIX-only (`fcntl`, `termios`, `tty`,
#: `pwd`, `grp`, `resource`, `posix`) and Windows-only (`msvcrt`,
#: `winreg`, `_winapi`) alike, matching `frob.app.ticket_runner.
#: _rapid_sweep`'s own T-2918 pairing of the two. Deliberately NOT
#: third-party optional-dependency names (`z3`, `tree_sitter`, ...) --
#: those follow the identical `try/except ImportError` shape for a
#: wholly different reason (an optional extra, not a platform gap) and
#: are out of this rule's population by design.
_PLATFORM_RESTRICTED_MODULES = frozenset(
    {
        "fcntl",
        "termios",
        "tty",
        "pwd",
        "grp",
        "resource",
        "posix",
        "msvcrt",
        "winreg",
        "_winapi",
    }
)

#: Logging-call attribute names PLATFORM001 treats as "this guard body
#: observably logged something" -- if a guard degrades with none of
#: these AND no loud exit either, that is a separate, worse silent-no-op
#: shape this v1 does not attempt to detect (see `_guard_is_loud`'s
#: docstring for the disclosed gap).
_LOG_CALL_ATTRS = frozenset({"warning", "warn", "error", "critical", "info", "debug"})


def _restricted_import_names(try_body: list[ast.stmt]) -> frozenset[str]:
    """Local names a `Try.body` (one candidate try-block) binds to one of
    `_PLATFORM_RESTRICTED_MODULES`, via either `import X [as name]` or
    `name = importlib.import_module("X")` -- the two shapes this repo's
    own fcntl/msvcrt degrade sites use (T-2918's own `_rapid_sweep.py`
    uses the second form)."""
    names: set[str] = set()
    for stmt in try_body:
        if isinstance(stmt, ast.Import):
            # frob:waive PERF003 reason="PERF003's pattern-match flags any nested loop plus equality/membership check regardless of the inner collection's type; `_PLATFORM_RESTRICTED_MODULES` is already a frozenset (O(1) membership), and `try_body`/`stmt.names` are both a single small statement/alias list (a handful of items at most, one try-block's own body) -- there is no larger collection to index into"  # noqa: E501
            for alias in stmt.names:
                if alias.name in _PLATFORM_RESTRICTED_MODULES:
                    names.add(alias.asname or alias.name)
        elif (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Call)
            and _dotted_prefix(stmt.value.func) == "importlib.import_module"
        ):
            literal = _first_arg_literal(stmt.value)
            if literal in _PLATFORM_RESTRICTED_MODULES:
                names.add(stmt.targets[0].id)
    return frozenset(names)


def _handles_import_error(handler: ast.ExceptHandler) -> bool:
    """Whether `handler` catches `ImportError` (bare name or a tuple
    that includes it) -- a bare `except:` is deliberately NOT treated as
    matching here, since that shape already has its own, unrelated gate
    concerns and this rule only cares about the specific platform-
    availability-probe idiom."""
    if handler.type is None:
        return False
    if isinstance(handler.type, ast.Name):
        return handler.type.id == "ImportError"
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(elt, ast.Name) and elt.id == "ImportError"
            for elt in handler.type.elts
        )
    return False


def _none_bound_names(
    handler_body: list[ast.stmt], candidates: frozenset[str]
) -> set[str]:
    """The subset of `candidates` that `handler_body` (an `except
    ImportError:` block) assigns `= None`, confirming the try/except
    pair really is the platform-probe degrade idiom and not an unrelated
    `except ImportError` that happens to import one of the same module
    names for some other reason."""
    bound: set[str] = set()
    for stmt in handler_body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and stmt.targets[0].id in candidates
            and isinstance(stmt.value, ast.Constant)
            and stmt.value.value is None
        ):
            bound.add(stmt.targets[0].id)
    return bound


def _platform_guard_names(tree: ast.Module) -> frozenset[str]:
    """Every local name in `tree` that PLATFORM001 treats as a platform-
    optional primitive: bound to a restricted module in a `try:` block
    whose `except ImportError:` handler sets it back to `None` on
    failure -- the exact shape this repo's own `fcntl`/`msvcrt` degrade
    sites (T-2595/T-2918) use."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        candidates = _restricted_import_names(node.body)
        if not candidates:
            continue
        for handler in node.handlers:
            if _handles_import_error(handler):
                names |= _none_bound_names(handler.body, candidates)
    return frozenset(names)


# frob:ticket T-2944
#: T-2944 shape 2: `sys.platform`/`os.name` reads (`_dotted_prefix`);
#: `platform.system()` (a call) is matched inline below.
_PLATFORM_STRING_EXPRS = frozenset({"sys.platform", "os.name"})


# frob:ticket T-2944
def _is_platform_string_read(node: ast.expr) -> bool:
    """Whether `node` reads the platform as a string (`sys.platform`,
    `os.name`, or a bare `platform.system()` call)."""
    if _dotted_prefix(node) in _PLATFORM_STRING_EXPRS:
        return True
    return (
        isinstance(node, ast.Call)
        and not node.args
        and not node.keywords
        and _dotted_prefix(node.func) == "platform.system"
    )


# frob:ticket T-2944
def _is_platform_string_guard_test(test: ast.expr) -> bool:
    """Whether `test` is `<platform-string> (!=|==) "<literal>"` --
    T-2944 shape 2 (`_reap.py:204`). A bare `ast.Compare` only -- a
    `BoolOp` combining it with something else (`reap_orphaned_
    forkservers`'s `sys.platform == "win32" or not proc.is_dir()`) is
    real branching logic, not this rule's target."""
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], (ast.Eq, ast.NotEq)):
        return False
    if len(test.comparators) != 1:
        return False
    comparator = test.comparators[0]
    if not (
        isinstance(comparator, ast.Constant) and isinstance(comparator.value, str)
    ):
        return False
    return _is_platform_string_read(test.left)


# frob:ticket T-2944
# frob:waive DUP001 reason="T-2944: the structural clone detector matches this against \
# _print_fuzz_results/_near_duplicate_cluster/_assumption_ledger_lines purely on the \
# generic shape (iterate a small list, isinstance/attr checks, return a bool/subset) \
# -- those three are semantically unrelated (fuzz-result logging, near-duplicate \
# cluster formation, assumption-ledger rendering); there is no shared abstraction to \
# extract with a platform-guard-body no-op check"
def _is_degrade_body(body: list[ast.stmt]) -> bool:
    """Whether an `If.body` is a pure "return falsy, do nothing else"
    (or bare `pass`) no-op -- real platform-specific WORK that merely
    doesn't log/raise (`_coverage_refresh.py`'s win32 `taskkill` branch)
    must stay quiet. Ignores a leading string-literal "comment"
    statement, then requires exactly one real statement left."""
    real_stmts = [
        stmt
        for stmt in body
        if not (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        )
    ]
    if len(real_stmts) != 1:
        return False
    stmt = real_stmts[0]
    if isinstance(stmt, ast.Pass):
        return True
    if not isinstance(stmt, ast.Return):
        return False
    value = stmt.value
    if value is None:
        return True
    if isinstance(value, ast.Constant):
        return value.value is None or value.value is False
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return not value.elts
    if isinstance(value, ast.Dict):
        return not value.keys
    return False


# frob:ticket T-2944
def _scan_platform_string_guards(tree: ast.Module) -> tuple[_PlatformSite, ...]:
    """Every silent platform-string no-op degrade (T-2944 shape 2) --
    body is `_is_degrade_body`-shaped and neither `_guard_is_loud` nor
    `_guard_logs`. Checks the guard's OWN body only, never a caller
    elsewhere: `arm_parent_death_signal`'s guard is caught here even
    though its caller happens to log, since this scan cannot see across
    call sites and a future guard with no lucky caller needs catching."""
    sites: list[_PlatformSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not _is_platform_string_guard_test(node.test):
            continue
        if _guard_is_loud(node.body) or _guard_logs(node.body):
            continue
        if not _is_degrade_body(node.body):
            continue
        sites.append(_PlatformSite(node.lineno, ("<platform-string>",)))
    return tuple(sites)


# frob:ticket T-2944
def _scan_bare_restricted_imports(tree: ast.Module) -> tuple[_PlatformSite, ...]:
    """Every module-TOP-LEVEL `import X` (never nested in a `try:`)
    naming a `_PLATFORM_RESTRICTED_MODULES` module -- T-2944 shape 3,
    the T-2952 regression class (`_new_renumber.py` et al's bare
    `import fcntl`); this scan is the regression guard."""
    guarded_import_ids = {
        id(stmt)
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for stmt in node.body
        if isinstance(stmt, ast.Import)
    }
    sites: list[_PlatformSite] = []
    for stmt in tree.body:
        if not isinstance(stmt, ast.Import) or id(stmt) in guarded_import_ids:
            continue
        for alias in stmt.names:
            if alias.name in _PLATFORM_RESTRICTED_MODULES:
                sites.append(_PlatformSite(stmt.lineno, (alias.name,)))
    return tuple(sites)


def _is_none_names(test: ast.expr, guard_names: frozenset[str]) -> frozenset[str]:
    """The subset of `guard_names` that `test` compares to `None` --
    handles a single `X is None` as well as an `X is None and Y is
    None [and ...]` chain (T-2918's own `if fcntl is None and msvcrt is
    None:` shape, the "neither primitive" case). Returns an empty
    frozenset when `test` matches no guard name at all, which callers
    treat as "not a platform-availability guard"."""
    if isinstance(test, ast.Compare):
        if (
            isinstance(test.left, ast.Name)
            and test.left.id in guard_names
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Is)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value is None
        ):
            return frozenset({test.left.id})
        return frozenset()
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        hit: set[str] = set()
        for value in test.values:
            hit |= _is_none_names(value, guard_names)
        return frozenset(hit)
    return frozenset()


#: T-2934: typani's two Result constructors -- a `return Ok(...)`/
#: `return Err(...)` is a STRUCTURED, typed exit distinct from falling
#: through to whatever the normal-success code path does, matching this
#: repo's dominant error-handling convention (see `~/.claude/refs/
#: typani.md`, "PREFER pydantic and typani"). `_guard_is_loud` treats
#: either constructor as loud: measured false positive on
#: `frob.tickets._land_git_ops.reclaim_orphaned_squash_residue`'s real
#: `if _fcntl is None: _log.warning(...); return Ok(False)` -- that
#: function's whole job is "decide whether it is SAFE to mutate", and
#: `Ok(False)` there means "decided no, on purpose, logged" (a real,
#: visible, controlled abort of the risky operation), not "proceeded as
#: if the missing primitive did not matter" the way `_baseline_lock`'s
#: pre-T-2918 bug did. `Err(...)` is the more obviously-loud half of the
#: same pair; `Ok(...)` earns the same treatment because the discriminator
#: PLATFORM001 actually cares about is "did the guard body take an
#: explicit, typed exit instead of continuing normal flow", not "did it
#: specifically signal failure" -- a plain `return None`/bare `return`/
#: fallthrough is NOT a typed exit and still fires (see the must-fire
#: fixture, `TestPlatform001._WARN_AND_CONTINUE_SRC`, which returns
#: `None` with no such constructor).
_TYPED_EXIT_RESULT_CONSTRUCTORS = frozenset({"Ok", "Err"})


def _is_typed_result_return(node: ast.stmt) -> bool:
    """Whether `node` is a `return Ok(...)`/`return Err(...)` (bare name
    or dotted, e.g. `typani.Ok(...)`) -- see `_TYPED_EXIT_RESULT_
    CONSTRUCTORS`'s own docstring for why this counts as loud."""
    if not isinstance(node, ast.Return) or node.value is None:
        return False
    if not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    name = func.id if isinstance(func, ast.Name) else _attr_name(func)
    return name in _TYPED_EXIT_RESULT_CONSTRUCTORS


def _guard_is_loud(body: list[ast.stmt]) -> bool:
    """Whether a platform-guard `If.body` refuses LOUDLY: contains a
    `raise` anywhere, a top-level `sys.exit(...)`/`os._exit(...)` call,
    or a `return Ok(...)`/`return Err(...)` typed exit (T-2934,
    `_TYPED_EXIT_RESULT_CONSTRUCTORS`) -- the shapes this rule accepts
    as "declared, not silent" (T-2918's own `BaselineLockUnavailable`
    fix uses the first). A plain `return`/fallthrough with no typed
    constructor is still NOT loud -- distinguishing a genuinely
    structured exit from an ordinary silent one is exactly the line
    T-2934 measured a real false positive on and narrowed this
    function to draw correctly, rather than papering over it with a
    `frob:waive` on the first real site this brand-new rule found."""
    for stmt in body:
        if _is_typed_result_return(stmt):
            return True
        for node in ast.walk(stmt):
            if isinstance(node, ast.Raise):
                return True
            if isinstance(node, ast.Call) and _dotted_prefix(node.func) in (
                "sys.exit",
                "os._exit",
            ):
                return True
    return False


def _guard_logs(body: list[ast.stmt]) -> bool:
    """Whether `body` contains a call shaped like `<anything>.<level>(...)`
    for a level in `_LOG_CALL_ATTRS` -- the observable half of "warn-and-
    continue" (module logger convention `_log.warning(...)` throughout
    this codebase, matched on the attribute name alone since resolving
    the receiver to an actual `logging.Logger` instance is out of scope
    for a single-pass AST scan, same posture `_pii_structural` already
    takes for its own attribute-name heuristics)."""
    for stmt in body:
        for node in ast.walk(stmt):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _LOG_CALL_ATTRS
            ):
                return True
    return False


@dataclass(frozen=True)
class _PlatformSite:
    """One PLATFORM001 finding site: the guard's line and the primitive
    name(s) it tested for absence."""

    lineno: int
    names: tuple[str, ...]


def _scan_platform_guards(tree: ast.Module) -> tuple[_PlatformSite, ...]:
    """Every `if <platform-optional-name> is None [and ...]:` guard in
    `tree` whose body logs (module docstring's warn-and-continue shape)
    but never refuses loudly (`_guard_is_loud`) -- PLATFORM001's actual
    findings."""
    guard_names = _platform_guard_names(tree)
    if not guard_names:
        return ()
    sites: list[_PlatformSite] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        hit = _is_none_names(node.test, guard_names)
        if not hit:
            continue
        if _guard_logs(node.body) and not _guard_is_loud(node.body):
            # frob:waive PERF004 reason="sorted(hit) sorts a 1-2-element set (the platform-optional names one `if X is None [and Y is None]:` test names) at most once per matched guard site across a whole file's AST walk -- not a hot loop, and the call exists only so `_PlatformSite.names` has a deterministic tuple order for the Violation message/tests"  # noqa: E501
            sites.append(_PlatformSite(node.lineno, tuple(sorted(hit))))
    return tuple(sites)


# frob:enforces CHK-GATE-PLATFORM001
def _platform001_violation(rel_path: str, site: _PlatformSite) -> Violation:
    """The PLATFORM001 `Violation` for one warn-and-continue platform
    guard (module docstring)."""
    names = " and ".join(f"`{n}` is None" for n in site.names)
    _log.warning(
        "PLATFORM001: %s:%d guard on %s logs and proceeds unlocked/unguarded "
        "instead of refusing loudly",
        rel_path,
        site.lineno,
        names,
    )
    return Violation(
        rule="PLATFORM001",
        severity=Severity.WARN,
        file=rel_path,
        line=site.lineno,
        message=(
            f"PLATFORM001: {rel_path}:{site.lineno} a guard on {names} logs a "
            f"warning and then proceeds as if the missing primitive did not "
            f"matter -- a POSIX/Windows-only primitive with no other "
            f"platform available must either declare a real cross-platform "
            f"path (a second backend, an `elif` branch trying another "
            f"primitive) or refuse LOUDLY (`raise`, `sys.exit`), never "
            f'warn-and-continue (T-2918); `frob:waive PLATFORM001 '
            f'reason="..."` if this is a real structured-error return this '
            f"detector's AST scan cannot see (module docstring's disclosed "
            f"gap)"
        ),
    )


# frob:enforces CHK-GATE-PLATFORM001
# frob:ticket T-2944
def _platform001_string_violation(rel_path: str, site: _PlatformSite) -> Violation:
    """The PLATFORM001 `Violation` for one silent platform-STRING degrade
    (`_scan_platform_string_guards`, T-2944 shape 2)."""
    _log.warning(
        "PLATFORM001: %s:%d a platform-string guard degrades silently "
        "instead of refusing loudly",
        rel_path,
        site.lineno,
    )
    return Violation(
        rule="PLATFORM001",
        severity=Severity.WARN,
        file=rel_path,
        line=site.lineno,
        message=(
            f"PLATFORM001: {rel_path}:{site.lineno} a `sys.platform`/"
            f"`os.name`/`platform.system()` guard returns a falsy/no-op "
            f"value with no raise and no log in its OWN body (T-2944) -- "
            f"a caller elsewhere that logs is invisible to this scan; "
            f"declare a real fallback, refuse LOUDLY, or log in the "
            f'guard itself, or `frob:waive PLATFORM001 reason="..."` if '
            f"this is a structured-error return this scan cannot see"
        ),
    )


# frob:enforces CHK-GATE-PLATFORM001
# frob:ticket T-2944
def _platform001_bare_import_violation(rel_path: str, site: _PlatformSite) -> Violation:
    """The PLATFORM001 `Violation` for one bare unconditional import of a
    platform-restricted module (`_scan_bare_restricted_imports`, T-2944
    shape 3 -- the T-2952 regression class)."""
    module_name = site.names[0]
    _log.warning(
        "PLATFORM001: %s:%d bare unconditional `import %s` has no "
        "platform guard at all",
        rel_path,
        site.lineno,
        module_name,
    )
    return Violation(
        rule="PLATFORM001",
        severity=Severity.WARN,
        file=rel_path,
        line=site.lineno,
        message=(
            f"PLATFORM001: {rel_path}:{site.lineno} bare unconditional "
            f"`import {module_name}` has no platform guard -- crashes the "
            f"IMPORT of this module on any platform lacking `{module_name}` "
            f"(T-2952); guard with `try: import {module_name} / except "
            f"ImportError: {module_name} = None`, or `frob:waive "
            f'PLATFORM001 reason="..."` if never imported cross-platform'
        ),
    )


# frob:doc docs/modules/gates.md#walk001-unpruned-traversal-t-0471
# frob:tests tests/test_walk_lint_gate.py::TestRglob.test_raw_rglob_fires
# frob:tests tests/test_walk_lint_gate.py::TestHelper.test_helper_call_is_silent
# frob:tests tests/test_walk_lint_gate.py::TestSelfMatchExclusion.test_own_files_not_scanned  # noqa: E501
# frob:doc \
# docs/modules/gates.md#platform001-posix-only-primitive-degrades-silently-t-2919
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001.test_warn_and_continue_fires  # noqa: E501
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001.test_loud_refusal_is_quiet  # noqa: E501
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001.test_no_platform_probe_is_quiet  # noqa: E501
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001StringGuard.test_silent_string_guard_fires  # noqa: E501
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001StringGuard.test_logged_string_guard_is_quiet  # noqa: E501
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001StringGuard.test_real_platform_branch_is_quiet  # noqa: E501
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001BareImport.test_bare_import_fires  # noqa: E501
# frob:tests tests/test_walk_lint_gate.py::TestPlatform001BareImport.test_guarded_import_is_quiet  # noqa: E501
# frob:invariant INV-005
# invariant spec: [INV-005](invariants/INV-005.md)
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling so one bad file cannot abort the whole WALK001 pass; the documented behavior is unchanged, so docs/modules/gates.md#walk001-unpruned-traversal-t-0471 needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
# frob:ticket T-2944
def walk_lint_gate(root: Path) -> tuple[Violation, ...]:
    """WALK001 (docs/modules/gates.md#walk001-unpruned-traversal-t-0471)
    and PLATFORM001 (docs/modules/gates.md#platform001-posix-only-
    primitive-degrades-silently-t-2919, T-2919): every git-tracked
    `src/frob/**/*.py` file scanned, in one pass, for a raw recursive
    traversal call that bypasses `frob.excludes`' shared prune-aware
    helpers (WALK001) and for a POSIX/Windows-only primitive's absence
    guard that logs and silently proceeds instead of declaring a real
    fallback or refusing loudly (PLATFORM001). Self-excludes this module
    and `frob/excludes.py` (module docstring)."""
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
        try:
            violations.extend(
                _walk001_violation(rel_path, site) for site in _scan_python_walks(tree)
            )
            violations.extend(
                _platform001_violation(rel_path, site)
                for site in _scan_platform_guards(tree)
            )
            violations.extend(
                _platform001_string_violation(rel_path, site)
                for site in _scan_platform_string_guards(tree)
            )
            violations.extend(
                _platform001_bare_import_violation(rel_path, site)
                for site in _scan_bare_restricted_imports(tree)
            )
        except Exception:
            # One file's AST shape confusing the walk-site scanner must
            # not abort the whole WALK001/PLATFORM001 pass over every
            # OTHER tracked file (EXHAUST001/EXHAUST002, T-1371) -- same
            # "skip just this one" posture as the parse-failure branch
            # above.
            _log.debug("walk_lint_gate: skipping unscannable %s", rel_path)

    _log.info(
        "walk_lint_gate: scanned %d tracked src/frob .py file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = ["walk_lint_gate"]
