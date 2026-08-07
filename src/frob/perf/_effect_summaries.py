"""Shared interprocedural EFFECT-SUMMARY substrate (T-0922), promoting
`_loop_effects.py`'s original `_EffectGraph` (T-0775/T-0919) into its own
first-class module with a documented public surface: `EffectGraph`,
`Unknown`, and the needle tables every consuming PERF rule (PERF008,
PERF012, and any future rule) shares rather than re-implements.

Reuses the T-0659 binding-resolver convention (best-effort by-name
resolution, same-file-preferred, degrade rather than guess) and the
T-0745 summary-fixpoint precedent (bottom-up, cycle-safe, budget-bounded
propagation) instead of inventing a third engine, per the T-0922 user
directive.

WHAT THIS MODULE ANSWERS, for any function/method symbol `F` in a set of
parsed files:

1. `EffectGraph.reachable_effect(name)` -- the cheap yes/no/first-hit
   question PERF008 asks: does calling something named `name`
   transitively reach ANY directly-effectful call (a process spawn or a
   directory walk, today's two effect classes -- T-0775's original
   question).
2. `EffectGraph.summary(symref)` -- the FULL per-function EFFECT-SUMMARY:
   every `(kind, arg)` pair transitively reachable by calling `symref`,
   however many hops deep, propagated through sibling/cousin callees and
   diamonds alike (T-0919's addition, generalized here). `arg` is either
   a normalized argument-text string (a real, comparable argv-equivalence
   fact) or an `Unknown` instance -- see below.

EXPLICIT UNKNOWN, NOT SILENT EMPTY (T-0922 acceptance criterion (c)): a
call this substrate cannot bind (dynamic dispatch, an external/stdlib
boundary with no local definition, an ambiguous short name with no
single-candidate or same-file resolution, a call whose own argument list
cannot be recovered as text, or a summary walk that gives up because its
recursion-depth/node budget is exhausted) used to simply contribute
NOTHING to a summary -- indistinguishable, from the caller's side, from
"genuinely no effect here". That is a real information loss: a rule
consuming the summary cannot tell "this call path is provably effect-free"
from "this substrate gave up on part of this call path". Every one of
those gives-up cases now appends an explicit `(UNKNOWN_KIND, Unknown(...))`
member to the relevant occurrence set instead of silently omitting
anything. Each `Unknown` instance carries a human-readable `reason` for
diagnostics but compares equal to NOTHING but itself (default identity
equality, deliberately not overridden) -- two independently-unresolved
bindings must never accidentally look like "the same argument shape" to
a duplicate-detection consumer (PERF012), so `Unknown` can only ever
WIDEN what a rule can see (a caller can now ask "did any part of this
give up?"), never spuriously CREATE a false-positive duplicate pairing.
Each rule module documents its own Unknown policy where it consumes this
substrate (see `_loop_effects.py`'s and `_dup_spawn.py`'s module
docstrings)."""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Sequence
from pathlib import Path

from tree_sitter import Node

from frob.lang import child_by_field as _child_by_field
from frob.lang import node_text as _node_text
from frob.lang import raw_tree as _raw_tree
from frob.lang._models import ParsedFile, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "EffectGraph",
    "Unknown",
    "UNKNOWN_KIND",
    "EffectArg",
    "EffectOccurrence",
]

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

# Bounded BFS over `EffectGraph` -- same posture as `frob.graph.callgraph`'s
# `_DEFAULT_MAX_DEPTH`/`_DEFAULT_MAX_NODES` (T-0773's own incident was
# three calls deep; these leave headroom without letting a pathological
# project's call graph make the substrate itself the next `frob check`
# bottleneck).
_MAX_DEPTH = 8
_MAX_NODES = 200

#: The occurrence `kind` used for an explicit `Unknown` member (T-0922) --
#: distinct from the real effect kinds (`"spawn"`, `"fs-walk"`) so a
#: consumer can trivially filter "genuine effect occurrences" from "the
#: substrate gave up here" without inspecting `Unknown` itself.
# frob:doc docs/modules/perf.md#shared-interprocedural-effect-summary-substrate-effectgraph-t-0922  # noqa: E501
# frob:ticket T-0922
UNKNOWN_KIND = "unknown"


# frob:doc docs/modules/perf.md#shared-interprocedural-effect-summary-substrate-effectgraph-t-0922  # noqa: E501
# frob:tests tests/unit/perf/test_effect_summaries.py::TestUnknownIdentityEquality.test_two_unknowns_with_the_same_reason_text_are_not_equal  # noqa: E501
# frob:ticket T-0922
class Unknown:
    """T-0922 acceptance criterion (c): an explicit, non-empty marker for
    an effect binding this substrate could not resolve -- an ambiguous or
    external callee, an unrecoverable argument list, or a summary walk cut
    short by its recursion/budget guard. Carries a human-readable `reason`
    for diagnostics. Deliberately uses PLAIN IDENTITY equality (no
    `__eq__`/`__hash__` override): two different `Unknown` instances are
    never equal, so an `Unknown` can never be mistaken for a matching
    duplicate occurrence by a set-membership/grouping consumer (PERF012)
    -- it can only ever surface "something here is unresolved", never
    manufacture a spurious match."""

    __slots__ = ("reason",)

    def __init__(self, reason: str) -> None:
        """Store `reason` (why this binding could not be resolved) for
        diagnostics/messages; identity is this instance, not `reason`'s
        text -- see class docstring for why equality is not overridden."""
        self.reason = reason

    def __repr__(self) -> str:
        """`Unknown(<reason>)` -- diagnostic-only, never used for equality."""
        return f"Unknown({self.reason!r})"


#: An occurrence's argument component: a normalized argument-text string
#: (a real, comparable argv-equivalence fact) or an explicit `Unknown`.
EffectArg = str | Unknown
#: One effect occurrence: `(kind, arg)` -- `kind` is `"spawn"`/`"fs-walk"`
#: for a resolved effect, or `UNKNOWN_KIND` paired with an `Unknown` `arg`.
EffectOccurrence = tuple[str, EffectArg]

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

#: Node types marking a `*args`/`**kwargs` splat/spread argument (T-1018).
_SPLAT_KINDS = frozenset({"list_splat", "dictionary_splat"})

#: Decorator short names (T-1053) marking a memoizing wrapper -- same needle
#: set `frob.graph.callgraph._WRAPPER_MARKER_NAMES` already trusts for its
#: own "this call is really a reach-through to its wrapped target" reasoning
#: (T-0583), reused here for the opposite question: "is repeatedly CALLING
#: this symbol actually cheap because its own decorator already memoizes
#: it?" A symbol decorated `@lru_cache`/`@functools.lru_cache`/`@cache`
#: pays its real cost once per distinct argument tuple, not once per call
#: site or per loop iteration -- PERF008/PERF012 both need this to stop
#: mistaking a memoized repeat call for real repeated work (the "lru_cache
#: blindness" FP class).
_MEMOIZE_DECORATOR_NAMES = frozenset({"lru_cache", "cache"})


def _contains_splat(node: Node) -> bool:
    """T-1018 calibration: True if `node` (an `arguments`/`argument_list`
    call-site node) contains a `*args`/`**kwargs` splat ANYWHERE in its
    subtree -- not just as a direct top-level argument (`f(*args)`) but
    also nested inside a literal collection argument (`f(["git", *args])`,
    the real `_git(*args, cwd): subprocess.run(["git", *args], ...)` shape
    this fix targets: the splat sits inside the `list` literal, one level
    below `argument_list`, not as a direct child of it) -- the false-
    positive class behind most of PERF012's
    post-T-0922 over-fire (1777 -> low hundreds before this fix's other
    half, `_dup_spawn._split_clean_runs`, took the rest down further):
    a generic pass-through wrapper like `def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd)` has ONE fixed source text at
    its OWN definition site (`["git", *args]`) regardless of what any
    particular caller actually forwards through `*args` -- two entirely
    different callers (`_git("add", ...)`, `_git("commit", ...)`) both
    resolve, via `resolve_scoped`, to this SAME wrapper, whose textually
    IDENTICAL-at-the-defsite argument shape then looks like a duplicate
    spawn even though the real, runtime argv the two callers produce is
    completely different. A splat argument's real content is inherently
    caller-determined and cannot be compared by static text at the callee
    site the way a plain named-parameter forward (`ticket_id` used
    identically by two dedicated single-purpose helpers, T-0919's real
    motivating shape) safely can -- see this module's `summary` docstring
    and `_dup_spawn._entry_occurrences` for where this degrades to an
    explicit `Unknown` instead."""
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in _SPLAT_KINDS:
            return True
        stack.extend(current.children)
    return False


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


def _is_memoized_sig(sig_tokens: tuple[str, ...]) -> bool:
    """True if `sig_tokens` (a `RawSymbol.sig_tokens` stream, which carries
    a decorated python `def`'s decorator tokens ahead of its header -- see
    `frob.lang._walk_python._effective_node`, which returns the enclosing
    `decorated_definition` as `sig_node`) shows an `@lru_cache`/`@cache`/
    `@functools.lru_cache`/`@functools.cache` decorator immediately
    preceding the `def`. Requires the `@` marker directly before the
    name -- walking forward through any `module.` dotted-attribute prefix
    (`@functools.lru_cache(...)`'s real, common spelling, not just the
    bare `@lru_cache` a `from functools import lru_cache` gives) to the
    FINAL identifier before the next non-identifier/non-`.` token, then
    checking THAT against the marker set -- rather than just the bare
    word `cache` anywhere in the signature, e.g. a parameter literally
    named `cache`, same "actually used as a decorator, not a name
    coincidence" discipline this ticket's other two fixes apply."""
    n = len(sig_tokens)
    for i, tok in enumerate(sig_tokens[:-1]):
        if tok != "@":
            continue
        j = i + 1
        last = sig_tokens[j] if j < n else None
        while j + 1 < n and sig_tokens[j + 1] == "." and j + 2 < n:
            last = sig_tokens[j + 2]
            j += 2
        if last in _MEMOIZE_DECORATOR_NAMES:
            return True
    return False


def _infer_receiver_class(source: str | bytes, receiver: str) -> str | None:
    """T-1053 receiver-conflation fix: a cheap, textual, best-effort guess
    at the CLASS a simple local `receiver` identifier holds, from a nearby
    `receiver = ClassName(...)` constructor-call assignment anywhere in
    `source` -- same "textual scan, not real dataflow" posture as this
    package's other heuristics (e.g. `_loop_effects._assigned_in_body`).
    Returns `None` (no preference, caller falls back to its original
    unfiltered/best-effort resolution -- fail OPEN, never fail closed) when
    `receiver` is `self`/`cls` (handled separately by same-file/same-class
    bias elsewhere), is not a plain identifier, or no such assignment is
    found. Deliberately conservative: this can only ever NARROW an
    already-ambiguous by-name resolution toward the one receiver whose
    constructed type actually matches -- it never adds a candidate that
    `_by_name` did not already have."""
    if receiver in ("self", "cls") or not _IDENT_RE.fullmatch(receiver):
        return None
    text = (
        source.decode("utf-8", errors="replace")
        if isinstance(source, bytes)
        else source
    )
    match = re.search(
        rf"\b{re.escape(receiver)}\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", text
    )
    return match.group(1) if match else None


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


# frob:doc docs/modules/perf.md#shared-interprocedural-effect-summary-substrate-effectgraph-t-0922  # noqa: E501
# frob:tests tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation.test_fully_resolvable_call_path_has_no_unknown_member  # noqa: E501
# frob:ticket T-0922
class EffectGraph:
    """The SHARED interprocedural EFFECT-SUMMARY substrate (T-0922,
    promoted from `_loop_effects._EffectGraph`, T-0775/T-0919): a local,
    whole-project, best-effort NAME-based call graph over every FUNCTION/
    METHOD symbol in the files it is given. Every PERF rule that keys on
    a sub-call effect (PERF008, PERF012, and any future rule) consumes
    ONE instance of this class rather than hand-rolling its own call-graph
    walk -- see module docstring for the public surface
    (`reachable_effect`/`summary`) and the Unknown policy.

    Deliberately NOT `frob.graph.callgraph.build_call_graph` (which only
    ever resolves PRIVATE callees, by design, to stop its own BFS at the
    public-API boundary): the effects this substrate must trace routinely
    cross that exact boundary (a public `run_argv`-style helper called
    from a private caller in a different module), so this graph treats
    every candidate, public or private, as a real edge -- a second,
    narrower-purpose graph, matching `frob.perf._recursion`'s own
    precedent for building one rather than widening `callgraph`'s
    contract for a use case it was not designed for."""

    def __init__(self, files: Sequence[ParsedFile]) -> None:
        """Index every function/method symbol's own direct effect (from its
        `body_tokens`, a cheap pre-check before the expensive AST walk),
        its source file path (for `_direct_occurrences`' lazy AST
        re-parse), and its called-name set, keyed by short name for
        best-effort resolution."""
        self._by_name: dict[str, list[str]] = {}
        self._direct: dict[str, str] = {}
        self._path_of: dict[str, str] = {}
        self._called: dict[str, frozenset[str]] = {}
        self._memo: dict[str, str | None] = {}
        #: symref -> enclosing class name (T-1053 receiver-conflation
        #: fix), `None` for a plain top-level function -- `qualname`'s
        #: dotted prefix, matching how a METHOD's qualname is built
        #: everywhere else in this codebase (`Class.method`).
        self._owner_of: dict[str, str | None] = {}
        #: symrefs decorated `@lru_cache`/`@cache` (T-1053 lru_cache-
        #: blindness fix) -- see `_is_memoized_sig`.
        self._memoized: set[str] = set()
        #: file path -> {short_name -> (kind, arg_text_or_None, line,
        #: callee_name), ...} -- one AST re-parse per FILE
        #: (`_index_file_occurrences`), not per symbol.
        self._occurrence_cache: dict[
            str, dict[str, tuple[tuple[str, str | None, int, str], ...]]
        ] = {}
        self._summary_memo: dict[str, frozenset[EffectOccurrence]] = {}
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
                self._owner_of[symref] = (
                    sym.qualname.rsplit(".", 1)[0] if "." in sym.qualname else None
                )
                if _is_memoized_sig(sym.sig_tokens):
                    self._memoized.add(symref)
                effect = _direct_effect_from_tokens(sym.body_tokens)
                if effect is not None:
                    self._direct[symref] = effect
                self._called[symref] = _called_names_from_tokens(sym.body_tokens)

    # frob:doc docs/modules/perf.md#loop-invariant-effectful-call-detector-perf008-t-0775  # noqa: E501
    # frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_loop_invariant_spawn_call_three_hops_deep_is_flagged  # noqa: E501
    # frob:ticket T-0922
    def reachable_effect(
        self, callee_name: str, receiver_class: str | None = None
    ) -> tuple[str, str] | None:
        """`(effect_kind, symref)` for the first directly-effectful function
        transitively reachable by calling ANY symbol named `callee_name`
        (best-effort, ambiguous names all tried), or `None` if nothing
        reachable within the bounded BFS is directly effectful. Unknown
        policy: an unresolvable name simply yields `None` here (this is
        the cheap yes/no question PERF008 asks; see that module's own
        Unknown-policy note -- the richer `summary()` is where `Unknown`
        becomes an explicit, visible member).

        `receiver_class` (T-1053 receiver-conflation fix): when given (a
        dotted call's inferred receiver type, `_infer_receiver_class`),
        candidates whose OWN enclosing class matches it are tried FIRST and
        EXCLUSIVELY if any exist -- a `b.run()` call whose receiver is
        known to be a `B` no longer risks binding to an unrelated `A.run`
        that merely shares the bare name `run`. Falls back to the
        unfiltered candidate set when no candidate matches (fail OPEN,
        never fail closed -- an unmatched hint never suppresses a real
        finding, it only ever narrows an otherwise-ambiguous one)."""
        candidates = self._by_name.get(callee_name, ())
        if receiver_class is not None:
            scoped = [c for c in candidates if self._owner_of.get(c) == receiver_class]
            if scoped:
                candidates = scoped
        for symref in candidates:
            hit = self._reachable(symref)
            if hit is not None:
                return hit
        return None

    # frob:doc docs/modules/perf.md#three-false-positive-classes-closed-t-1053
    # frob:tests tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection.test_lru_cache_decorated_symbol_is_memoized  # noqa: E501
    # frob:ticket T-1053
    def is_memoized(self, symref: str) -> bool:
        """True if `symref` (T-1053) is itself decorated `@lru_cache`/
        `@cache` -- a repeated call to it pays its real cost at most once
        per distinct argument tuple, not once per call site."""
        return symref in self._memoized

    # frob:doc docs/modules/perf.md#three-false-positive-classes-closed-t-1053
    # frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_loop_invariant_call_to_lru_cached_helper_is_not_flagged  # noqa: E501
    # frob:ticket T-1053
    def callee_is_memoized(self, callee_name: str) -> bool:
        """True (T-1053) if EVERY symbol named `callee_name` this graph
        knows about is memoized -- the conservative "safe to suppress"
        check `_loop_effects` uses before dropping a PERF008 finding: an
        ambiguous name where only SOME candidates are memoized is left
        alone (fail open) rather than risk suppressing a real repeated-work
        finding for the unmemoized candidate."""
        candidates = self._by_name.get(callee_name, ())
        return bool(candidates) and all(c in self._memoized for c in candidates)

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

    # frob:doc docs/modules/perf.md#duplicate-identical-subprocess-spawn-detector-perf012-t-0919  # noqa: E501
    # frob:tests tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation.test_ambiguous_cross_file_callee_yields_an_explicit_unknown_member  # noqa: E501
    # frob:ticket T-0922
    def resolve_scoped(
        self,
        short_name: str,
        from_path: str | None,
        receiver_class: str | None = None,
    ) -> list[str]:
        """By-name resolution SCOPED to same-file candidates first -- the
        safe default for MULTISET/duplicate-detection propagation
        (`summary`), unlike the unfiltered by-name union
        `reachable_effect` uses for its cheap yes/no BFS (safe there since
        it only ever returns the FIRST hit, never a union of many).

        A common short name (`run`, `check`, `fn`...) can resolve to
        DOZENS of unrelated top-level symbols across a whole project;
        unioning every one of their summaries cross-contaminates
        completely unrelated call paths. Restricting to same-file
        candidates matches the common shape (a helper and its caller are
        overwhelmingly typically defined in the same module) and is
        symmetric with `_index_file_occurrences`'s own by-short-name-per-
        file indexing. Falls back to the full cross-file candidate set
        ONLY when it is unambiguous (a single candidate total) -- an
        unambiguous name is safe to follow cross-file regardless of
        scope. `[]` (genuinely ambiguous, no same-file candidate) is the
        caller's cue to record an explicit `Unknown` rather than silently
        contributing nothing (T-0922) -- see `summary`/`_dup_spawn.
        _entry_occurrences`.

        `receiver_class` (T-1053 receiver-conflation fix): same posture as
        `reachable_effect`'s own -- when given and at least one candidate's
        owner class matches, narrow to just those FIRST, before the same-
        file/unambiguous fallback below runs; an unmatched hint changes
        nothing (fail open)."""
        candidates = self._by_name.get(short_name, ())
        if receiver_class is not None:
            scoped = [c for c in candidates if self._owner_of.get(c) == receiver_class]
            if scoped:
                candidates = scoped
        if from_path is not None:
            same_file = [c for c in candidates if self._path_of.get(c) == from_path]
            if same_file:
                return same_file
        if len(candidates) == 1:
            return list(candidates)
        return []

    def _direct_occurrences(
        self, symref: str
    ) -> tuple[tuple[str, str | None, int, str], ...]:
        """Every direct (non-transitive) process-spawn/directory-walk call
        inside `symref`'s OWN body, as `(kind, normalized_arg_text_or_
        None, line, callee_name)` -- `None` arg text means the call's own
        argument list could not be resolved; `summary()` turns that into
        an explicit `Unknown` member (T-0922) rather than dropping it.
        `callee_name` (T-0922) is the call's own bare/attribute name --
        used by `_summary` to recognize that a `_called`-edge sharing this
        SAME name is this SAME already-counted direct occurrence, not a
        second, separately-unresolvable callee (see `_summary`'s own
        comment). Lazily re-parses `symref`'s source file via AST (unlike
        this class's cheap token-level `_direct`/`_called` indexes, which
        cannot carry argument text) and caches per FILE path, not per
        symbol, so a file with several effectful symbols is re-parsed
        once."""
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
    def summary(self, symref: str) -> frozenset[EffectOccurrence]:
        """T-0922 (promoted from T-0919's `_EffectGraph.summary`): the full
        interprocedural EFFECT-SUMMARY for `symref` -- every `(kind, arg)`
        pair reachable by calling `symref` directly or transitively,
        bottom-up over `_called`. `arg` is a normalized argument-text
        string for a resolved binding, or an explicit `Unknown` (T-0922
        criterion (c)) for: an unresolvable call argument list, an
        ambiguous/unresolvable callee name (`resolve_scoped` returning
        `[]`), or a walk cut short by the recursion-depth/node budget --
        never silently dropped. Memoized per symref; a symref already on
        the CURRENT recursion stack (a call cycle) contributes nothing
        further rather than recursing forever. `_budget` is reset PER
        external call so an earlier large query can never starve a
        later, unrelated one."""
        self._budget = _MAX_NODES
        return self._summary(symref, frozenset())

    # frob:invariant terminates reason="self._budget is decremented before every \
    # recursive descent (via _called_callee_effects) and checked non-positive at \
    # entry, so the mutual recursion with _called_callee_effects can only run a \
    # bounded number of steps regardless of call-graph shape; the stack frozenset \
    # additionally short-circuits any symref already on the current path, so a call \
    # cycle in the graph itself cannot recurse forever either" measure="self._budget, \
    # a non-negative int strictly decreasing by 1 per _summary call, floored by the \
    # eager return at budget<=0; bounded above by _MAX_NODES"
    def _summary(
        self, symref: str, stack: frozenset[str]
    ) -> frozenset[EffectOccurrence]:
        if symref in self._summary_memo:
            return self._summary_memo[symref]
        if symref in stack:
            return frozenset()
        if self._budget <= 0:
            return frozenset(
                {(UNKNOWN_KIND, Unknown(f"summary budget exhausted at {symref!r}"))}
            )
        self._budget -= 1
        next_stack = stack | {symref}
        acc, direct_names = self._direct_occurrence_effects(symref)
        acc |= self._called_callee_effects(symref, direct_names, next_stack)
        result = frozenset(acc)
        # Only cache once fully resolved outside any in-progress cycle --
        # caching a partial (cycle-truncated) result under `stack` non-
        # empty would wrongly freeze a short-circuited answer as final.
        if not stack:
            self._summary_memo[symref] = result
        return result

    # frob:ticket T-0976
    def _direct_occurrence_effects(
        self, symref: str
    ) -> tuple[set[EffectOccurrence], set[str]]:
        """`symref`'s own DIRECT effect occurrences (`_direct_occurrences`)
        as an accumulator set, plus the set of callee names already fully
        accounted for that way (T-0922) -- `_summary`'s direct-occurrence
        half, split from its callee-resolution half. See `_summary`'s own
        docstring comment for why `direct_names` must be threaded through
        to the callee-resolution half."""
        acc: set[EffectOccurrence] = set()
        direct_names: set[str] = set()
        for kind, arg, _line, callee_name in self._direct_occurrences(symref):
            direct_names.add(callee_name)
            if arg is not None:
                acc.add((kind, arg))
            else:
                acc.add(
                    (
                        UNKNOWN_KIND,
                        Unknown(
                            f"unresolvable argument text for a {kind} call "
                            f"in {symref!r}"
                        ),
                    )
                )
        return acc, direct_names

    # frob:ticket T-0976
    # frob:invariant terminates reason="every call into _summary from here shares the \
    # same self._budget counter _summary itself decrements before recursing again, and \
    # the same stack frozenset guard against call-graph cycles -- see _summary's own \
    # frob:invariant for the shared measure this mutual recursion relies on" \
    # measure="self._budget, a non-negative int strictly decreasing by 1 per mutual \
    # _summary call, floored by _summary's own eager return at budget<=0"
    def _called_callee_effects(
        self, symref: str, direct_names: set[str], next_stack: frozenset[str]
    ) -> set[EffectOccurrence]:
        """`symref`'s transitive callee effects: resolve every name in
        `self._called[symref]` (`resolve_scoped`) and recurse `_summary`
        into each candidate, or emit one `Unknown` for a name that
        resolves to nothing AND was not already accounted for as a direct
        occurrence (`direct_names`) -- `_summary`'s callee-resolution
        half, split from its direct-occurrence half."""
        acc: set[EffectOccurrence] = set()
        current_path = self._path_of.get(symref)
        for name in self._called.get(symref, ()):
            candidates = self.resolve_scoped(name, current_path)
            if not candidates:
                if name not in direct_names:
                    acc.add(
                        (
                            UNKNOWN_KIND,
                            Unknown(
                                f"unresolvable/ambiguous callee {name!r} "
                                f"called from {symref!r}"
                            ),
                        )
                    )
                continue
            for callee in candidates:
                acc |= self._summary(callee, next_stack)
        return acc


_WS_RE = re.compile(r"\s+")


def _normalize_arg_text(text: str) -> str:
    """Collapse all whitespace runs to a single space and strip the ends --
    the comparison key for "identical argument shape": two spawn calls
    whose argument source text differs only in incidental formatting
    (line-wrapping, trailing comma) still count as the SAME duplicated
    call, matching what a copy-pasted or independently re-typed identical
    call looks like."""
    return _WS_RE.sub(" ", text).strip()


def _iter_calls(root: Node) -> list[Node]:
    """Every `call` node anywhere under `root`, in document order (used by
    `_index_file_occurrences` to find every direct effect call inside one
    `def`'s body, INCLUDING calls nested inside a closure defined in that
    body -- an accepted over-attribution cost, same "lean toward firing"
    posture the rest of this substrate already takes, rather than the
    false-negative risk of excluding nested defs)."""
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
) -> dict[str, tuple[tuple[str, str | None, int, str], ...]]:
    """Re-parse `path` via AST and return, for every `def` (function/
    method) in it, the tuple of `(kind, normalized_arg_text_or_None, line,
    callee_name)` for each DIRECT process-spawn/directory-walk call inside
    that def's own body -- keyed by the def's own short name (matching
    `EffectGraph`'s by-short-name resolution elsewhere). `arg_text` is
    `None` (T-0922: `summary()` turns this into an explicit `Unknown`
    rather than dropping it) for a call node with no resolvable
    `arguments` field, OR (T-1018) one whose argument list contains a
    `*args`/`**kwargs` splat -- see `_contains_splat`'s own docstring for
    why a splat's real content can never be compared by static text at the
    callee's definition site; the overwhelmingly common case always
    recovers real, comparable source text. `callee_name` (T-0922) is the
    call's own bare/attribute name, carried through so `EffectGraph.
    _summary` can recognize a `_called`-edge of the SAME name as this SAME
    already-counted occurrence rather than a second, unresolvable callee.
    `{}` if the file cannot be re-parsed (moved/deleted since the original
    parse) or is not python."""
    result = _raw_tree(Path(path))
    if result.is_err:
        return {}
    tree, _source, language = result.danger_ok
    if language != "python":
        return {}
    by_short: dict[str, list[tuple[str, str | None, int, str]]] = {}
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "function_definition":
            _record_def_effect_occurrences(node, by_short)
        stack.extend(node.children)
    return {short: tuple(occ) for short, occ in by_short.items()}


def _call_effect_occurrence(call: Node) -> tuple[str, str | None, int, str] | None:
    """One `(kind, arg_text_or_None, line, callee_name)` occurrence for a
    single `call` node, or `None` if it is not a direct process-spawn/
    directory-walk call (extracted from `_index_file_occurrences` to cut
    nesting, T-0394)."""
    effect = _direct_effect(call)
    if effect is None:
        return None
    args = _child_by_field(call, "arguments")
    arg_text = (
        _normalize_arg_text(_node_text(args))
        if args is not None and not _contains_splat(args)
        else None
    )
    line = call.start_point[0] + 1
    callee_name = _callee_short_name(call) or "?"
    return (effect, arg_text, line, callee_name)


def _record_def_effect_occurrences(
    def_node: Node, by_short: dict[str, list[tuple[str, str | None, int, str]]]
) -> None:
    """Record every direct-effect call occurrence inside one `def`'s body
    into `by_short`, keyed by its short name (extracted from
    `_index_file_occurrences` to cut nesting, T-0394)."""
    name_node = _child_by_field(def_node, "name")
    short = _node_text(name_node) if name_node is not None else None
    body = _child_by_field(def_node, "body")
    if short is None or body is None:
        return
    occurrences = [
        occ
        for call in _iter_calls(body)
        if (occ := _call_effect_occurrence(call)) is not None
    ]
    if occurrences:
        by_short.setdefault(short, []).extend(occurrences)


def _direct_effect_from_tokens(tokens: tuple[str, ...]) -> str | None:
    """Cheap token-level pre-check mirroring `_direct_effect`'s AST version,
    used to seed `EffectGraph` without re-parsing every file's tree --
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
    name(`) referenced in `tokens` -- `EffectGraph`'s call-edge extractor,
    deliberately including BOTH public and private names (unlike `frob.
    graph.callgraph`'s private-only resolution -- see module docstring)."""
    names: set[str] = set()
    n = len(tokens)
    for i in range(n - 1):
        if tokens[i + 1] != "(" or not tokens[i].isidentifier():
            continue
        names.add(tokens[i])
    return frozenset(names)
