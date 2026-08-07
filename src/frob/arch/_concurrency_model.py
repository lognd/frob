"""Concurrency model-mismatch advisory (T-0698, child 5 of the T-0693
concurrency-hazard umbrella, the user's seem-IO-bound/seem-CPU-bound
mandate): classify each function as IO-BOUND, CPU-BOUND, or MIXED/UNKNOWN
from curated call/loop evidence in its own scope, then flag when a
function's chosen dispatch EXECUTOR mismatches its classification. Same
fail-closed, non-runtime-tracing posture as this package's other
concurrency-hazard checks (`frob.arch._lock_ordering`, T-0694;
`frob.arch._concurrency`, T-0695; `frob.arch._async_hazards`, T-0696;
`frob.arch._shared_state_race`, T-0697): a finding flags a STRUCTURAL shape
that makes the mismatch likely, not a runtime measurement.

MODEL (T-0698):

1. CLASSIFICATION (`_classify_function`): a function is IO-BOUND when its
   own scope (`_iter_own_scope`) contains at least one curated IO call
   (sockets, files, `requests`/`urllib`/http, `subprocess`, or a database
   `execute`/`cursor` call -- `_is_io_call`, reusing
   `frob.arch._async_hazards`'s `_BLOCKING_CALL_TABLE`/`_OPEN_BUILTIN_RE`
   patterns where they already cover this ticket's own "http/subprocess/
   files" wording rather than re-curating the same names twice) AND no
   `for`/`while` loop anywhere in its own scope; CPU-BOUND when it
   contains a loop but no curated IO call; anything else (both present,
   or neither) is MIXED/UNKNOWN and produces NO advisory at all (T-0332's
   noise-discipline precedent every other `frob.arch` category already
   follows: an advisory only fires on a CONFIDENT classification).

2. EXECUTOR-DISPATCH BINDING (`_executor_bindings`): a name bound (via a
   plain assignment or a `with <ctor>() as name:` clause) to a
   `ThreadPoolExecutor(...)` or `ProcessPoolExecutor(...)` construction is
   tracked as that kind of executor for the rest of the module; every
   `<name>.submit(...)`/`<name>.map(...)` call on a tracked name resolves
   the dispatched callee (via `frob.arch._concurrency._first_arg_names`'s
   own raw+bare-segment convention) to that executor's kind.

3. GIL-BOUND ADVISORY (`gil-bound-in-threadpool`): a CPU-BOUND function
   dispatched to a THREAD-kind executor -- Python's GIL means CPU-bound
   work submitted to a thread pool does not actually parallelize; the
   finding names the loop line(s) that drove the CPU-bound classification
   as evidence and suggests `ProcessPoolExecutor` or a native extension.

4. IPC-OVERHEAD ADVISORY (`ipc-overhead-in-processpool`): a TRIVIALLY
   SMALL (own-scope body of `_TRIVIAL_BODY_LINE_CEILING` lines or fewer)
   IO-BOUND function dispatched to a PROCESS-kind executor -- the
   per-task IPC/pickling overhead of a process pool dominates a tiny
   IO-bound task; the finding names the dispatched IO call site as
   evidence and suggests a thread pool or `asyncio` instead.

MODEL-LIMIT DISCLOSURE (matching this package's house convention): same-
module only (an executor binding tracked via a local name, not through a
factory function or attribute); "arithmetic-dense" is approximated as
"contains a loop with no IO call" -- a loop that itself only calls IO
(e.g. iterating a socket's lines) is classified IO-BOUND instead (IO
dominance wins whenever both are present is deliberately NOT this
module's rule -- both-present is MIXED/UNKNOWN, per step 1 -- so a mixed
loop-plus-IO function never fires either advisory, avoiding a false
GIL-bound claim on genuinely-IO work that happens to loop). The two
remaining advisory shapes this ticket's own text also names --
sequential-independent-awaits-should-gather, and async-def-with-zero-
awaits -- are NOT duplicated here: `async-zero-awaits` already exists as
its own `frob.arch._async_hazards` category (T-0696, whose own module
docstring cross-references feeding this ticket's advisory) and firing it
twice under two names would be the exact duplication this repo's own
house rule forbids; the sequential-awaits-should-gather shape needs an
independence proof between two `await` expressions this ticket's own
normalized-model scope does not yet support and is filed as a follow-up
rather than approximated unsoundly (see this ticket's Done report).

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

from frob.arch._async_hazards import _BLOCKING_CALL_TABLE, _OPEN_BUILTIN_RE
from frob.arch._concurrency import _first_arg_names
from frob.arch._models import ArchSuggestion
from frob.arch._python import _iter_own_scope, _iter_py_functions, _py_call_callee_text
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text
from frob.logging import get_logger

_log = get_logger(__name__)

#: Additional curated IO calls this ticket's own "sockets/files/http/
#: subprocess/db" wording names that `_async_hazards._BLOCKING_CALL_TABLE`
#: does not already cover (that table is scoped to BLOCKING calls inside
#: an `async def`, not a general IO-boundness classifier) -- socket
#: send/recv and a database cursor's `execute`.
_EXTRA_IO_CALL_RE = re.compile(
    r"\.(?:recv|recvfrom|send|sendto|sendall|connect|accept|read|write|execute)$"
)

_THREAD_POOL_CTOR_RE = re.compile(r"(?:^|\.)ThreadPoolExecutor$")
_PROCESS_POOL_CTOR_RE = re.compile(r"(?:^|\.)ProcessPoolExecutor$")
_SUBMIT_LIKE_RE = re.compile(r"\.(?:submit|map)$")

#: A dispatched function whose own-scope body is this many lines or fewer
#: counts as "trivially small" for the IPC-overhead advisory (T-0698).
_TRIVIAL_BODY_LINE_CEILING = 3


def _iter_calls(node: Node) -> Iterator[Node]:
    """Every `call` node in `node`'s full subtree, without stopping at a
    nested `function_definition`/`class_definition` boundary -- mirrors
    `frob.arch._concurrency._iter_calls`'s own reachability rationale,
    needed here to find executor-construction/dispatch sites regardless
    of lexical nesting."""
    if node.type == "call":
        yield node
    for c in node.children:
        yield from _iter_calls(c)


def _is_io_call(callee: str) -> bool:
    """Whether a call's dotted callee TEXT matches this module's curated
    IO table (T-0698, this module's docstring step 1): the shared
    `_async_hazards._BLOCKING_CALL_TABLE` patterns, the bare `open(...)`
    builtin, or this module's own socket/db additions."""
    if any(pattern.search(callee) for pattern, _ in _BLOCKING_CALL_TABLE):
        return True
    if _OPEN_BUILTIN_RE.match(callee):
        return True
    return bool(_EXTRA_IO_CALL_RE.search(callee))


class _FunctionClassification:
    """One function's classification inputs and result (T-0698): `kind` is
    `"io"`, `"cpu"`, or `None` (mixed/unknown, no advisory ever fires);
    `loop_lines`/`io_call_lines` are the evidence lines named in a
    finding's message."""

    __slots__ = ("symref", "fname", "kind", "loop_lines", "io_call_lines", "body_lines")

    def __init__(
        self,
        symref: str,
        fname: str,
        kind: str | None,
        loop_lines: list[int],
        io_call_lines: list[int],
        body_lines: int,
    ) -> None:
        """Bind this function's symref, bare name, classification kind,
        evidence line lists, and own-scope body line span."""
        self.symref = symref
        self.fname = fname
        self.kind = kind
        self.loop_lines = loop_lines
        self.io_call_lines = io_call_lines
        self.body_lines = body_lines


def _classify_function(body: Node) -> tuple[str | None, list[int], list[int], int]:
    """Classify one function's own-scope body (T-0698, this module's
    docstring step 1): `(kind, loop_lines, io_call_lines, body_lines)`.
    `kind` is `"io"` (IO calls present, no loop), `"cpu"` (loop present,
    no IO calls), or `None` (both or neither -- MIXED/UNKNOWN, never
    advisory-eligible)."""
    loop_lines: list[int] = []
    io_call_lines: list[int] = []
    for node in _iter_own_scope(body):
        if node.type in ("for_statement", "while_statement"):
            loop_lines.append(node.start_point[0] + 1)
        elif node.type == "call":
            callee = _py_call_callee_text(node)
            if _is_io_call(callee):
                io_call_lines.append(node.start_point[0] + 1)
    body_lines = body.end_point[0] - body.start_point[0] + 1
    if io_call_lines and not loop_lines:
        return "io", loop_lines, io_call_lines, body_lines
    if loop_lines and not io_call_lines:
        return "cpu", loop_lines, io_call_lines, body_lines
    return None, loop_lines, io_call_lines, body_lines


def _bound_ctor_name(rhs: Node) -> str | None:
    """`"thread"`/`"process"` when `rhs` is a bare `ThreadPoolExecutor(...)`/
    `ProcessPoolExecutor(...)` call, else `None` (T-0698, this module's
    docstring step 2)."""
    if rhs.type != "call":
        return None
    callee = _py_call_callee_text(rhs)
    if _THREAD_POOL_CTOR_RE.search(callee):
        return "thread"
    if _PROCESS_POOL_CTOR_RE.search(callee):
        return "process"
    return None


def _executor_bindings(root: Node) -> dict[str, str]:
    """Every module-wide `name -> "thread"|"process"` binding (T-0698, this
    module's docstring step 2): a plain `name = ThreadPoolExecutor(...)`/
    `ProcessPoolExecutor(...)` assignment, or a `with ThreadPoolExecutor()
    as name:`/`with ProcessPoolExecutor() as name:` clause, anywhere in
    the module (not scoped to `_iter_own_scope`, since an executor is
    commonly bound at module or function level and consumed elsewhere)."""
    bindings: dict[str, str] = {}
    for node in _walk_all(root):
        if node.type == "assignment":
            left = _child(node, "left")
            right = _child(node, "right")
            if left is not None and left.type == "identifier" and right is not None:
                kind = _bound_ctor_name(right)
                if kind is not None:
                    bindings[_node_text(left)] = kind
        elif node.type == "with_item":
            child = node.named_children[0] if node.named_children else node
            if child.type == "as_pattern" and len(child.named_children) >= 2:
                ctor = child.named_children[0]
                target = child.named_children[1]
                # tree-sitter-python wraps the `as X` target in its own
                # `as_pattern_target` node, one level above the bare
                # identifier.
                if target.type == "as_pattern_target" and target.named_children:
                    target = target.named_children[0]
                kind = _bound_ctor_name(ctor)
                if kind is not None and target.type == "identifier":
                    bindings[_node_text(target)] = kind
    return bindings


# frob:invariant terminates reason="recurses only into a direct tree-sitter child one \
# edge below the current node; a lexical prover cannot see that the child accessor is \
# structurally smaller without dataflow" measure="tree-sitter AST depth under node, \
# finite per parse"
def _walk_all(node: Node) -> Iterator[Node]:
    """Every node in `node`'s full subtree, descending through every
    boundary (functions, classes, nested scopes) -- used only by
    `_executor_bindings`, which deliberately wants module-wide bindings,
    unlike this module's other per-function walks."""
    yield node
    for c in node.children:
        yield from _walk_all(c)


def _dispatch_kinds_for_name(
    fname: str, calls: list[Node], bindings: dict[str, str]
) -> set[str]:
    """Every executor `kind` (`"thread"`/`"process"`) `fname` is dispatched
    to ANYWHERE in the module (T-0698, this module's docstring step 2):
    every `<bound-name>.submit(...)`/`<bound-name>.map(...)` call whose
    first-argument name (raw or bare-segment) matches `fname`, resolved
    against `bindings`."""
    kinds: set[str] = set()
    for call_node in calls:
        callee = _py_call_callee_text(call_node)
        if not _SUBMIT_LIKE_RE.search(callee):
            continue
        receiver = callee.rsplit(".", 1)[0]
        kind = bindings.get(receiver)
        if kind is None:
            continue
        if fname in _first_arg_names(call_node):
            kinds.add(kind)
    return kinds


def _gil_bound_finding(rel: str, c: _FunctionClassification) -> ArchSuggestion:
    """The `gil-bound-in-threadpool` `ArchSuggestion` (and matching log
    line) for one CPU-bound function dispatched to a thread pool."""
    line = c.loop_lines[0]
    _log.warning(
        "gil-bound-in-threadpool: %s is CPU-bound (loop at line %d) but "
        "dispatched to a ThreadPoolExecutor",
        c.symref,
        line,
    )
    return ArchSuggestion(
        file=rel,
        line=line,
        category="gil-bound-in-threadpool",
        severity="suggestion",
        message=(
            f"{c.symref}: classified CPU-bound (loop at line {line}, no "
            f"IO call in its own body) but is submitted to a "
            f"ThreadPoolExecutor -- the GIL means this does not actually "
            f"parallelize"
        ),
        detail=(
            "use a ProcessPoolExecutor (or a native extension) for "
            "CPU-bound work instead of a thread pool"
        ),
        symref=c.symref,
    )


def _ipc_overhead_finding(rel: str, c: _FunctionClassification) -> ArchSuggestion:
    """The `ipc-overhead-in-processpool` `ArchSuggestion` (and matching log
    line) for one trivially-small IO-bound function dispatched to a
    process pool."""
    line = c.io_call_lines[0]
    _log.warning(
        "ipc-overhead-in-processpool: %s is a trivially small IO-bound "
        "task (IO call at line %d, %d body line(s)) dispatched to a "
        "ProcessPoolExecutor",
        c.symref,
        line,
        c.body_lines,
    )
    return ArchSuggestion(
        file=rel,
        line=line,
        category="ipc-overhead-in-processpool",
        severity="suggestion",
        message=(
            f"{c.symref}: classified IO-bound (IO call at line {line}) "
            f"and trivially small ({c.body_lines} body line(s)) but is "
            f"submitted to a ProcessPoolExecutor -- per-task IPC/pickling "
            f"overhead dominates a task this small"
        ),
        detail=(
            "use a ThreadPoolExecutor or asyncio for a small IO-bound "
            "task instead of a process pool"
        ),
        symref=c.symref,
    )


# frob:ticket T-0698
# frob:tests tests/unit/test_arch.py::TestConcurrencyModelMismatch.test_cpu_bound_loop_in_threadpool_fires_gil_bound  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestConcurrencyModelMismatch.test_io_bound_socket_read_in_threadpool_does_not_fire  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestConcurrencyModelMismatch.test_trivial_io_task_in_processpool_fires_ipc_overhead  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestConcurrencyModelMismatch.test_mixed_loop_and_io_function_never_fires_either_advisory  # noqa: E501
def _check_concurrency_model_mismatch(
    tree: object, rel: str, out: list[ArchSuggestion]
) -> None:
    """Run the concurrency model-mismatch check (this module's docstring)
    over one parsed python file: classify every function, resolve every
    executor binding and dispatch site, then report `gil-bound-in-
    threadpool` for a CPU-bound function dispatched to a thread pool and
    `ipc-overhead-in-processpool` for a trivially-small IO-bound function
    dispatched to a process pool (T-0698)."""
    t = cast("Tree", tree)
    root = t.root_node
    bindings = _executor_bindings(root)
    if not bindings:
        return
    all_calls = list(_iter_calls(root))

    for func_node, class_prefix, fname in _iter_py_functions(root):
        body = _child(func_node, "body")
        if body is None:
            continue
        symref = f"{rel}::{class_prefix}{fname}" if class_prefix else f"{rel}::{fname}"
        kind, loop_lines, io_call_lines, body_lines = _classify_function(body)
        if kind is None:
            continue
        dispatch_kinds = _dispatch_kinds_for_name(fname, all_calls, bindings)
        classification = _FunctionClassification(
            symref, fname, kind, loop_lines, io_call_lines, body_lines
        )
        if kind == "cpu" and "thread" in dispatch_kinds:
            out.append(_gil_bound_finding(rel, classification))
        elif (
            kind == "io"
            and body_lines <= _TRIVIAL_BODY_LINE_CEILING
            and "process" in dispatch_kinds
        ):
            out.append(_ipc_overhead_finding(rel, classification))
