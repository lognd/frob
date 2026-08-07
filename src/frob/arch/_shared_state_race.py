"""Shared-mutable-state race approximation (T-0697, child 4 of the T-0693
concurrency-hazard umbrella): a structural, INTERPROCEDURAL scan flagging a
WRITE to module-level or class-level MUTABLE state (a rebind assignment, a
subscript assignment, or a curated mutating-method call) reachable from a
thread-target / executor-submission / async-task dispatch point, with no
lock acquisition enclosing the write in ITS OWN function's body. Same
fail-closed, non-runtime-tracing posture as this package's other
concurrency-hazard checks (`frob.arch._concurrency`'s fork/pool family
T-0695; `frob.arch._async_hazards`'s event-loop family T-0696;
`frob.arch._lock_ordering`'s lock-order family T-0694): a finding flags a
STRUCTURAL shape that makes a race possible, not a proof it fires at
runtime. Single-process cousin of strata's distributed no-shared-mutable-
state check (REL360, T-0656, `frob.strata._shared_state`) -- this module
tracks python-level `threading`/`multiprocessing`/`asyncio` dispatch inside
one process's call graph, not cross-service state; no logic is duplicated
between the two, only the "shared mutable state" naming convention is
shared intentionally.

MODEL (T-0697):

1. SHARED-STATE IDENTITY (`_collect_shared_state`): reuses
   `frob.arch._lock_ordering`'s own module/class-level identity convention
   (`_collect_module_locks`'s structure), but keyed on MUTABLE-LITERAL
   construction instead of lock construction -- a module-level
   `name = [...]`/`{...}`/`{...}` (set/dict)/`list(...)`/`dict(...)`/
   `set(...)` assignment, or a class-level `self.<attr> = <same shapes>`
   assignment inside any method body. Canonical ids follow the identical
   `name` / `ClassName.attr` convention `_lock_ordering._collect_module_
   locks` already establishes.

2. THREAD/TASK DISPATCH ENTRYPOINTS (`_dispatch_entrypoints`): reuses
   `frob.arch._concurrency._dispatched_callee_names`'s pool/thread submit
   corpus (`.submit`/`.map`/`.apply_async`, `Thread(target=...)`) and adds
   the async-task construction shapes that corpus does not cover
   (`asyncio.create_task(f)`, `asyncio.ensure_future(f)`, a
   `<loop>.create_task(f)` method call) using the same first-positional-
   argument name convention `_concurrency._first_arg_names` already uses.

3. INTERPROCEDURAL REACHABILITY (`_reachable_from_dispatch`): a same-module
   call graph (the same bare-name resolution convention `_lock_ordering`/
   `_mayraise`/`_fallibility` all share) closed over via BFS from every
   directly-dispatched function -- any function transitively CALLED by a
   dispatched function is thread/task-reachable too, since the write could
   happen inside a helper the worker calls, not just the worker's own body.

4. WRITE DETECTION + LOCK ENCLOSURE (`_writes_in_function`): every write
   site (rebind assignment, subscript assignment, or a curated mutating-
   method call -- append/extend/insert/remove/pop/clear/sort/reverse/
   update/add/discard/popitem/setdefault) to a canonical shared-state id,
   found in the WRITING function's own scope (`_iter_own_scope`, matching
   this package's other checks) -- resolved via the same `self.<attr>`
   class-name-scoped rule `_lock_ordering._resolve_lock_expr` uses. A write
   is silenced when it is lexically enclosed by a `with_statement` whose
   with-items resolve (or merely LOOK lock-shaped, same permissive
   heuristic as `_lock_ordering`'s advisory-unresolved case) -- checked
   against THIS FUNCTION's own ancestor chain only, deliberately NOT
   tracking whether a caller elsewhere on the reachable path already holds
   the lock (a documented model limit, see below).

Only a write inside a function that is thread/task-reachable (step 3) AND
unenclosed by any lock-shaped `with` (step 4) is reported --
`unguarded-shared-write`, one finding per (function, canonical id) pair
(deduplicated the same way `_lock_ordering`'s unresolved-identity advisory
is, to avoid drowning signal on a tight write loop).

MODEL-LIMIT DISCLOSURE (matching this package's house convention): same-
module only (no cross-file call resolution, matching every other
`frob.arch` interprocedural check); a lock enclosing the write site
LEXICALLY silences it regardless of whether that specific lock actually
guards this specific piece of state (a `with unrelated_lock:` around an
unrelated write silences too -- deliberately permissive, matching
`_lock_ordering`'s own "any lock-shaped with" acceptance shape, since
correlating a SPECIFIC lock to a SPECIFIC piece of state is a heavier claim
than this approximation makes); a lock acquired by a CALLER before
dispatching into a callee that performs the write is not modeled (the
callee's own body is checked in isolation, per step 4) -- a documented
false-positive source, waivable per-site via the usual advisory channel.
Mutable-state identity is a CONSTRUCTION-shape heuristic only (a name
assigned a non-mutable-looking expression, e.g. an int counter target of
`+=`, is not tracked -- augmented-assignment races on immutable-typed
counters are a distinct hazard class, out of this ticket's own "shared
MUTABLE state" framing).

Every finding stays on the same unwaivable advisory channel every other
`frob.arch` category is on (`frob.gates._unwaivable_channel_rules` auto-
adopts any new `ArchCategory` value, so no `frob.gates` change is needed
here) -- see docs/modules/arch.md's concurrency-hazard sections for the
sibling categories this one joins.
"""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Iterator
from typing import cast

from tree_sitter import Node, Tree

from frob.arch._concurrency import _first_arg_names, _target_kwarg_names
from frob.arch._lock_ordering import (
    _LOCK_NAME_HINT_RE,
    _collect_module_locks,
    _resolve_lock_expr,
)
from frob.arch._models import ArchSuggestion
from frob.arch._python import _iter_own_scope, _iter_py_functions, _py_call_callee_text
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text
from frob.logging import get_logger

_log = get_logger(__name__)

#: RHS shapes that count as a fresh MUTABLE-container construction (T-0697,
#: this module's docstring step 1): a bare literal (`[]`, `{}`, `{1, 2}`) or
#: a call to `list`/`dict`/`set` (bare or dotted, matching
#: `_lock_ordering._LOCK_CTOR_RE`'s own permissive-receiver convention).
_MUTABLE_LITERAL_TYPES = ("list", "dictionary", "set")
_MUTABLE_CTOR_RE = re.compile(r"(?:^|\.)(?:list|dict|set)$")

#: Curated mutating-method table (T-0697): a call to one of these names on a
#: resolved shared-state receiver is a WRITE, not a read.
_MUTATING_METHOD_RE = re.compile(
    r"\.(?:append|extend|insert|remove|pop|clear|sort|reverse|update|add|"
    r"discard|popitem|setdefault|__setitem__|__delitem__)$"
)

#: Async-task dispatch constructors this module adds on top of
#: `frob.arch._concurrency`'s pool/thread submit corpus (T-0697, this
#: module's docstring step 2): `asyncio.create_task`/`ensure_future`, or a
#: bare/dotted `.create_task(...)` (an event-loop object's own method).
_ASYNC_TASK_CALL_RE = re.compile(r"(?:^|\.)(?:create_task|ensure_future)$")


def _iter_calls(node: Node) -> Iterator[Node]:
    """Every `call` node in `node`'s full subtree, without stopping at a
    nested `function_definition`/`class_definition` boundary -- mirrors
    `frob.arch._concurrency._iter_calls`'s own "reachability through nested
    closures" rationale, needed here to find dispatch sites regardless of
    where they are lexically nested."""
    if node.type == "call":
        yield node
    for c in node.children:
        yield from _iter_calls(c)


def _assignment_mutable_ctor(assign_node: Node) -> bool:
    """Whether `assign_node`'s right-hand side is a fresh mutable-container
    construction (T-0697, this module's docstring step 1): a bare `[]`/
    `{}`/`{...}` literal, or a `list()`/`dict()`/`set()` call."""
    right = _child(assign_node, "right")
    if right is None:
        return False
    if right.type in _MUTABLE_LITERAL_TYPES:
        return True
    if right.type == "call":
        callee = _py_call_callee_text(right)
        return bool(_MUTABLE_CTOR_RE.search(callee))
    return False


def _module_level_shared_state_name(assign: Node) -> str | None:
    """Canonical id for a module-level `name = <mutable-ctor>` shared-state
    assignment, or `None` if `assign` does not match that shape (T-0697
    step 1, extracted from `_collect_shared_state` to cut nesting,
    T-0394)."""
    left = _child(assign, "left")
    if left is None or left.type != "identifier":
        return None
    if not _assignment_mutable_ctor(assign):
        return None
    return _node_text(left)


def _class_attr_shared_state_name(assign: Node, cname: str) -> str | None:
    """Canonical `ClassName.attr` id for a `self.<attr> = <mutable-ctor>`
    shared-state assignment inside a class body, or `None` if `assign`
    does not match that shape (T-0697 step 1, extracted from
    `_collect_shared_state` to cut nesting, T-0394)."""
    left = _child(assign, "left")
    if left is None or left.type != "attribute":
        return None
    if not _assignment_mutable_ctor(assign):
        return None
    obj = _child(left, "object")
    attr = _child(left, "attribute")
    is_self = obj is not None and obj.type == "identifier" and _node_text(obj) == "self"
    if not is_self or attr is None:
        return None
    return f"{cname}.{_node_text(attr)}"


def _collect_class_shared_state(class_node: Node) -> dict[str, str]:
    """Canonical shared-state entries for one class's `self.<attr> =
    <mutable-ctor>` assignments (T-0697 step 1, extracted from
    `_collect_shared_state` to cut nesting, T-0394)."""
    name_node = _child(class_node, "name")
    cname = _node_text(name_node) if name_node is not None else "?"
    body = _child(class_node, "body")
    if body is None:
        return {}
    state: dict[str, str] = {}
    for assign in _iter_own_scope(body):
        if assign.type != "assignment":
            continue
        canon = _class_attr_shared_state_name(assign, cname)
        if canon is not None:
            state[canon] = canon
    return state


def _collect_shared_state(root: Node) -> dict[str, str]:
    """Canonical shared-mutable-state identity table (T-0697, this module's
    docstring step 1): module-level `name = <mutable-ctor>` assignments map
    `name` -> `name`; class-level `self.<attr> = <mutable-ctor>`
    assignments (found inside any method body) map `ClassName.attr` ->
    `ClassName.attr`. Mirrors `frob.arch._lock_ordering._collect_module_
    locks`'s exact structure, just gated on a mutable-construction RHS
    instead of a lock-constructor RHS."""
    state: dict[str, str] = {}
    for c in root.children:
        if c.type == "assignment":
            name = _module_level_shared_state_name(c)
            if name is not None:
                state[name] = name
        elif c.type == "class_definition":
            state.update(_collect_class_shared_state(c))
    return state


def _async_task_arg_names(call_node: Node) -> list[str]:
    """Candidate callee names from an `asyncio.create_task(worker())`-shaped
    call's first positional argument (T-0697): unlike `.submit(worker)`,
    the argument is itself a CALL expression (the coroutine object) --
    `_first_arg_names`'s raw-text convention would capture `worker()`
    (including the trailing parens) rather than the bare callee, so this
    extracts the inner call's own callee text instead when the argument is
    a `call` node, falling back to `_first_arg_names`'s plain-name
    convention otherwise (a coroutine passed by bare reference, e.g. a
    variable already holding the coroutine object)."""
    args = _child(call_node, "arguments")
    if args is None:
        return []
    first = next(iter(args.named_children), None)
    if first is None:
        return []
    if first.type == "call":
        text = _py_call_callee_text(first)
    else:
        text = _node_text(first)
    names = [text]
    if "." in text:
        names.append(text.rsplit(".", 1)[-1])
    return names


def _dispatch_entrypoints(root: Node) -> set[str]:
    """Every callee name (raw + bare-segment) dispatched as a thread/
    executor/async-task target ANYWHERE in the module (T-0697, this
    module's docstring step 2) -- `_concurrency._dispatched_callee_names`'s
    pool/thread submit corpus, widened with `asyncio.create_task`/
    `ensure_future`/`<loop>.create_task` async-task construction."""
    names: set[str] = set()
    for call_node in _iter_calls(root):
        callee = _py_call_callee_text(call_node)
        if re.search(r"\.(?:submit|map|apply_async)$", callee):
            names.update(_first_arg_names(call_node))
        elif re.search(r"(?:^|\.)Thread$", callee):
            names.update(_target_kwarg_names(call_node))
        elif _ASYNC_TASK_CALL_RE.search(callee):
            names.update(_async_task_arg_names(call_node))
    return names


class _FunctionScan:
    """One function's precomputed shared-state inputs (T-0697): its
    `symref`, bare name, the set of same-module bare callee names it calls
    (own scope only, for the reachability BFS), and its own write sites
    (each a `(canonical_id, line, lock_enclosed)` tuple, from
    `_writes_in_function`)."""

    __slots__ = ("symref", "fname", "calls", "writes")

    def __init__(
        self,
        symref: str,
        fname: str,
        calls: set[str],
        writes: list[tuple[str, int, bool]],
    ) -> None:
        """Bind this function's symref, bare name, callee-name corpus, and
        own write-site list."""
        self.symref = symref
        self.fname = fname
        self.calls = calls
        self.writes = writes


def _with_clause_has_lock_item(
    clause: Node, class_name: str, module_locks: dict[str, str]
) -> bool:
    """Whether one `with_clause`'s items resolve to a known lock, or merely
    LOOK lock-shaped (T-0697 step 4, extracted from `_enclosing_lock_with`
    to cut nesting, T-0394)."""
    for item in clause.named_children:
        if item.type != "with_item":
            continue
        child = item.named_children[0] if item.named_children else item
        if child.type == "as_pattern":
            child = child.named_children[0] if child.named_children else child
        text = _node_text(child)
        if _resolve_lock_expr(text, class_name, module_locks) is not None or (
            _LOCK_NAME_HINT_RE.search(text)
        ):
            return True
    return False


def _enclosing_lock_with(
    node: Node, class_name: str, module_locks: dict[str, str]
) -> bool:
    """Whether `node` is lexically enclosed by a `with_statement` whose
    with-items resolve to a known lock, OR merely LOOK lock-shaped (T-0697,
    this module's docstring step 4 -- same permissive heuristic
    `frob.arch._lock_ordering`'s own unresolved-identity advisory uses, so
    a lock this module cannot statically identify still silences a write
    rather than producing a false positive on top of a separate
    `lock-identity-unresolved` advisory)."""
    cur = node.parent
    while cur is not None:
        # frob:waive PERF003 reason="ancestor-chain walk (bounded by AST nesting depth) over each with_statement's own small with-item list (bounded by items in one `with` clause) -- not a cross join over two large collections"  # noqa: E501
        if cur.type == "with_statement":
            for wc in cur.named_children:
                if wc.type == "with_clause" and _with_clause_has_lock_item(
                    wc, class_name, module_locks
                ):
                    return True
        cur = cur.parent
    return False


def _writes_in_function(
    body: Node,
    class_name: str | None,
    shared_state: dict[str, str],
    module_locks: dict[str, str],
) -> list[tuple[str, int, bool]]:
    """Every write site to a canonical shared-state id inside `body`'s own
    scope (T-0697, this module's docstring step 4): a rebind assignment, a
    subscript assignment, or a curated mutating-method call, each resolved
    via the same `self.<attr>` class-scoped rule
    `_lock_ordering._resolve_lock_expr` uses. Each tuple is `(canonical_id,
    line, lock_enclosed)`."""
    writes: list[tuple[str, int, bool]] = []
    cname = class_name or ""
    for node in _iter_own_scope(body):
        if node.type == "assignment":
            left = _child(node, "left")
            if left is None:
                continue
            if left.type == "identifier":
                text = _node_text(left)
            elif left.type == "subscript":
                base = left.named_children[0] if left.named_children else left
                text = _node_text(base)
            elif left.type == "attribute":
                text = _node_text(left)
            else:
                continue
            canon = _resolve_lock_expr(text, cname, shared_state)
            if canon is not None:
                line = left.start_point[0] + 1
                enclosed = _enclosing_lock_with(node, cname, module_locks)
                writes.append((canon, line, enclosed))
        elif node.type == "call":
            callee = _py_call_callee_text(node)
            if _MUTATING_METHOD_RE.search(callee):
                receiver = callee.rsplit(".", 1)[0]
                canon = _resolve_lock_expr(receiver, cname, shared_state)
                if canon is not None:
                    line = node.start_point[0] + 1
                    enclosed = _enclosing_lock_with(node, cname, module_locks)
                    writes.append((canon, line, enclosed))
    return writes


def _reachable_from_dispatch(
    scans: dict[int, _FunctionScan],
    name_to_fid: dict[str, int],
    entrypoints: set[str],
) -> set[int]:
    """BFS closure (T-0697, this module's docstring step 3) over the
    same-module call graph, starting from every function whose bare name is
    in `entrypoints` -- every function transitively called from a
    dispatched function is thread/task-reachable too."""
    start = [fid for fid, s in scans.items() if s.fname in entrypoints]
    seen: set[int] = set(start)
    queue: deque[int] = deque(start)
    while queue:
        fid = queue.popleft()
        for callee_name in scans[fid].calls:
            callee_fid = name_to_fid.get(callee_name)
            if callee_fid is not None and callee_fid not in seen:
                seen.add(callee_fid)
                queue.append(callee_fid)
    return seen


# frob:ticket T-0697
def _collect_function_scans(
    root: Node, rel: str, shared_state: dict[str, str], module_locks: dict[str, str]
) -> tuple[dict[int, _FunctionScan], dict[str, int]]:
    """Build this module's two shared per-function tables in one pass:
    `id(func_node) -> _FunctionScan` for every function/method in the
    parsed tree, and the same-module bare-name -> fid lookup (ambiguous
    names bound to more than one function excluded entirely, fail-closed,
    same convention as `frob.arch._mayraise._build_name_to_func` and
    `frob.arch._lock_ordering._collect_function_lock_infos`)."""
    scans: dict[int, _FunctionScan] = {}
    fids_by_bare: dict[str, list[int]] = {}

    for func_node, class_prefix, fname in _iter_py_functions(root):
        body = _child(func_node, "body")
        if body is None:
            continue
        class_name = class_prefix[:-1] if class_prefix else None
        symref = f"{rel}::{class_prefix}{fname}" if class_prefix else f"{rel}::{fname}"
        writes = _writes_in_function(body, class_name, shared_state, module_locks)
        calls = {_py_call_callee_text(n).rsplit(".", 1)[-1] for n in _iter_calls(body)}
        fid = id(func_node)
        scans[fid] = _FunctionScan(symref, fname, calls, writes)
        fids_by_bare.setdefault(fname, []).append(fid)

    name_to_fid = {name: fs[0] for name, fs in fids_by_bare.items() if len(fs) == 1}
    return scans, name_to_fid


def _unguarded_shared_write_finding(
    rel: str, symref: str, canon: str, line: int
) -> ArchSuggestion:
    """The `unguarded-shared-write` `ArchSuggestion` (and matching log line)
    for one unguarded write site."""
    _log.warning(
        "unguarded-shared-write: %s writes shared state `%s` at line %d "
        "on a thread/task-reachable path with no enclosing lock",
        symref,
        canon,
        line,
    )
    return ArchSuggestion(
        file=rel,
        line=line,
        category="unguarded-shared-write",
        severity="warning",
        message=(
            f"{symref}: write to shared mutable state `{canon}` at line "
            f"{line} is reachable from a thread/executor/async-task "
            f"dispatch point with no lock enclosing it"
        ),
        detail=(
            "wrap this write (and every other write/read that must stay "
            "consistent with it) in a `with <lock>:` block shared across "
            "every thread/task that can reach this state, or make the "
            "write itself thread-confined"
        ),
        symref=symref,
    )


# frob:ticket T-0697
# frob:tests tests/unit/test_arch.py::TestSharedStateRaceHazards.test_unguarded_write_from_thread_submitted_function_fires  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestSharedStateRaceHazards.test_same_write_under_with_lock_does_not_fire  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestSharedStateRaceHazards.test_write_reachable_via_callee_of_dispatched_function_fires  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestSharedStateRaceHazards.test_write_not_reachable_from_any_dispatch_does_not_fire  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestSharedStateRaceHazards.test_async_create_task_dispatch_fires_same_as_thread_submit  # noqa: E501
def _check_shared_state_race_hazards(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """Run the shared-mutable-state race check (this module's docstring)
    over one parsed python file: build the module's shared-state and lock
    identity tables, every function's own write sites and call corpus, the
    thread/task dispatch entrypoint corpus, the BFS reachability closure,
    then report `unguarded-shared-write` for every unenclosed write inside
    a reachable function (T-0697)."""
    t = cast("Tree", tree)
    root = t.root_node
    module_locks = _collect_module_locks(root)
    shared_state = _collect_shared_state(root)
    if not shared_state:
        return
    scans, name_to_fid = _collect_function_scans(root, rel, shared_state, module_locks)
    entrypoints = _dispatch_entrypoints(root)
    if not entrypoints:
        return
    reachable = _reachable_from_dispatch(scans, name_to_fid, entrypoints)

    for fid in reachable:
        scan = scans.get(fid)
        if scan is None:
            continue
        seen_pairs: set[tuple[str, str]] = set()
        for canon, line, enclosed in scan.writes:
            if enclosed:
                continue
            key = (scan.symref, canon)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            out.append(_unguarded_shared_write_finding(rel, scan.symref, canon, line))
