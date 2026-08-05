# frob:waive INV006 reason="module/design docstring prose: the 'only' claims describe \
# this module's own implemented detection-scope rules (which decorator name it \
# matches, which read call shapes it recognizes), verifiable by reading the code they \
# annotate -- not a separate cross-module contract needing a tracked invariant; same \
# disposition as the T-0585 first-turn-on calibration batch other gate modules in this \
# package carry (e.g. src/frob/gates/_gate_cache.py's identical waiver)"
"""CACHE001: a `@memoize_per_run`-decorated computation's OBSERVED read-set
must be covered by its declared cache-key inputs (T-1520).

Root cause this closes (the T-1454 incident shape, `docs/audits/` and
`invariants/INV-050.md`'s own "Full cache inventory" section): a cached
computation reads an input its cache key does not cover, so a change to
that input serves a stale result forever, silently. `frob.check._memo.
memoize_per_run`'s cache key is exactly (and only) the decorated function's
own call arguments (`_freeze`d, T-0423) -- so if the function's BODY reads
something no argument derives from (a hardcoded path, `os.environ`, a
module-level global), that read is invisible to the key and a stale
memoized result can be served across a run boundary the read's own target
changed within, the SAME class of bug T-1454 hit for `frob.gates.
_gate_cache`'s bespoke digest-keyed cache (a sibling, unrelated cache
mechanism -- CACHE001 covers the `memoize_per_run` shape specifically,
where "declared cache-key inputs" literally means "this function's own
parameter list").

Detection is AST-based (Python's own `ast` module), the same structural-
gate precedent `frob.gates._walk_lint`/`frob.gates._pii_structural` already
establish and this module's docstring borrows verbatim reasoning from: a
lexical/regex scan would both over- and under-fire on multi-line calls,
aliased imports, and string content that merely mentions a flagged shape,
where a real `ast.Call`/`ast.Attribute` match does not.

Scope (T-1520's own "detector core, not every wrapper" acceptance): this
first cut only recognizes `@memoize_per_run` (imported by name, matching
this repo's own single real usage sites -- `frob.arch.analyze_project`,
`frob.dup._legacy.find_duplicates`, `frob.graph.build_graph`) as the
"cached computation" surface, and only a function's OWN body (not callees
it transitively reaches) for observed reads. Both are real, disclosed
narrowings, not silent gaps -- see `invariants/INV-050.md`'s own
follow-up-ticket precedent for the same "core now, long tail later"
posture, and the module-level `frob:waive` escape hatch below for the
already-known exception (`frob.lang.parse_file`'s content-hash-keyed
artifact cache, a DIFFERENT and already-correct cache-key discipline this
detector's decorator-name match cannot see since it never uses the
`@memoize_per_run` decorator syntax at all -- it is wrapped dynamically,
per that module's own docstring).
"""

# frob:ticket T-1520

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._walk_lint import tracked_python_files_for_gate
from frob.logging import get_logger

_log = get_logger(__name__)

#: The decorator name this detector recognizes as "persistent-cache-backed,
#: with the call arguments AS the declared cache key" -- matched by bare
#: name (`@memoize_per_run`) since every real usage in this repo imports it
#: unaliased (`from frob.check._memo import memoize_per_run`).
_MEMO_DECORATOR = "memoize_per_run"

#: Read-effect call shapes this detector treats as "observes external,
#: potentially-mutable state" -- a `Path`-method read, the `open()`
#: builtin, or an `os.environ`/`os.getenv` access. Anything else (pure
#: computation over already-passed-in values) is out of scope by
#: construction: CACHE001 only cares about reads that could silently make
#: a memoized result stale.
_READ_METHOD_ATTRS = frozenset({"read_text", "read_bytes", "open"})
_ENV_ATTRS = frozenset({"environ", "getenv"})


@dataclass(frozen=True)
class _UncoveredRead:
    """One CACHE001 site: a read at `lineno` inside `func_name`, whose
    target expression names no parameter of the enclosing
    `@memoize_per_run` function."""

    lineno: int
    func_name: str
    read_desc: str


def _is_memo_decorated(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether `node` carries a bare `@memoize_per_run` decorator (T-1520
    scope: name-matched, not import-resolved -- see module docstring)."""
    return any(
        isinstance(dec, ast.Name) and dec.id == _MEMO_DECORATOR
        for dec in node.decorator_list
    )


def _param_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    """Every parameter name `node` binds (positional, keyword-only, `*args`/
    `**kwargs`) -- the declared cache-key input surface `memoize_per_run`'s
    own `_freeze`d-args key is built from."""
    args = node.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    if args.vararg:
        names.append(args.vararg.arg)
    if args.kwarg:
        names.append(args.kwarg.arg)
    return frozenset(names)


def _subtree_references_any(node: ast.expr, names: frozenset[str]) -> bool:
    """Whether any `ast.Name` inside `node`'s own subtree resolves to one of
    `names` -- the "is this read's target derived from a declared cache-key
    input" test: a literal free variable (a hardcoded path, a module
    global) has none of the function's own parameter names anywhere in its
    expression tree."""
    return any(isinstance(n, ast.Name) and n.id in names for n in ast.walk(node))


def _read_desc(call: ast.Call) -> str:
    """A human-readable description of the flagged read call."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return f"...{func.attr}(...)"
    if isinstance(func, ast.Name):
        return f"{func.id}(...)"
    return "<read>(...)"


def _scan_function_reads(
    node: ast.FunctionDef | ast.AsyncFunctionDef, param_names: frozenset[str]
) -> list[_UncoveredRead]:
    """Every observed-read call inside `node`'s OWN body (not nested
    `def`s -- see `ast.walk` note below) whose target expression names none
    of `param_names`."""
    found: list[_UncoveredRead] = []
    for inner in ast.walk(node):
        # Do not descend into a nested function/lambda's own scope: its
        # reads are that inner callable's own concern, not this outer
        # memoized function's cache-key surface (a nested closure captures
        # variables lexically, not as call-args this detector can see).
        if inner is not node and isinstance(
            inner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
        ):
            continue
        if not isinstance(inner, ast.Call):
            continue
        func = inner.func
        if isinstance(func, ast.Attribute) and func.attr in _READ_METHOD_ATTRS:
            if not _subtree_references_any(func.value, param_names):
                found.append(_UncoveredRead(inner.lineno, node.name, _read_desc(inner)))
        elif isinstance(func, ast.Name) and func.id == "open":
            if inner.args and not _subtree_references_any(inner.args[0], param_names):
                found.append(_UncoveredRead(inner.lineno, node.name, _read_desc(inner)))
        elif (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
            and func.attr in _ENV_ATTRS
        ):
            # os.environ/os.getenv are never parameter-derived by
            # construction -- always uncovered.
            found.append(
                _UncoveredRead(inner.lineno, node.name, f"os.{func.attr}(...)")
            )
    for inner in ast.walk(node):
        if (
            isinstance(inner, ast.Attribute)
            and inner.attr == "environ"
            and isinstance(inner.value, ast.Name)
            and inner.value.id == "os"
            and not isinstance(inner.ctx, ast.Store)
        ):
            found.append(_UncoveredRead(inner.lineno, node.name, "os.environ"))
    return found


def _scan_memoized_functions(tree: ast.Module) -> tuple[_UncoveredRead, ...]:
    """Every uncovered-read site inside every `@memoize_per_run`-decorated
    top-level or class-method function in `tree`."""
    sites: list[_UncoveredRead] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _is_memo_decorated(node):
            continue
        params = _param_names(node)
        sites.extend(_scan_function_reads(node, params))
    return tuple(sites)


# frob:enforces CHK-GATE-CACHE001
def _cache001_violation(rel_path: str, site: _UncoveredRead) -> Violation:
    """The CACHE001 `Violation` for one uncovered-read site."""
    _log.warning(
        "CACHE001: %s:%d %s reads %s not covered by any parameter of "
        "@memoize_per_run function %s",
        rel_path,
        site.lineno,
        site.func_name,
        site.read_desc,
        site.func_name,
    )
    return Violation(
        rule="CACHE001",
        severity=Severity.ERROR,
        file=rel_path,
        line=site.lineno,
        message=(
            f"CACHE001: {rel_path}:{site.lineno} @memoize_per_run function "
            f"{site.func_name} reads {site.read_desc}, whose target is not "
            f"derived from any of {site.func_name}'s own parameters -- this "
            f"read is invisible to memoize_per_run's args-only cache key, so "
            f"a change to it between two calls in the same run can serve a "
            f"stale memoized result (the T-1454 incident shape); pass the "
            f"read target in as a parameter, or "
            f'`frob:waive CACHE001 reason="..."` if this read is genuinely '
            f"immutable for a run's duration"
        ),
    )


# frob:doc docs/modules/gates.md#rule-catalog
# frob:tests tests/test_cache_gate.py::TestMemoizedReadCoverage.test_uncovered_read_fires  # noqa: E501
# frob:tests tests/test_cache_gate.py::TestMemoizedReadCoverage.test_silent_shapes  # noqa: E501
def cache_gate(root: Path) -> tuple[Violation, ...]:
    """CACHE001: every git-tracked `src/frob/**/*.py` `@memoize_per_run`
    function scanned for a read whose target is not derived from any of its
    own parameters (module docstring). Self-excludes this module (its own
    docstring/prose mentions the flagged shapes, same posture
    `_walk_lint.py` documents for its own analogous self-match risk)."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in tracked_python_files_for_gate(root, log_prefix="cache_gate"):
        if rel_path == "src/frob/gates/_cache_gate.py":
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
            tree = ast.parse(text, filename=rel_path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            _log.debug("cache_gate: skipping unparseable %s", rel_path)
            continue
        scanned += 1
        try:
            violations.extend(
                _cache001_violation(rel_path, site)
                for site in _scan_memoized_functions(tree)
            )
        except Exception:
            # One file's AST shape confusing the scanner must not abort the
            # whole CACHE001 pass over every OTHER tracked file
            # (EXHAUST001/EXHAUST002 posture, matching _walk_lint_gate's
            # identical guard).
            _log.debug("cache_gate: skipping unscannable %s", rel_path)

    _log.info(
        "cache_gate: scanned %d tracked src/frob .py file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = ["cache_gate"]
