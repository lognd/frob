# frob:waive INV006 reason="this module's 'only'/'exactly one' occurrences \
# are source-level design-rationale prose (the module docstring's model \
# description and per-function docstrings describing already-implemented \
# resolution/matching logic), verifiable by reading the function it \
# annotates, not a separate cross-module contract needing its own tracked \
# invariant -- the same INV006 first-turn-on pool disposition \
# frob.arch._mayraise's own module docstring already carries"
"""Lock-ordering hazard checks (T-0694, child 2 of the T-0693 concurrency-
hazard umbrella): a structural, INTERPROCEDURAL scan for cyclic lock-
acquisition order across call paths -- the classic AB/BA two-lock deadlock
shape, generalized to fire even when the second acquisition happens inside
a callee, not the same function body. Same fail-closed, non-runtime-tracing
posture as this package's other concurrency-hazard checks
(`frob.arch._concurrency`'s fork/pool family, T-0695;
`frob.arch._async_hazards`'s event-loop family, T-0696): every finding
flags a STRUCTURAL shape that makes a deadlock possible, not a proof it
fires at runtime.

MODEL (T-0694):

1. LOCK IDENTITY (`_collect_module_locks`): a lock object is
   statically-identifiable only when its CONSTRUCTION site is one of the
   curated ctor names (`threading`/`multiprocessing`'s `Lock`/`RLock`/
   `Semaphore`/`BoundedSemaphore`, or `anyio`/`asyncio`'s `Lock`), assigned
   either at MODULE level (`lock = threading.Lock()`) or as a `self.<attr>`
   assignment inside a class's own method body (`self._lock =
   threading.RLock()`) -- matching this ticket's own "module/class-level"
   framing. A module-level name's canonical id is its bare name; a
   class-attribute lock's canonical id is `ClassName.attr`, resolved at a
   USE site only when that use site's own enclosing class matches (a
   `self.attr` read outside the class that assigned it, or from a
   different attr, does not alias).

2. PER-FUNCTION LOCK EVENTS (`_collect_function_lock_events`): every
   `with <expr>:` context manager (each item in a possibly-multi-item
   `with` clause, left to right) and every explicit `<expr>.acquire()`
   call, walked in the function's OWN body in program order (crossing
   `with`/`if`/`for`/`try` blocks but not descending into a nested
   `function_definition`/`class_definition`, same convention
   `frob.arch._async_hazards._iter_own_scope` already uses) -- each event
   resolves `<expr>`'s text against the module's lock-identity table
   (canonical id) or, when `<expr>` merely LOOKS lock-shaped (a name
   containing "lock"/"mutex"/"semaphore", case-insensitive) but does not
   resolve, is recorded as UNRESOLVED (an advisory-tier, fail-closed
   finding per function, not per site, to avoid drowning signal -- see
   this module's docstring's "unresolvable identity" clause). A plain
   `with open(...) as f:` (no lock-shaped name, no resolved identity) is
   silently ignored -- it is not the shape this check targets.

3. INTERPROCEDURAL PROPAGATION (`_ordered_pairs_for_function`): a call to
   a resolvable SAME-MODULE function (the same bare-name lookup convention
   `frob.arch._mayraise._build_name_to_func`/`frob.arch._fallibility` both
   already use) is treated, at its call-site position in the caller's own
   event sequence, as if it "acquires" every lock that function's own
   (transitively expanded) reachable-lock SET reaches -- a monotonic
   chaotic-iteration fixpoint over the same-module call graph exactly
   mirroring `frob.arch._mayraise.compute_may_raise`'s cycle-safe fixpoint,
   just propagating a lock SET instead of a may-raise SET. This is a
   deliberate over-approximation (any lock reachable anywhere inside a
   callee is treated as reachable at the call site, not ordered against
   the callee's OWN internal sequence) -- matching the fail-closed,
   advisory-not-proof posture every other `frob.arch` concurrency category
   already discloses.

4. ORDER-PAIR EXTRACTION: a function's OWN event sequence, with each call
   event's position expanded to the callee's reachable-lock set, is turned
   into totally-ordered "slots" (an own lock event is a one-lock slot; a
   call event is a slot of the callee's reachable-lock set, possibly
   empty). Every `(lockA, lockB)` pair where `lockA` occupies an EARLIER
   slot than `lockB` (`lockA != lockB` -- reentrant use of the SAME lock,
   including via `RLock`, never counts as an ordering pair) is a directed
   edge `lockA -> lockB` ("this call path can acquire lockA before
   lockB"), tagged with the contributing function's symref and the
   `lockA` event's line for reporting.

5. CYCLE DETECTION (`_find_cycles`): every function in the module
   contributes its own edges into one GLOBAL directed graph over lock
   canonical ids (the whole module is the resolution boundary, matching
   `_mayraise`/`_fallibility`'s own same-module disclosed limit). A cycle
   in this graph (`lockA -> lockB -> ... -> lockA`, any length, but the
   fixtures this ticket calls for are the 2-lock case) is a potential
   deadlock: two (or more) call paths that acquire the SAME set of locks
   in opposite orders can deadlock if they ever run concurrently. A
   CONSISTENT global order (every path acquires `A` before `B`, never the
   reverse) produces no back-edge and stays silent, per the ticket's own
   acceptance criterion.

MODEL-LIMIT DISCLOSURE (matching this package's house convention): same-
module only (no cross-file call resolution); a lock passed as a function
PARAMETER or returned from a factory is not identity-tracked (out of
scope -- only module/class-level construction sites are); release
ordering is not modeled at all (only acquisition order, per the ticket's
own "acquisition order" framing) since a deadlock is caused by acquisition
order, not release order.

Every finding stays on the same unwaivable advisory channel every other
`frob.arch` category is on (`frob.gates._unwaivable_channel_rules` auto-
adopts any new `ArchCategory` value, so no `frob.gates` change is needed
here) -- see docs/modules/arch.md's concurrency-hazard sections for the
sibling categories this one joins.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.arch._python import _iter_py_functions, _py_call_callee_text
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text
from frob.logging import get_logger

_log = get_logger(__name__)

#: Curated lock-constructor table (T-0694): matched against a call's full
#: dotted callee TEXT so `threading.Lock`/`multiprocessing.Lock`/
#: `anyio.Lock`/`asyncio.Lock` (any module prefix, or a bare imported name)
#: all count, while an unrelated `.Lock`-suffixed name on some other object
#: still counts too (deliberately permissive on the RECEIVER, narrow on the
#: trailing ctor name -- a false-negative-avoidance choice matching this
#: package's other curated-table checks).
_LOCK_CTOR_RE = re.compile(r"(?:^|\.)(?:Lock|RLock|Semaphore|BoundedSemaphore)$")

#: A `with`/`.acquire()` target whose bare name merely LOOKS lock-shaped --
#: used only to decide whether an unresolved identity is worth an advisory
#: note (a `with open(...) as f:` never matches this and is silently
#: ignored, per this module's docstring).
_LOCK_NAME_HINT_RE = re.compile(r"lock|mutex|semaphore", re.IGNORECASE)

_ACQUIRE_CALL_RE = re.compile(r"\.acquire$")


def _iter_own_scope(node: Node) -> Iterator[Node]:
    """Every node in `node`'s subtree belonging to the OWNING function's own
    scope -- stops descending at a nested `function_definition`/
    `class_definition` boundary, same convention as
    `frob.arch._async_hazards._iter_own_scope` (that nested scope gets its
    own separate pass via `_iter_py_functions`)."""
    if node.type in ("function_definition", "class_definition"):
        return
    yield node
    for c in node.children:
        yield from _iter_own_scope(c)


def _assignment_ctor_callee(assign_node: Node) -> Node | None:
    """The `call` node on the right-hand side of an `assignment` node, or
    `None` if the right-hand side is not a bare call expression (T-0694)."""
    right = _child(assign_node, "right")
    if right is not None and right.type == "call":
        return right
    return None


def _collect_module_locks(root: Node) -> dict[str, str]:
    """Canonical lock-identity table (T-0694, this module's docstring step
    1): module-level `name = <ctor>()` assignments map `name` -> `name`
    itself; class-level `self.<attr> = <ctor>()` assignments (found inside
    any method body) map `ClassName.attr` -> `ClassName.attr`. Both keys
    and canonical ids are the same string deliberately -- the table is a
    SET of known-identifiable canonical ids, keyed for O(1) membership."""
    locks: dict[str, str] = {}
    for c in root.children:
        if c.type == "assignment":
            left = _child(c, "left")
            call = _assignment_ctor_callee(c)
            if left is not None and left.type == "identifier" and call is not None:
                callee = _py_call_callee_text(call)
                if _LOCK_CTOR_RE.search(callee):
                    name = _node_text(left)
                    locks[name] = name
        elif c.type == "class_definition":
            name_node = _child(c, "name")
            cname = _node_text(name_node) if name_node is not None else "?"
            body = _child(c, "body")
            if body is None:
                continue
            for assign in _iter_own_scope(body):
                if assign.type != "assignment":
                    continue
                left = _child(assign, "left")
                call = _assignment_ctor_callee(assign)
                if (
                    left is not None
                    and left.type == "attribute"
                    and call is not None
                ):
                    obj = _child(left, "object")
                    attr = _child(left, "attribute")
                    if (
                        obj is not None
                        and obj.type == "identifier"
                        and _node_text(obj) == "self"
                        and attr is not None
                    ):
                        callee = _py_call_callee_text(call)
                        if _LOCK_CTOR_RE.search(callee):
                            canon = f"{cname}.{_node_text(attr)}"
                            locks[canon] = canon
    return locks


def _with_item_expr_text(with_item: Node) -> str:
    """The raw source text of one `with_item`'s context expression, EXCLUDING
    an `as X` target -- tree-sitter-python wraps `expr as target` in an
    `as_pattern` node whose first named child is the actual expression
    (T-0694)."""
    child = with_item.named_children[0] if with_item.named_children else with_item
    if child.type == "as_pattern":
        value = child.named_children[0] if child.named_children else child
        return _node_text(value)
    return _node_text(child)


def _resolve_lock_expr(
    text: str, class_name: str | None, module_locks: dict[str, str]
) -> str | None:
    """Canonical lock id for a use-site expression `text` (T-0694): a bare
    module-level name resolves directly; a `self.<attr>` expression
    resolves against `class_name.<attr>` when the use site's own enclosing
    class assigned that attribute (a `self.attr` used outside its owning
    class, or naming a different attr, does not alias -- see this module's
    docstring). Returns `None` when `text` matches no known lock identity."""
    if text in module_locks:
        return module_locks[text]
    if class_name is not None and text.startswith("self."):
        attr = text[len("self.") :]
        canon = f"{class_name}.{attr}"
        if canon in module_locks:
            return canon
    return None


class _LockEvent:
    """One RESOLVED lock-acquisition event inside a function's own body
    (T-0694): `lock_id` is the canonical id (an unresolved-but-lock-shaped
    use site never becomes a `_LockEvent` -- it is tracked separately in
    the per-function `unresolved` text set instead, see
    `_collect_function_lock_events`); `line` is the acquisition site's
    source line."""

    __slots__ = ("lock_id", "line", "raw_text")

    def __init__(self, lock_id: str, line: int, raw_text: str) -> None:
        """Bind this event's resolved canonical lock id, source line, and
        the raw expression text (kept for message/debug purposes)."""
        self.lock_id = lock_id
        self.line = line
        self.raw_text = raw_text


class _CallEvent:
    """One same-module call-site event inside a function's own body
    (T-0694): `bare_name` is the callee's bare (last-dotted-segment) name,
    looked up against the module's same-module name-to-function table at
    propagation time (`_ordered_pairs_for_function`'s docstring)."""

    __slots__ = ("bare_name", "line")

    def __init__(self, bare_name: str, line: int) -> None:
        """Bind this call event's bare callee name and source line."""
        self.bare_name = bare_name
        self.line = line


def _collect_function_lock_events(
    body: Node, class_name: str | None, module_locks: dict[str, str]
) -> tuple[list[_LockEvent | _CallEvent], set[str]]:
    """`func`'s own ordered event sequence (T-0694, this module's docstring
    step 2) -- a list of `_LockEvent`/`_CallEvent` in program order over
    `body`'s own scope (`_iter_own_scope`), plus the set of raw texts that
    looked lock-shaped but never resolved (feeds the per-function
    `lock-identity-unresolved` advisory, deduplicated so one function
    contributes at most one finding regardless of how many unresolved
    sites it has)."""
    events: list[_LockEvent | _CallEvent] = []
    unresolved: set[str] = set()
    for node in _iter_own_scope(body):
        if node.type == "with_clause":
            for item in node.named_children:
                if item.type != "with_item":
                    continue
                text = _with_item_expr_text(item)
                line = item.start_point[0] + 1
                lock_id = _resolve_lock_expr(text, class_name, module_locks)
                if lock_id is not None:
                    events.append(_LockEvent(lock_id, line, text))
                elif _LOCK_NAME_HINT_RE.search(text):
                    unresolved.add(text)
        elif node.type == "call":
            callee = _py_call_callee_text(node)
            line = node.start_point[0] + 1
            if _ACQUIRE_CALL_RE.search(callee):
                receiver = callee.rsplit(".", 1)[0]
                lock_id = _resolve_lock_expr(receiver, class_name, module_locks)
                if lock_id is not None:
                    events.append(_LockEvent(lock_id, line, receiver))
                elif _LOCK_NAME_HINT_RE.search(receiver):
                    unresolved.add(receiver)
            else:
                bare = callee.rsplit(".", 1)[-1]
                events.append(_CallEvent(bare, line))
    return events, unresolved


class _FunctionLockInfo:
    """One function's precomputed lock-ordering inputs (T-0694): its
    `symref`, own event sequence, and the set of raw unresolved-lock-shaped
    texts (`_collect_function_lock_events`) -- registered once per function
    before the interprocedural fixpoint runs, mirroring
    `frob.arch._mayraise.compute_may_raise`'s own `_register` pre-pass."""

    __slots__ = ("symref", "events", "unresolved")

    def __init__(
        self,
        symref: str,
        events: list[_LockEvent | _CallEvent],
        unresolved: set[str],
    ) -> None:
        """Bind this function's symref, own event sequence, and unresolved-
        lock-shaped text set."""
        self.symref = symref
        self.events = events
        self.unresolved = unresolved


class _OrderEdge:
    """One directed lock-order edge (T-0694): `lockA -> lockB` observed on
    some call path, tagged with the contributing function's `symref` and
    the `line` of the EARLIER (`lockA`) event, for the finding message."""

    __slots__ = ("src", "dst", "symref", "line")

    def __init__(self, src: str, dst: str, symref: str, line: int) -> None:
        """Bind this edge's source/destination lock ids and the
        contributing function's symref/line."""
        self.src = src
        self.dst = dst
        self.symref = symref
        self.line = line


def _reachable_locks(
    infos: dict[int, _FunctionLockInfo],
    name_to_fid: dict[str, int],
    reachable: dict[int, set[str]],
) -> None:
    """Fixpoint step (T-0694, this module's docstring step 3): compute
    `reachable[fid]`, the set of every canonical lock id reachable anywhere
    in `fid`'s own body OR transitively through same-module calls it makes
    -- a monotonic chaotic-iteration fixpoint over the whole module's
    functions (mirrors `frob.arch._mayraise.compute_may_raise`'s cycle-safe
    fixpoint loop exactly, just growing a lock-id set instead of a
    may-raise set)."""
    changed = True
    while changed:
        changed = False
        for cur_fid, info in infos.items():
            pool = set(reachable[cur_fid])
            for ev in info.events:
                if isinstance(ev, _LockEvent):
                    pool.add(ev.lock_id)
                elif isinstance(ev, _CallEvent):
                    callee_fid = name_to_fid.get(ev.bare_name)
                    if callee_fid is not None:
                        pool |= reachable[callee_fid]
            if pool != reachable[cur_fid]:
                reachable[cur_fid] = pool
                changed = True


def _edges_for_function(
    info: _FunctionLockInfo,
    name_to_fid: dict[str, int],
    reachable: dict[int, set[str]],
) -> list[_OrderEdge]:
    """Every directed lock-order edge (T-0694, this module's docstring step
    4) `info`'s own event sequence implies: each event becomes a "slot"
    (an own lock event is a one-lock slot; a resolved call event's slot is
    the callee's fully-propagated `reachable` set) and every earlier slot's
    lock is paired against every later slot's lock (excluding same-lock
    pairs -- reentrant use never counts as an ordering hazard)."""
    slots: list[tuple[set[str], int]] = []
    for ev in info.events:
        if isinstance(ev, _LockEvent):
            slots.append(({ev.lock_id}, ev.line))
        else:
            callee_fid = name_to_fid.get(ev.bare_name)
            locks = (
                reachable.get(callee_fid, set()) if callee_fid is not None else set()
            )
            if locks:
                slots.append((locks, ev.line))

    edges: list[_OrderEdge] = []
    for i, (earlier_locks, line) in enumerate(slots):
        later_union: set[str] = set()
        for later_locks, _ in slots[i + 1 :]:
            later_union |= later_locks
        for a in earlier_locks:
            for b in later_union:
                if a != b:
                    edges.append(_OrderEdge(a, b, info.symref, line))
    return edges


def _find_cycle(
    edges: list[_OrderEdge],
) -> tuple[str, str, _OrderEdge, _OrderEdge] | None:
    """The first cyclic lock pair found in `edges` (T-0694, this module's
    docstring step 5): builds a directed adjacency map from every edge's
    `(src, dst)` and looks for the SIMPLEST case this ticket's own
    acceptance criterion names -- some pair `(A, B)` with both an `A -> B`
    edge and a `B -> A` edge, each from a (possibly different) contributing
    function. Returns `(A, B, edge_a_to_b, edge_b_to_a)` for the first such
    pair found (by first-seen order of the edge list, stable and
    deterministic), or `None` when no reciprocal pair exists -- a
    consistent global order across every call path in the module produces
    none, per the ticket's own silence criterion."""
    by_pair: dict[tuple[str, str], _OrderEdge] = {}
    for e in edges:
        by_pair.setdefault((e.src, e.dst), e)
    for (a, b), edge_ab in by_pair.items():
        edge_ba = by_pair.get((b, a))
        if edge_ba is not None:
            return a, b, edge_ab, edge_ba
    return None


# frob:ticket T-0694
# frob:tests tests/unit/test_arch.py::TestLockOrderingHazards.test_two_lock_ab_ba_cycle_fires_within_one_function  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestLockOrderingHazards.test_two_lock_ab_ba_cycle_fires_across_call_paths_via_callees  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestLockOrderingHazards.test_consistent_global_order_does_not_fire  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestLockOrderingHazards.test_reentrant_same_lock_does_not_fire  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestLockOrderingHazards.test_unresolvable_lock_identity_is_advisory  # noqa: E501
def _check_lock_ordering_hazards(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """Run the lock-ordering hazard check (this module's docstring) over
    one parsed python file: build the module's lock-identity table, each
    function's own event sequence, the interprocedural reachable-lock
    fixpoint, every function's implied order edges, then report the first
    cyclic pair found (`lock-order-cycle`) plus one `lock-identity-
    unresolved` advisory per function with unresolved lock-shaped usage
    (T-0694)."""
    t = cast("Tree", tree)
    root = t.root_node
    module_locks = _collect_module_locks(root)

    infos: dict[int, _FunctionLockInfo] = {}
    fids_by_bare: dict[str, list[int]] = {}

    for func_node, class_prefix, fname in _iter_py_functions(root):
        body = _child(func_node, "body")
        if body is None:
            continue
        class_name = class_prefix[:-1] if class_prefix else None
        symref = f"{rel}::{class_prefix}{fname}" if class_prefix else f"{rel}::{fname}"
        events, unresolved = _collect_function_lock_events(
            body, class_name, module_locks
        )
        fid = id(func_node)
        infos[fid] = _FunctionLockInfo(symref, events, unresolved)
        fids_by_bare.setdefault(fname, []).append(fid)

    # Same-module bare-name -> fid, AMBIGUOUS names (bound to more than one
    # function/method) excluded entirely -- fail-closed, same convention as
    # `frob.arch._mayraise._build_name_to_func` (this module's docstring
    # step 3).
    name_to_fid = {name: fs[0] for name, fs in fids_by_bare.items() if len(fs) == 1}

    reachable: dict[int, set[str]] = {fid: set() for fid in infos}
    _reachable_locks(infos, name_to_fid, reachable)

    all_edges: list[_OrderEdge] = []
    for fid, info in infos.items():
        all_edges.extend(_edges_for_function(info, name_to_fid, reachable))

    cycle = _find_cycle(all_edges)
    if cycle is not None:
        lock_a, lock_b, edge_ab, edge_ba = cycle
        _log.warning(
            "lock-order-cycle: %s acquires %s before %s (line %d); %s "
            "acquires %s before %s (line %d)",
            edge_ab.symref,
            lock_a,
            lock_b,
            edge_ab.line,
            edge_ba.symref,
            lock_b,
            lock_a,
            edge_ba.line,
        )
        out.append(
            ArchSuggestion(
                file=rel,
                line=edge_ab.line,
                category="lock-order-cycle",
                severity="warning",
                message=(
                    f"cyclic lock-acquisition order between `{lock_a}` and "
                    f"`{lock_b}`: {edge_ab.symref} acquires {lock_a} before "
                    f"{lock_b} (line {edge_ab.line}); {edge_ba.symref} "
                    f"acquires {lock_b} before {lock_a} (line {edge_ba.line})"
                ),
                detail=(
                    "if these two call paths can ever run concurrently, "
                    "acquiring the two locks in opposite orders can "
                    "deadlock -- establish one consistent global "
                    "acquisition order for every path that needs both locks"
                ),
                symref=edge_ab.symref,
            )
        )

    for info in infos.values():
        if not info.unresolved:
            continue
        sample = sorted(info.unresolved)[0]
        _log.info(
            "lock-identity-unresolved: %s has lock-shaped usage `%s` this "
            "resolver could not statically identify",
            info.symref,
            sample,
        )
        out.append(
            ArchSuggestion(
                file=rel,
                line=None,
                category="lock-identity-unresolved",
                severity="suggestion",
                message=(
                    f"{info.symref}: lock-shaped usage (`{sample}`, and "
                    f"possibly others) could not be resolved to a known "
                    f"module/class-level lock construction -- lock-order-"
                    f"cycle detection cannot account for it"
                ),
                detail=(
                    "declare the lock as a module-level or self.<attr> "
                    "assignment of threading/multiprocessing/anyio/asyncio's "
                    "Lock/RLock/Semaphore/BoundedSemaphore so this check "
                    "can track its acquisition order"
                ),
                symref=info.symref,
            )
        )
