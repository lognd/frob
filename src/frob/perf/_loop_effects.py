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
    FUNCTION/METHOD symbol in the files this run was given -- the SHARED
    interprocedural EFFECT-SUMMARY substrate PERF008
    (`loop_invariant_effect_violations`) and PERF012
    (`frob.perf._dup_spawn.duplicate_spawn_violations`, T-0919) both
    consume, rather than each rule hand-rolling its own one-off call-graph
    walk (see module docstring for why this is a second graph, not
    `frob.graph.callgraph.build_call_graph`).

    Two questions, both memoized and reused across every caller in one
    run:

    1. `_effect_reachable_from_name`/`_reachable` (PERF008's original
       question, T-0775): does calling `qualname` transitively reach ANY
       directly-effectful call, and which one -- a cheap yes/no/first-hit
       BFS over `body_tokens`-derived call edges, never re-parsing AST.
    2. `summary`/`_direct_occurrences_for` (T-0919's addition): the FULL
       per-function EFFECT-SUMMARY multiset -- every `(kind, normalized_
       arg_text)` pair transitively reachable from `symref`, computed
       bottom-up over the SAME call edges with a recursion-depth guard
       (cycle-safe: a symref already on the current recursion stack
       contributes nothing further, breaking the cycle) and the same
       `_MAX_NODES` global visit budget PERF008's BFS already enforces.
       This is what lets PERF012 answer "does this call path spawn the
       SAME subprocess twice", however many hops deep, or however split
       across sibling callees, the duplicate is -- `Unknown` (an
       unresolvable call, or a call whose own arguments cannot be
       recovered) fails OPEN: it contributes no occurrence rather than a
       guessed one, so an unresolvable edge can only cause a missed
       finding, never a false one."""

    def __init__(self, files: Sequence[ParsedFile]) -> None:
        """Index every function/method symbol's own direct effect (from its
        `body_tokens`, a cheap pre-check before the expensive AST walk),
        its source file path (for `_direct_occurrences_for`'s lazy AST
        re-parse), and its called-name set, keyed by short name for
        best-effort resolution."""
        self._by_name: dict[str, list[str]] = {}
        self._direct: dict[str, str] = {}
        self._path_of: dict[str, str] = {}
        self._called: dict[str, frozenset[str]] = {}
        self._memo: dict[str, str | None] = {}
        #: file path -> {short_name -> (kind, arg_text_or_None, line), ...}
        #: -- one AST re-parse per FILE (`_index_file_occurrences`), not
        #: per symbol (T-0919).
        self._occurrence_cache: dict[
            str, dict[str, tuple[tuple[str, str | None, int], ...]]
        ] = {}
        self._summary_memo: dict[str, frozenset[tuple[str, str]]] = {}
        self._budget = _MAX_NODES
        for file in files:
            for sym in file.symbols:
                if sym.kind not in _FUNCTION_KINDS:
                    continue
                symref = f"{file.path}::{sym.qualname}"
                self._by_name.setdefault(sym.qualname.rsplit(".", 1)[-1], []).append(
                    symref
                )
                self._path_of[symref] = file.path
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

    def _resolve_scoped(self, short_name: str, from_path: str | None) -> list[str]:
        """T-0919: by-name resolution SCOPED to same-file candidates first
        -- the safe default for MULTISET/duplicate-detection propagation
        (`summary`, `_entry_occurrences`), unlike the unfiltered by-name
        union `_effect_reachable_from_name` uses for its cheap yes/no BFS
        (safe there since it only ever returns the FIRST hit, never a
        union of many).

        A common short name (`run`, `check`, `fn`...) can resolve to
        DOZENS of unrelated top-level symbols across a whole project;
        unioning every one of their summaries (as an early version of this
        module did) cross-contaminates completely unrelated call paths --
        any two call sites anywhere in the project that both happen to
        call something named `run` would spuriously share the SAME
        occurrence multiset and false-positive PERF012 as "duplicated".
        Restricting to same-file candidates matches the actual T-0919
        shape (a helper and its caller are overwhelmingly typically
        defined in the same module) and is symmetric with `_index_file_
        occurrences`' own by-short-name-per-file indexing. Falls back to
        the full cross-file candidate set ONLY when it is unambiguous (a
        single candidate total) -- an unambiguous name is safe to follow
        cross-file regardless of scope; a genuinely ambiguous cross-file
        name resolves to `[]` (fails OPEN: this call edge contributes
        nothing, a missed finding is accepted, a false one is not)."""
        candidates = self._by_name.get(short_name, ())
        if from_path is not None:
            same_file = [c for c in candidates if self._path_of.get(c) == from_path]
            if same_file:
                return same_file
        if len(candidates) == 1:
            return list(candidates)
        return []

    def _direct_occurrences(
        self, symref: str
    ) -> tuple[tuple[str, str | None, int], ...]:
        """T-0919: every direct (non-transitive) process-spawn/directory-
        walk call inside `symref`'s OWN body, as `(kind, normalized_arg_
        text_or_None, line)` -- `None` arg text means the call's own
        argument list could not be resolved (fails OPEN: excluded from
        `summary`'s duplicate-detection multiset, never guessed). Lazily
        re-parses `symref`'s source file via AST (unlike this class's
        cheap token-level `_direct`/`_called` indexes, which cannot carry
        argument text) and caches per FILE path, not per symbol, so a
        file with several effectful symbols is re-parsed once."""
        path = self._path_of.get(symref)
        if path is None:
            return ()
        by_short = self._occurrence_cache.get(path)
        if by_short is None:
            by_short = _index_file_occurrences(path)
            self._occurrence_cache[path] = by_short
        short = symref.split("::", 1)[1].rsplit(".", 1)[-1]
        return by_short.get(short, ())

    # frob:doc docs/modules/perf.md#duplicate-identical-subprocess-spawn-detector-perf012-t-0919  # noqa: E501
    def summary(self, symref: str) -> frozenset[tuple[str, str]]:
        """T-0919: the full interprocedural EFFECT-SUMMARY for `symref` --
        every `(kind, normalized_arg_text)` pair reachable by calling
        `symref` directly or transitively, bottom-up over `_called`.
        Memoized per symref; a symref already on the CURRENT recursion
        stack (a call cycle) contributes nothing further rather than
        recursing forever -- the same "bounded, best-effort, lean toward
        firing but never hang" posture `_reachable`'s BFS already
        establishes for PERF008, extended here to carry argument text
        instead of just a yes/no. `_budget` is reset PER external call
        (matching `_reachable`'s own per-call `seen` set semantics) so an
        earlier large query can never starve a later, unrelated one."""
        self._budget = _MAX_NODES
        return self._summary(symref, frozenset())

    def _summary(
        self, symref: str, stack: frozenset[str]
    ) -> frozenset[tuple[str, str]]:
        if symref in self._summary_memo:
            return self._summary_memo[symref]
        if symref in stack or self._budget <= 0:
            return frozenset()
        self._budget -= 1
        next_stack = stack | {symref}
        acc: set[tuple[str, str]] = {
            (kind, arg)
            for kind, arg, _line in self._direct_occurrences(symref)
            if arg is not None
        }
        current_path = self._path_of.get(symref)
        for name in self._called.get(symref, ()):
            for callee in self._resolve_scoped(name, current_path):
                acc |= self._summary(callee, next_stack)
        result = frozenset(acc)
        # Only cache once fully resolved outside any in-progress cycle --
        # caching a partial (cycle-truncated) result under `stack` non-
        # empty would wrongly freeze a short-circuited answer as final.
        if not stack:
            self._summary_memo[symref] = result
        return result


_WS_RE = re.compile(r"\s+")


def _normalize_arg_text(text: str) -> str:
    """Collapse all whitespace runs to a single space and strip the ends --
    T-0919's comparison key for "identical argument shape": two spawn
    calls whose argument source text differs only in incidental
    formatting (line-wrapping, trailing comma) still count as the SAME
    duplicated call, matching what a copy-pasted or independently
    re-typed identical call looks like."""
    return _WS_RE.sub(" ", text).strip()


def _iter_calls(root: Node) -> list[Node]:
    """Every `call` node anywhere under `root`, in document order (T-0919:
    used by `_index_file_occurrences` to find every direct effect call
    inside one `def`'s body, INCLUDING calls nested inside a closure
    defined in that body -- an accepted over-attribution cost, same
    "lean toward firing" posture the rest of this module already takes,
    rather than the false-negative risk of excluding nested defs)."""
    hits: list[Node] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "call":
            hits.append(node)
        stack.extend(node.children)
    return hits


def _index_file_occurrences(
    path: str,
) -> dict[str, tuple[tuple[str, str | None, int], ...]]:
    """T-0919: re-parse `path` via AST and return, for every `def`
    (function/method) in it, the tuple of `(kind, normalized_arg_text_or_
    None, line)` for each DIRECT process-spawn/directory-walk call inside
    that def's own body -- keyed by the def's own short name (matching
    `_EffectGraph`'s by-short-name resolution elsewhere). `arg_text` is
    `None` (fails OPEN, excluded from `_EffectGraph.summary`'s duplicate
    multiset) only for the pathological case of a call node with no
    resolvable `arguments` field; the overwhelmingly common case always
    recovers real source text. `{}` if the file cannot be re-parsed (moved/
    deleted since the original parse) or is not python."""
    result = _raw_tree(Path(path))
    if result.is_err:
        return {}
    tree, _source, language = result.danger_ok
    if language != "python":
        return {}
    by_short: dict[str, list[tuple[str, str | None, int]]] = {}
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "function_definition":
            name_node = _child_by_field(node, "name")
            short = _node_text(name_node) if name_node is not None else None
            body = _child_by_field(node, "body")
            if short is not None and body is not None:
                occurrences: list[tuple[str, str | None, int]] = []
                for call in _iter_calls(body):
                    effect = _direct_effect(call)
                    if effect is None:
                        continue
                    args = _child_by_field(call, "arguments")
                    arg_text = (
                        _normalize_arg_text(_node_text(args))
                        if args is not None
                        else None
                    )
                    line = call.start_point[0] + 1
                    occurrences.append((effect, arg_text, line))
                if occurrences:
                    by_short.setdefault(short, []).extend(occurrences)
        stack.extend(node.children)
    return {short: tuple(occ) for short, occ in by_short.items()}


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
    graph: _EffectGraph | None = None,
) -> tuple[Violation, ...]:
    """PERF008: a loop body's call site that is directly, or transitively
    (via `_EffectGraph`), a process-spawn/directory-walk effect, called
    with arguments that never reference the loop's own bound variable(s)
    or anything derived from them inside the loop body -- see this
    module's docstring for the full detector. WARN-tier (waivable with a
    reasoned `frob:waive PERF008 reason="..."`), never a silent error.

    `graph`: an optional pre-built `_EffectGraph` to SHARE with a sibling
    PERF012 run in the same `perf_rules` pass (T-0919: avoids re-indexing
    the same project's call graph twice in one `frob check`); builds its
    own if not given."""
    if graph is None:
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
