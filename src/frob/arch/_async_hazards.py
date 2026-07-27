"""Async event-loop hazard checks (T-0696, child 3 of the T-0693 concurrency-
hazard umbrella): structural, syntactic co-occurrence heuristics over one
parsed python file's functions -- same fail-closed, non-runtime-tracing
posture as `frob.arch._concurrency`'s fork/pool family (T-0695): every
detector here flags the STRUCTURAL shape that makes an event-loop hazard
possible, not a proof that it fires at runtime. Four detectors:

- `blocking-call-in-async`: a curated blocking call (`time.sleep`,
  `requests.get/post/put/delete/patch/head/request`, `urllib`'s
  `urlopen`, `subprocess.run/call/check_call/check_output`, a bare
  `.result()` future/Future wait, or the builtin `open(...)`) reachable
  inside an `async def` body, UNLESS the call site is itself the callable
  argument to a `run_in_executor`/`to_thread` dispatch (which correctly
  offloads it off the event loop). MODEL LIMIT: `open`/`.result()` are
  curated by name alone -- this scan cannot distinguish a large blocking
  read from a trivial one, or a `concurrent.futures.Future.result()` from
  an unrelated `.result()` accessor; both stay advisory-tier for exactly
  that reason, matching the ticket's "curated table, not a proof" framing.
- `nested-event-loop`: `asyncio.run(...)`/`.run_until_complete(...)`
  reachable inside an `async def` body -- a coroutine is by construction
  already running on a loop when it executes, so either call raises
  `RuntimeError: ... cannot be called from a running event loop`.
- `unawaited-coroutine`: a call to a function this module itself defines
  as `async def`, used as a bare expression statement -- neither awaited,
  gathered (`asyncio.gather`/`asyncio.ensure_future`/`asyncio.create_task`
  wrap it as an ARGUMENT, so the bare top-level statement is a different
  call), nor stored/returned -- the call constructs a coroutine object
  whose body silently never runs.
- `async-zero-awaits`: an `async def` whose body contains no `await`
  expression anywhere in its OWN scope (not crossing into a nested
  function's body -- that nested function is visited separately) -- it
  never actually suspends back to the loop, so it should probably be a
  plain `def` (feeds T-0698's IO/CPU-bound model-mismatch advisory too,
  per that ticket's own text).

Every finding stays on the same unwaivable advisory channel every other
`frob.arch` category is on (`frob.gates._unwaivable_channel_rules` auto-
adopts any new `ArchCategory` value, so no `frob.gates` change is needed
here) -- docs/modules/arch.md coverage is out of this ticket's declared
scope; the follow-up is T-0914.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.arch._python import _iter_py_functions, _py_call_callee_text
from frob.lang import child_by_field as _child
from frob.logging import get_logger

_log = get_logger(__name__)

#: Curated blocking-call table (T-0696): `(pattern, human label)` pairs
#: matched against a call's full dotted callee TEXT (as written, e.g.
#: `"time.sleep"`, `"requests.get"`) -- matching on the full text (not
#: just the trailing segment) deliberately avoids conflating `time.sleep`
#: with `asyncio.sleep`, which is the correctly-async equivalent.
_BLOCKING_CALL_TABLE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:^|\.)time\.sleep$"), "time.sleep"),
    (
        re.compile(r"(?:^|\.)requests\.(?:get|post|put|delete|patch|head|request)$"),
        "requests.*",
    ),
    (re.compile(r"(?:^|\.)urlopen$"), "urllib urlopen"),
    (
        re.compile(r"(?:^|\.)subprocess\.(?:run|call|check_call|check_output)$"),
        "subprocess.run/call/check_call/check_output",
    ),
    (re.compile(r"\.result$"), "a future's .result()"),
]
#: The builtin `open(...)` call, matched separately from the table above
#: since it is a BARE identifier (never a dotted attribute) -- curated
#: per the ticket's "sync open/read on large paths" entry; see this
#: module's docstring for the "large paths" model limit disclosure.
_OPEN_BUILTIN_RE = re.compile(r"^open$")

#: `run_in_executor`/`to_thread` -- the two correct ways to dispatch a
#: blocking call off the event loop; a blocking call whose call site is
#: the argument of one of these does NOT fire `blocking-call-in-async`.
_EXECUTOR_DISPATCH_RE = re.compile(r"(?:^|\.)(?:run_in_executor|to_thread)$")

#: `asyncio.run(...)` / `loop.run_until_complete(...)` -- both raise at
#: runtime when called from inside an already-running loop (every
#: `async def` body qualifies).
_NESTED_LOOP_RE = re.compile(r"(?:^|\.)(?:run_until_complete|asyncio\.run)$")

#: `asyncio.gather`/`asyncio.ensure_future`/`asyncio.create_task` -- a
#: coroutine call passed as one of THESE calls' arguments is gathered, not
#: an un-awaited bare statement; `unawaited-coroutine` inspects a call
#: whose immediate parent is a `block` (a bare top-level statement), so a
#: coroutine call nested as an argument here has an `argument_list` parent
#: instead and is not the shape that check inspects -- this table backs
#: the module docstring's cross-reference; the matching logic lives in
#: `_check_unawaited_coroutines` below.


def _is_async_def(func_node: Node) -> bool:
    """True if `func_node` (a `function_definition`) is declared
    `async def` -- tree-sitter-python parses the `async` keyword as the
    function definition's own first child token, not a separate wrapper
    node."""
    return any(c.type == "async" for c in func_node.children)


def _iter_calls_crossing_closures(node: Node) -> Iterator[Node]:
    """Every `call` node in `node`'s full subtree, recursing THROUGH nested
    function/class boundaries -- mirrors `frob.arch._concurrency._iter_
    calls`: a blocking call dispatched via a `def _worker(): ...` defined
    and invoked inside the same `async def` is exactly the shape this
    check wants to catch."""
    if node.type == "call":
        yield node
    for c in node.children:
        yield from _iter_calls_crossing_closures(c)


def _iter_own_scope(node: Node) -> Iterator[Node]:
    """Every node in `node`'s subtree belonging to the OWNING function's
    own scope -- stops descending at a nested `function_definition`/
    `class_definition` boundary (that nested scope gets its own pass via
    `_iter_py_functions`'s separate yield for it), so `await`-counting and
    bare-statement detection never double-count a nested closure's own
    awaits/statements as the outer function's."""
    if node.type in ("function_definition", "class_definition"):
        return
    yield node
    for c in node.children:
        yield from _iter_own_scope(c)


def _enclosed_by_executor_dispatch(call_node: Node, func_node: Node) -> bool:
    """True if `call_node` sits somewhere inside the argument list of a
    `run_in_executor`/`to_thread` call between it and `func_node` -- the
    call is being correctly dispatched off the event loop rather than
    invoked directly."""
    n = call_node.parent
    while n is not None:
        if n.type == "call" and _EXECUTOR_DISPATCH_RE.search(_py_call_callee_text(n)):
            return True
        if n is func_node:
            break
        n = n.parent
    return False


def _blocking_label(callee: str) -> str | None:
    """The curated human label for `callee`'s blocking-call table entry
    (`_BLOCKING_CALL_TABLE` or the bare `open` builtin), or `None` if
    `callee` matches no curated entry."""
    if _OPEN_BUILTIN_RE.match(callee):
        return "the builtin open()"
    for pattern, label in _BLOCKING_CALL_TABLE:
        if pattern.search(callee):
            return label
    return None


def _check_blocking_and_nested_loop(
    rel: str, fqname: str, func_node: Node, body: Node, out: list[ArchSuggestion]
) -> None:
    """`blocking-call-in-async` and `nested-event-loop` (T-0696): both scan
    the same call corpus reachable inside one `async def` body, so they
    share a single call-graph walk."""
    for call_node in _iter_calls_crossing_closures(body):
        callee = _py_call_callee_text(call_node)
        line = call_node.start_point[0] + 1
        if _NESTED_LOOP_RE.search(callee):
            _log.warning(
                "nested-event-loop: %s::%s calls %s at line %d inside a running loop",
                rel,
                fqname,
                callee,
                line,
            )
            out.append(
                ArchSuggestion(
                    file=rel,
                    line=line,
                    category="nested-event-loop",
                    severity="warning",
                    message=(
                        f"{fqname}: `{callee}` at line {line} is reachable "
                        f"inside this `async def` -- a coroutine already "
                        f"runs on a loop, so this raises RuntimeError "
                        f"('cannot be called from a running event loop')"
                    ),
                    detail=(
                        "await the coroutine directly instead of driving a "
                        "second loop from inside a running one"
                    ),
                    symref=f"{rel}::{fqname}",
                )
            )
            continue
        label = _blocking_label(callee)
        if label is None:
            continue
        if _enclosed_by_executor_dispatch(call_node, func_node):
            continue
        _log.warning(
            "blocking-call-in-async: %s::%s calls %s (%s) at line %d "
            "without executor dispatch",
            rel,
            fqname,
            callee,
            label,
            line,
        )
        out.append(
            ArchSuggestion(
                file=rel,
                line=line,
                category="blocking-call-in-async",
                severity="warning",
                message=(
                    f"{fqname}: {label} (`{callee}`) at line {line} is "
                    f"reachable inside this `async def` without a "
                    f"run_in_executor/to_thread dispatch -- it blocks the "
                    f"whole event loop for its duration"
                ),
                detail=(
                    "wrap the call in `await loop.run_in_executor(None, ...)` "
                    "or `await asyncio.to_thread(...)`, or use the async-"
                    "native equivalent (asyncio.sleep, an async HTTP client, ...)"
                ),
                symref=f"{rel}::{fqname}",
            )
        )


def _check_zero_awaits(
    rel: str, fqname: str, body: Node, out: list[ArchSuggestion]
) -> None:
    """`async-zero-awaits` (T-0696): an `async def` whose own scope
    contains no `await` expression never actually suspends back to the
    loop."""
    has_await = any(n.type == "await" for n in _iter_own_scope(body))
    if has_await:
        return
    line = body.start_point[0] + 1
    _log.warning("async-zero-awaits: %s::%s has no await in its own scope", rel, fqname)
    out.append(
        ArchSuggestion(
            file=rel,
            line=line,
            category="async-zero-awaits",
            severity="suggestion",
            message=(
                f"{fqname}: this `async def` contains no `await` anywhere "
                f"in its own body -- it never suspends back to the loop"
            ),
            detail=(
                "if nothing in this function is actually awaited, it should "
                "probably be a plain `def` (an async def with zero awaits "
                "also feeds the IO/CPU-bound model-mismatch advisory)"
            ),
            symref=f"{rel}::{fqname}",
        )
    )


def _collect_async_function_names(root: Node) -> set[str]:
    """Bare names of every `async def` function/method defined anywhere in
    the module -- the corpus `_check_unawaited_coroutines` matches a bare
    call statement's callee (raw + last dotted segment) against, since a
    coroutine call is commonly referenced as a bound-method attribute
    (`self.foo()`) but declared as a bare name (`async def foo`)."""
    names: set[str] = set()
    for func_node, _prefix, fname in _iter_py_functions(root):
        if _is_async_def(func_node):
            names.add(fname)
    return names


def _check_unawaited_coroutines(
    rel: str, fqname: str, body: Node, async_names: set[str], out: list[ArchSuggestion]
) -> None:
    """`unawaited-coroutine` (T-0696): a `call` node used as a BARE
    statement (its immediate parent is a `block` -- tree-sitter-python
    does not wrap a statement-level call in its own node, unlike an
    assignment/`return`/argument position) naming a function this module
    itself declares `async def` -- neither awaited (an `await` expression
    is a different parent shape), gathered (a coroutine passed as an
    ARGUMENT to `asyncio.gather`/etc. has an `argument_list` parent, not
    `block`), nor stored/returned (`assignment`/`return_statement` parents
    are excluded the same way) -- the coroutine object this produces
    silently never runs its body."""
    for call_node in _iter_own_scope(body):
        if call_node.type != "call" or call_node.parent is None:
            continue
        if call_node.parent.type != "block":
            continue
        callee = _py_call_callee_text(call_node)
        bare = callee.rsplit(".", 1)[-1] if "." in callee else callee
        if callee not in async_names and bare not in async_names:
            continue
        line = call_node.start_point[0] + 1
        _log.warning(
            "unawaited-coroutine: %s::%s calls %s at line %d without await",
            rel,
            fqname,
            callee,
            line,
        )
        out.append(
            ArchSuggestion(
                file=rel,
                line=line,
                category="unawaited-coroutine",
                severity="warning",
                message=(
                    f"{fqname}: `{callee}(...)` at line {line} calls an "
                    f"`async def` function but the result is neither "
                    f"awaited, gathered, nor stored -- its body never runs"
                ),
                detail=(
                    "await the call directly, pass it to asyncio.gather/"
                    "create_task, or store the coroutine object if it is "
                    "genuinely deferred -- a bare call statement drops it"
                ),
                symref=f"{rel}::{fqname}",
            )
        )


# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_blocking_call_in_async_fires_on_time_sleep  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_blocking_call_in_async_does_not_fire_via_to_thread  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_nested_event_loop_fires_on_asyncio_run_inside_coroutine  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_nested_event_loop_does_not_fire_at_top_level_sync_code  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_unawaited_coroutine_fires_on_bare_call_statement  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_unawaited_coroutine_does_not_fire_when_awaited_or_stored  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_async_zero_awaits_fires_on_no_await_body  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestAsyncEventLoopHazards.test_async_zero_awaits_does_not_fire_when_awaiting  # noqa: E501
# frob:waive COV001 reason="docs/modules/arch.md is out of T-0696's declared \
# scope (src/frob/arch/**, tests/unit/test_arch.py alone); docs follow-up \
# filed as T-0914, this waiver clears once that lands"
def _check_async_event_loop_hazards(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """Run all four async event-loop hazard detectors (this module's
    docstring) over one parsed python file's functions/methods (T-0696)."""
    t = cast("Tree", tree)
    async_names = _collect_async_function_names(t.root_node)
    for func_node, class_prefix, fname in _iter_py_functions(t.root_node):
        body = _child(func_node, "body")
        if body is None:
            continue
        fqname = f"{class_prefix}{fname}"
        _check_unawaited_coroutines(rel, fqname, body, async_names, out)
        if not _is_async_def(func_node):
            continue
        _check_blocking_and_nested_loop(rel, fqname, func_node, body, out)
        _check_zero_awaits(rel, fqname, body, out)
