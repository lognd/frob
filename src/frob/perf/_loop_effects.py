"""PERF008: loop-invariant effectful call detector (T-0775).

Motivated by the 2026-07-22 rev-parse incident (T-0773): `frob ticket list`
spawned `git rev-parse --git-common-dir` dozens of times because the LOOP
(one iteration per ticket row) and the EFFECT (a subprocess spawn, three
calls deep through `frob.gitio.run_argv`) live in different modules/
functions -- no per-function syntactic PERF heuristic (PERF001-004, all
scoped to one function body) can ever see this shape.

Two pieces, both best-effort and deliberately over-recall (the repo
philosophy: "undecidable invariance leans toward firing"):

1. DIRECT EFFECT DETECTION (`_direct_effect`): a call is directly
   effectful if its own dotted callee name matches a known process-spawn
   or filesystem-walk pattern (`_SPAWN_PATTERNS`/`_FS_WALK_PATTERNS`) --
   the same small, hand-picked needle tables `frob.vet._capability_registry`
   uses for the "exec"/"fs" capability kinds, narrowed here to the spawn
   and directory-walk subset this ticket actually names (T-0775's
   acceptance criteria never mention bare file read/write, so the broader
   "fs"/"fs-read"/"fs-write" registry kinds are intentionally NOT pulled
   in here -- that would fire on every `open()` call in a loop, a
   different and much noisier check no ticket has asked for).

2. TRANSITIVE CALL-GRAPH REACHABILITY (`_EffectGraph`): a small, local,
   whole-project, NAME-based call graph -- deliberately NOT
   `frob.graph.callgraph.build_call_graph` (which only ever resolves
   PRIVATE callees, by design, to stop its own BFS at the public-API
   boundary). The real T-0773 incident crosses that exact boundary: the
   effectful call lives behind `frob.gitio.run_argv`, a PUBLIC function
   called from a private helper in a completely different package. This
   module needs the opposite resolution rule -- every candidate, public
   or private, is a real edge -- so, matching `frob.perf._recursion`'s own
   precedent ("a second small graph is built locally instead of widening
   `callgraph`'s contract for a use case it was not designed for"), a
   second, broader graph is built here instead.

DETECTION: for each `for`/`while` loop (Python only for now -- an
accepted scope cut, matching PERF001-004's existing python-first/other-
language-best-effort tiering; see this module's own TODO below), for
each call site lexically inside that loop's body (attributed to its
INNERMOST enclosing loop when loops nest), determine whether the call is
itself directly effectful OR transitively reaches a directly-effectful
callee via `_EffectGraph`. If so, and every argument at the call site is
LOOP-INVARIANT (its source text names neither the loop's own bound
variable(s) nor any name assigned anywhere in the loop's body), fire
PERF008 naming the call site, the effectful callee, and why its
arguments look invariant. WARN-tier, not ERROR: `frob:waive` with a
reason is always available (T-0775's own acceptance: "re-reading mutable
state can be deliberate under concurrency, so this is warn-tier with an
unwaivable-style justification requirement, not a silent error").

# frob:todo T-0775 non-python (typescript/rust/cpp) coverage for PERF008
# is out of this ticket's scope, same posture as PERF001-004's existing
# python-first tiering -- track any follow-up need as its own ticket
# rather than silently expanding this one.
"""
# frob:waive INV006 reason="T-0775 first-turn-on: this module's \
# 'deliberately NOT'/'only ever' exclusivity language (module docstring, \
# _EffectGraph docstring) is source-level design-rationale prose \
# describing already-implemented internal behavior, verifiable by reading \
# the code it annotates, rather than a separate cross-module contract \
# needing its own tracked invariant -- same disposition as the identical \
# T-0585 calibration-batch waiver already carried by _redundancy.py and \
# _rules.py in this same package"

from __future__ import annotations

import re
from collections import deque
from collections.abc import Sequence
from pathlib import Path

from tree_sitter import Node

from frob.gates._models import Severity, Violation
from frob.lang import child_by_field as _child_by_field
from frob.lang import node_text as _node_text
from frob.lang import raw_tree as _raw_tree
from frob.lang._models import ParsedFile, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["loop_invariant_effect_violations"]

_FUNCTION_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD})

#: Dotted `(receiver, attribute)` shapes that spawn a subprocess -- the same
#: needle set `frob.vet._capability_registry`'s "exec" rows watch for in
#: third-party dependency source, narrowed to the ones meaningful as a
#: python call-site pattern here.
_SPAWN_DOTTED: frozenset[tuple[str, str]] = frozenset(
    {
        ("subprocess", "run"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("subprocess", "check_call"),
        ("subprocess", "check_output"),
        ("os", "system"),
        ("os", "popen"),
        ("os", "spawnl"),
        ("os", "spawnv"),
        ("os", "spawnve"),
    }
)
#: Bare (undotted) names that spawn a subprocess when imported directly
#: (`from subprocess import Popen; Popen(...)`).
_SPAWN_BARE: frozenset[str] = frozenset({"Popen"})

#: Dotted filesystem-directory-walk shapes -- `os.walk`, `os.scandir`, a
#: `Path`-typed receiver's `.rglob`/`.iterdir`/`.walk` (py3.12), `glob.glob`.
_FS_WALK_DOTTED: frozenset[tuple[str, str]] = frozenset(
    {
        ("os", "walk"),
        ("os", "scandir"),
        ("glob", "glob"),
        ("glob", "iglob"),
    }
)
#: Attribute-only shapes (any receiver) that mean a directory walk -- these
#: cannot be pinned to one dotted receiver name (`p.rglob(...)`, `path.
#: iterdir()`, `root.walk()` are all common receiver spellings for a
#: `pathlib.Path`), so they are matched on the attribute name alone.
_FS_WALK_ATTRS: frozenset[str] = frozenset({"rglob", "iterdir"})

_LOOP_KINDS = frozenset({"for_statement", "while_statement"})

# Bounded BFS over `_EffectGraph` -- same posture as
# `frob.graph.callgraph`'s `_DEFAULT_MAX_DEPTH`/`_DEFAULT_MAX_NODES`
# (T-0773's own incident was three calls deep; these leave headroom
# without letting a pathological project's call graph make PERF008 itself
# the next `frob check` bottleneck).
_MAX_DEPTH = 8
_MAX_NODES = 200

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ASSIGN_TARGET_RE = re.compile(r"(?<![=!<>])\b([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)")


def _callee_dotted(node: Node) -> tuple[str, str] | None:
    """`(receiver, attribute)` for a call node's `obj.attr(...)` function
    expression, or `None` if the call target is not a simple dotted
    attribute access (a bare name, a subscript, a chained call, ...)."""
    func = _child_by_field(node, "function")
    if func is None or func.type != "attribute":
        return None
    obj = _child_by_field(func, "object")
    attr = _child_by_field(func, "attribute")
    if obj is None or attr is None:
        return None
    return _node_text(obj), _node_text(attr)


def _callee_bare(node: Node) -> str | None:
    """The bare identifier name for a call node's function expression, or
    `None` if it is not a plain unqualified call (`name(...)`)."""
    func = _child_by_field(node, "function")
    if func is not None and func.type == "identifier":
        return _node_text(func)
    return None


def _direct_effect(node: Node) -> str | None:
    """`"spawn"` or `"fs-walk"` if `node` (a `call` node) is itself a direct
    process-spawn or directory-walk call, else `None` -- see this module's
    docstring for the exact needle tables."""
    dotted = _callee_dotted(node)
    if dotted is not None:
        if dotted in _SPAWN_DOTTED:
            return "spawn"
        if dotted in _FS_WALK_DOTTED or dotted[1] in _FS_WALK_ATTRS:
            return "fs-walk"
    bare = _callee_bare(node)
    if bare is not None and bare in _SPAWN_BARE:
        return "spawn"
    return None


def _callee_short_name(node: Node) -> str | None:
    """The callee's own short name for by-name graph resolution: the bare
    name for an unqualified call, or the attribute name for a dotted one
    (`self._foo(...)` / `helper.run(...)` both resolve on `_foo`/`run`,
    matching `frob.graph.callgraph`'s own by-short-name posture)."""
    bare = _callee_bare(node)
    if bare is not None:
        return bare
    dotted = _callee_dotted(node)
    if dotted is not None:
        return dotted[1]
    return None


class _EffectGraph:
    """A local, whole-project, best-effort NAME-based call graph over every
    FUNCTION/METHOD symbol in the files this run was given, built solely to
    answer "does calling `qualname` transitively reach a directly-
    effectful call" (see module docstring for why this is a second graph,
    not `frob.graph.callgraph.build_call_graph`).

    Built once per `loop_invariant_effect_violations` call and reused
    across every loop/call site in the run -- reachability answers are
    memoized per starting symref (`_reachable`), since the same widely-
    called helper (e.g. `run_argv`) is typically the reachability target
    for many distinct callers."""

    def __init__(self, files: Sequence[ParsedFile]) -> None:
        """Index every function/method symbol's own direct effect (from its
        `body_tokens`, a cheap pre-check before the expensive AST walk) and
        its called-name set, keyed by short name for best-effort
        resolution."""
        self._by_name: dict[str, list[str]] = {}
        self._direct: dict[str, str] = {}
        self._called: dict[str, frozenset[str]] = {}
        self._memo: dict[str, str | None] = {}
        for file in files:
            for sym in file.symbols:
                if sym.kind not in _FUNCTION_KINDS:
                    continue
                symref = f"{file.path}::{sym.qualname}"
                self._by_name.setdefault(sym.qualname.rsplit(".", 1)[-1], []).append(
                    symref
                )
                effect = _direct_effect_from_tokens(sym.body_tokens)
                if effect is not None:
                    self._direct[symref] = effect
                self._called[symref] = _called_names_from_tokens(sym.body_tokens)

    def _effect_reachable_from_name(self, callee_name: str) -> tuple[str, str] | None:
        """`(effect_kind, symref)` for the first directly-effectful function
        transitively reachable by calling ANY symbol named `callee_name`
        (best-effort, ambiguous names all tried), or `None` if nothing
        reachable within the bounded BFS is directly effectful."""
        for symref in self._by_name.get(callee_name, ()):
            hit = self._reachable(symref)
            if hit is not None:
                return hit
        return None

    def _reachable(self, start: str) -> tuple[str, str] | None:
        """Bounded BFS from `start` (inclusive) over `_called`, returning the
        first directly-effectful symref found -- memoized per `start` so a
        shared callee's reachability is computed once regardless of how
        many distinct loop call sites ask about it."""
        if start in self._memo:
            cached = self._memo[start]
            return None if cached is None else (self._direct.get(cached, ""), cached)
        direct = self._direct.get(start)
        if direct is not None:
            self._memo[start] = start
            return direct, start
        seen = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        found: str | None = None
        while queue and len(seen) < _MAX_NODES:
            current, depth = queue.popleft()
            if depth >= _MAX_DEPTH:
                continue
            for name in self._called.get(current, ()):
                for candidate in self._by_name.get(name, ()):
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    if candidate in self._direct:
                        found = candidate
                        queue.clear()
                        break
                    queue.append((candidate, depth + 1))
                if found is not None:
                    break
        self._memo[start] = found
        if found is None:
            return None
        return self._direct[found], found


def _direct_effect_from_tokens(tokens: tuple[str, ...]) -> str | None:
    """Cheap token-level pre-check mirroring `_direct_effect`'s AST version,
    used to seed `_EffectGraph` without re-parsing every file's tree --
    `body_tokens` is a flat leaf stream, so this only recognizes the
    `name . attr (` dotted shape and bare `Popen(`, same needle tables."""
    n = len(tokens)
    for i in range(n - 3):
        if tokens[i + 1] != "." or tokens[i + 3] != "(":
            continue
        pair = (tokens[i], tokens[i + 2])
        if pair in _SPAWN_DOTTED:
            return "spawn"
        if pair in _FS_WALK_DOTTED or tokens[i + 2] in _FS_WALK_ATTRS:
            return "fs-walk"
    for i in range(n - 1):
        if tokens[i] in _SPAWN_BARE and tokens[i + 1] == "(":
            return "spawn"
    return None


def _called_names_from_tokens(tokens: tuple[str, ...]) -> frozenset[str]:
    """Every callee short name (bare `name(` or the attribute half of `obj.
    name(`) referenced in `tokens` -- `_EffectGraph`'s call-edge extractor,
    deliberately including BOTH public and private names (unlike `frob.
    graph.callgraph`'s private-only resolution -- see module docstring)."""
    names: set[str] = set()
    n = len(tokens)
    for i in range(n - 1):
        if tokens[i + 1] != "(" or not tokens[i].isidentifier():
            continue
        names.add(tokens[i])
    return frozenset(names)


def _loop_bound_names(loop: Node) -> frozenset[str]:
    """Every identifier bound by a `for`'s target (`left` field) -- `()` for
    a `while` loop, which binds nothing. Handles tuple-unpacking targets
    (`for k, v in d.items():`) by collecting every identifier under `left`,
    not just a single top-level name."""
    if loop.type != "for_statement":
        return frozenset()
    left = _child_by_field(loop, "left")
    if left is None:
        return frozenset()
    return frozenset(_IDENT_RE.findall(_node_text(left)))


def _assigned_in_body(body_text: str) -> frozenset[str]:
    """Every name that is the target of a plain `name = ...` assignment
    anywhere in `body_text` -- used to extend "loop-variant" to a name
    DERIVED from the loop variable inside the loop body (`x = row.id;
    helper(x)`), not just the bound variable itself. Textual/best-effort,
    not scope-aware (matches this package's posture elsewhere): a name
    that happens to be reassigned in an unrelated nested scope still
    counts, which only widens what counts as "variant" -- i.e. never turns
    a real hazard into a false negative by missing an assignment; the
    accepted cost is the opposite (a rare missed finding), never a false
    accusation."""
    return frozenset(_ASSIGN_TARGET_RE.findall(body_text))


def _is_loop_invariant(
    call_node: Node, loop_vars: frozenset[str], derived_names: frozenset[str]
) -> bool:
    """True if `call_node`'s own argument list mentions neither a loop-bound
    name nor a name assigned inside the loop body -- see module docstring
    for why this is a text-token scan over the arguments span rather than a
    full dataflow analysis (undecidable in general; this stays a cheap,
    over-recall approximation, same posture as every other PERF rule)."""
    variant_names = loop_vars | derived_names
    if not variant_names:
        return True
    args = _child_by_field(call_node, "arguments")
    if args is None:
        return True
    used = frozenset(_IDENT_RE.findall(_node_text(args)))
    return not (used & variant_names)


def _iter_loop_call_sites(root: Node) -> list[tuple[Node, Node]]:
    """Every `(call_node, innermost_enclosing_loop)` pair in the tree rooted
    at `root` -- a call outside any loop is never yielded. A call inside
    nested loops is attributed to the INNERMOST one only (each loop still
    gets its own pass at any call nested even deeper via its own,
    separately-collected pair when that inner loop is walked)."""
    hits: list[tuple[Node, Node]] = []
    stack: list[tuple[Node, Node | None]] = [(root, None)]
    while stack:
        node, current_loop = stack.pop()
        if node.type in _LOOP_KINDS:
            body = _child_by_field(node, "body")
            for child in node.children:
                # `child is body` would always be False here -- tree-sitter
                # Node wrapper objects are re-created per access, not
                # identity-stable, even for the same underlying node
                # (confirmed empirically); `==` compares the underlying
                # node correctly.
                stack.append((child, node if child == body else current_loop))
            continue
        if node.type == "call" and current_loop is not None:
            hits.append((node, current_loop))
        stack.extend((child, current_loop) for child in node.children)
    return hits


def _file_violations(path: str, graph: _EffectGraph) -> list[Violation]:
    """Every PERF008 hit in one python source file, re-parsed via
    `frob.lang.raw_tree` (not reused from `ParsedFile.symbols`, which
    carries no loop/call AST -- see `frob.arch._normalized.NormalizedFunction`'s
    own documented gap: flat call/loop lists, no nesting). `[]` if the file
    cannot be re-parsed (moved/deleted since the original parse) or is not
    python."""
    result = _raw_tree(Path(path))
    if result.is_err:
        return []
    tree, _source, language = result.danger_ok
    if language != "python":
        return []
    violations: list[Violation] = []
    for call_node, loop in _iter_loop_call_sites(tree.root_node):
        effect = _direct_effect(call_node)
        effect_name = None
        if effect is not None:
            func = _child_by_field(call_node, "function")
            effect_name = _node_text(func) if func is not None else "?"
        else:
            short_name = _callee_short_name(call_node)
            if short_name is not None:
                hit = graph._effect_reachable_from_name(short_name)
                if hit is not None:
                    effect, effect_name = hit[0], hit[1]
        if effect is None:
            continue
        body = _child_by_field(loop, "body")
        body_text = _node_text(body) if body is not None else ""
        loop_vars = _loop_bound_names(loop)
        derived = _assigned_in_body(body_text) - loop_vars
        if not _is_loop_invariant(call_node, loop_vars, derived):
            continue
        func = _child_by_field(call_node, "function")
        call_text = _node_text(func) if func is not None else "?"
        line = call_node.start_point[0] + 1
        violations.append(
            Violation(
                rule="PERF008",
                severity=Severity.WARN,
                file=path,
                line=line,
                message=(
                    f"PERF008: {path}:{line} calls {call_text}(...) inside a "
                    f"loop with loop-invariant arguments; {call_text} "
                    f"transitively reaches {effect_name} (a {effect} "
                    f"effect) -- hoist the call out of the loop, memoize its "
                    f"result, or add a reasoned frob:waive PERF008 "
                    f"justifying why it must re-run every iteration (e.g. "
                    f"freshness under concurrency)"
                ),
            )
        )
    return violations


# frob:doc docs/modules/perf.md#loop-invariant-effectful-call-detector-perf008-t-0775
# frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_loop_invariant_spawn_call_two_hops_deep_is_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_loop_varying_argument_is_not_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_fs_walk_direct_call_in_loop_is_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_ticket_row_rev_parse_shape_fires_on_real_repo_history_fixture  # noqa: E501
# frob:ticket T-0775
def loop_invariant_effect_violations(
    files: Sequence[ParsedFile],
) -> tuple[Violation, ...]:
    """PERF008: a loop body's call site that is directly, or transitively
    (via `_EffectGraph`), a process-spawn/directory-walk effect, called
    with arguments that never reference the loop's own bound variable(s)
    or anything derived from them inside the loop body -- see this
    module's docstring for the full detector. WARN-tier (waivable with a
    reasoned `frob:waive PERF008 reason="..."`), never a silent error."""
    graph = _EffectGraph(files)
    violations: list[Violation] = []
    seen_paths: set[str] = set()
    for file in files:
        if file.language != "python" or file.path in seen_paths:
            continue
        seen_paths.add(file.path)
        violations.extend(_file_violations(file.path, graph))
    _log.info(
        "perf008: scanned %d python file(s), %d violation(s)",
        len(seen_paths),
        len(violations),
    )
    return tuple(violations)
