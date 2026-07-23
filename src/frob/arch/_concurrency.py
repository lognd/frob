"""Structural fork/pool hazard checks (T-0695): call-graph reachability
signals for the fork/thread/pipe deadlock shapes that cost this repo a
6-hour CI hang (T-0265/T-0581, docs/audits/perf.md H3). Every detector here
is a FAIL-CLOSED, syntactic co-occurrence heuristic over one parsed python
file -- it does not trace runtime ordering (mp_context, submit-before-open,
lock state) the way T-0581's actual fix reasons about; it flags the
STRUCTURAL shape that made the bug possible in the first place, exactly the
"advisory on opaque dispatch" posture the ticket calls for. A function that
is provably safe today (like this repo's own `_run_combined_jobs`, fixed by
T-0581) still trips the check: like every other `frob.arch` category
(T-0101's unwaivable advisory channel), a finding here is never build-
blocking and a `frob:waive` naming it is flagged as ineffective
(WAIVE002) rather than honored -- the finding simply stays visible in
`frob check`'s frob-arch summary permanently, which is the intended
disclosure for an opaque-dispatch shape a static scan cannot fully
resolve. See docs/modules/arch.md's "fork/pool hazards" section.

Four detectors, one shared per-function call scan:

- `pool-inside-pool`: a `ProcessPoolExecutor`/`multiprocessing.Pool`
  construction reachable in the same function as a `ThreadPoolExecutor`
  construction or a `threading.Thread(...).start()` pair (the T-0265 field
  bug's exact shape: forking while a sibling thread may hold an
  interpreter-internal lock).
- `fork-after-threads`: an explicit fork syscall (or a `fork`-start-method
  context/`set_start_method`) reachable AFTER a `Thread(...).start()` on
  the same function's source-line order.
- `pipe-wait-deadlock`: a `Popen` construction with a `PIPE`
  stdout/stderr, followed by a bare `.wait()` with no `.communicate()`
  anywhere in the function -- the classic pipe-fill-then-wait deadlock on
  unbounded output.
- `self-join-deadlock`: a function that is itself submitted/started as a
  pool/thread task (`.submit(f)`, `.map(f, ...)`, `.apply_async(f, ...)`,
  `Thread(target=f)`) and whose OWN body calls `.join()`/`.shutdown()`/
  `.close()` on some pool/thread object -- a worker blocking on the very
  dispatcher that is running it.
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

#: Construction of a CPU-forking pool: `ProcessPoolExecutor`, or a
#: `Pool` from `multiprocessing` (any alias) -- deliberately excludes
#: `ThreadPool` (its last dotted segment is `ThreadPool`, not `Pool`, so it
#: never matches this pattern).
_PROCESS_POOL_CTOR_RE = re.compile(r"(?:^|\.)(?:ProcessPoolExecutor|Pool)$")
_THREAD_POOL_CTOR_RE = re.compile(r"(?:^|\.)ThreadPoolExecutor$")
_THREAD_CTOR_RE = re.compile(r"(?:^|\.)Thread$")
_START_CALL_RE = re.compile(r"\.start$")
_FORK_CALL_RE = re.compile(r"(?:^|\.)fork$")
_FORK_CONTEXT_RE = re.compile(r"(?:^|\.)(?:get_context|set_start_method)$")
_POPEN_CTOR_RE = re.compile(r"(?:^|\.)Popen$")
_WAIT_CALL_RE = re.compile(r"\.wait$")
_COMMUNICATE_CALL_RE = re.compile(r"\.communicate$")
_JOIN_CALL_RE = re.compile(r"\.join$")
_SHUTDOWN_CALL_RE = re.compile(r"\.shutdown$")
_CLOSE_CALL_RE = re.compile(r"\.close$")
_SUBMIT_LIKE_RE = re.compile(r"\.(?:submit|map|apply_async)$")
_TARGET_KWARG_RE = re.compile(r"target\s*=\s*([A-Za-z_][A-Za-z0-9_.]*)")


def _iter_calls(node: Node) -> Iterator[Node]:
    """Every `call` node in `node`'s full subtree, without stopping at a
    nested `function_definition`/`class_definition` boundary -- unlike
    `_py_collect_body_events`'s flattened-events walk, these detectors
    deliberately want reachability THROUGH nested closures and `with`
    bodies too (a `def _worker(): ...` defined and dispatched inside the
    same outer function is exactly the shape T-0265 hit)."""
    if node.type == "call":
        yield node
    for c in node.children:
        yield from _iter_calls(c)


def _first_arg_names(call_node: Node) -> list[str]:
    """Candidate callee names a `.submit`/`.map`/`.apply_async` call's
    first positional argument names -- the raw dotted text (`self._worker`)
    and its bare last segment (`_worker`), since a submitted callable is
    often referenced as a bound-method attribute but defined as a bare
    function/method name."""
    args = _child(call_node, "arguments")
    if args is None:
        return []
    first = next(iter(args.named_children), None)
    if first is None:
        return []
    text = _node_text(first)
    names = [text]
    if "." in text:
        names.append(text.rsplit(".", 1)[-1])
    return names


def _target_kwarg_names(call_node: Node) -> list[str]:
    """Candidate callee names from a `Thread(target=X)` construction's
    `target=` keyword argument, same raw/bare-segment pair as
    `_first_arg_names`."""
    args = _child(call_node, "arguments")
    if args is None:
        return []
    match = _TARGET_KWARG_RE.search(_node_text(args))
    if match is None:
        return []
    text = match.group(1)
    names = [text]
    if "." in text:
        names.append(text.rsplit(".", 1)[-1])
    return names


def _dispatched_callee_names(root: Node) -> set[str]:
    """Every callee name (raw + bare-segment) submitted/started as a
    pool/thread task ANYWHERE in the module -- the corpus
    `_check_self_join` compares each function's own name against."""
    names: set[str] = set()
    for call_node in _iter_calls(root):
        callee = _py_call_callee_text(call_node)
        if _SUBMIT_LIKE_RE.search(callee):
            names.update(_first_arg_names(call_node))
        elif _THREAD_CTOR_RE.search(callee):
            names.update(_target_kwarg_names(call_node))
    return names


def _check_pool_inside_pool(
    rel: str, fqname: str, calls: list[tuple[str, str, int]], out: list[ArchSuggestion]
) -> None:
    """`pool-inside-pool`/`fork-after-threads` for one function's flattened
    `(callee, full_text, line)` calls -- both reason about the same
    process-pool-vs-thread co-occurrence signal, just gated on presence
    (pool-inside-pool) vs. line-order (fork-after-threads)."""
    process_pool = [(t, ln) for c, t, ln in calls if _PROCESS_POOL_CTOR_RE.search(c)]
    thread_pool = [(t, ln) for c, t, ln in calls if _THREAD_POOL_CTOR_RE.search(c)]
    thread_ctor = [(t, ln) for c, t, ln in calls if _THREAD_CTOR_RE.search(c)]
    thread_start = [(t, ln) for c, t, ln in calls if _START_CALL_RE.search(c)]
    has_thread_pool = bool(thread_pool) or bool(thread_ctor and thread_start)
    if process_pool and has_thread_pool:
        pp_line = process_pool[0][1]
        tp_line = (thread_pool or thread_ctor)[0][1]
        _log.warning(
            "pool-inside-pool: %s::%s process-pool at line %d alongside "
            "thread-pool at line %d",
            rel,
            fqname,
            pp_line,
            tp_line,
        )
        out.append(
            ArchSuggestion(
                file=rel,
                line=min(pp_line, tp_line),
                category="pool-inside-pool",
                severity="warning",
                message=(
                    f"{fqname}: a process-pool/multiprocessing construction "
                    f"(line {pp_line}) is reachable alongside a thread-pool/"
                    f"thread construction (line {tp_line}) -- forking while "
                    f"a sibling thread may hold an interpreter-internal lock "
                    f"can hang forever (T-0265)"
                ),
                detail=(
                    "submit the process pool's work (or open it) BEFORE any "
                    "thread pool/thread starts on this path, and use "
                    "mp_context=spawn regardless of ordering"
                ),
                symref=f"{rel}::{fqname}",
            )
        )
    fork = [
        (t, ln)
        for c, t, ln in calls
        if _FORK_CALL_RE.search(c) or (_FORK_CONTEXT_RE.search(c) and "fork" in t)
    ]
    if fork and thread_ctor and thread_start:
        earliest_start = min(ln for _, ln in thread_start)
        late_forks = [(t, ln) for t, ln in fork if ln > earliest_start]
        if late_forks:
            fork_line = late_forks[0][1]
            _log.warning(
                "fork-after-threads: %s::%s fork at line %d after thread "
                "start at line %d",
                rel,
                fqname,
                fork_line,
                earliest_start,
            )
            out.append(
                ArchSuggestion(
                    file=rel,
                    line=fork_line,
                    category="fork-after-threads",
                    severity="warning",
                    message=(
                        f"{fqname}: a fork/fork-start-method call (line "
                        f"{fork_line}) is reachable after a thread was "
                        f"started (line {earliest_start}) on the same path"
                    ),
                    detail=(
                        "fork inherits only the calling thread; a sibling "
                        "thread holding a lock at fork time never releases "
                        "it in the child -- fork before starting threads, "
                        "or use a spawn/forkserver start method"
                    ),
                    symref=f"{rel}::{fqname}",
                )
            )


def _check_pipe_wait(
    rel: str, fqname: str, calls: list[tuple[str, str, int]], out: list[ArchSuggestion]
) -> None:
    """`pipe-wait-deadlock`: a `Popen` with `stdout=PIPE` (or stderr)
    followed by a bare `.wait()` with no `.communicate()` anywhere in the
    same function -- unbounded child output fills the pipe buffer and both
    processes block forever."""
    popen_pipe = [
        (t, ln) for c, t, ln in calls if _POPEN_CTOR_RE.search(c) and "PIPE" in t
    ]
    wait_calls = [(t, ln) for c, t, ln in calls if _WAIT_CALL_RE.search(c)]
    has_communicate = any(_COMMUNICATE_CALL_RE.search(c) for c, _, _ in calls)
    if popen_pipe and wait_calls and not has_communicate:
        popen_line = popen_pipe[0][1]
        wait_line = wait_calls[0][1]
        _log.warning(
            "pipe-wait-deadlock: %s::%s Popen+PIPE at line %d, .wait() at "
            "line %d with no .communicate()",
            rel,
            fqname,
            popen_line,
            wait_line,
        )
        out.append(
            ArchSuggestion(
                file=rel,
                line=popen_line,
                category="pipe-wait-deadlock",
                severity="warning",
                message=(
                    f"{fqname}: Popen with a PIPE stream (line {popen_line}) "
                    f"is followed by .wait() (line {wait_line}) with no "
                    f".communicate() anywhere in the function -- unbounded "
                    f"child output fills the pipe buffer and deadlocks both "
                    f"processes"
                ),
                detail=(
                    "use .communicate() (which drains the pipe while "
                    "waiting) instead of a bare .wait() when a stream is "
                    "piped, or avoid PIPE if output is not consumed"
                ),
                symref=f"{rel}::{fqname}",
            )
        )


def _check_self_join(
    rel: str,
    fqname: str,
    fname: str,
    calls: list[tuple[str, str, int]],
    dispatched: set[str],
    out: list[ArchSuggestion],
) -> None:
    """`self-join-deadlock`: `fqname`'s own body calls `.join()`/
    `.shutdown()`/`.close()` on some pool/thread object, AND `fqname` (or
    its bare name) is itself submitted/started as a pool/thread task
    somewhere in the module (`dispatched`, from `_dispatched_callee_names`)
    -- a worker task blocking on the very dispatcher that is running it."""
    if fname not in dispatched and fqname not in dispatched:
        return
    joins = [
        (t, ln)
        for c, t, ln in calls
        if _JOIN_CALL_RE.search(c)
        or _SHUTDOWN_CALL_RE.search(c)
        or _CLOSE_CALL_RE.search(c)
    ]
    if not joins:
        return
    join_line = joins[0][1]
    _log.warning(
        "self-join-deadlock: %s::%s is dispatched as a pool/thread task and "
        "calls join/shutdown/close at line %d",
        rel,
        fqname,
        join_line,
    )
    out.append(
        ArchSuggestion(
            file=rel,
            line=join_line,
            category="self-join-deadlock",
            severity="warning",
            message=(
                f"{fqname}: dispatched as a pool/thread task elsewhere in "
                f"this module, but its own body calls join/shutdown/close "
                f"at line {join_line} -- a worker blocking on the "
                f"dispatcher running it deadlocks"
            ),
            detail=(
                "never join/shutdown/close a pool or thread from inside a "
                "task it is running -- signal completion back to the "
                "dispatcher instead and let it join after the task returns"
            ),
            symref=f"{rel}::{fqname}",
        )
    )


# frob:doc docs/modules/arch.md#fork-pool-hazards
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_pool_inside_pool_fires_on_real_repo_run_combined_jobs  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_fork_after_threads_fires_when_fork_follows_thread_start  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_fork_before_threads_does_not_fire  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_pipe_wait_deadlock_fires_without_communicate  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_pipe_wait_deadlock_does_not_fire_with_communicate  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_self_join_deadlock_fires_when_dispatched_task_joins_its_pool  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestForkPoolHazards.test_self_join_deadlock_does_not_fire_on_undispatched_join  # noqa: E501
def _check_fork_pool_hazards(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """Run all four fork/pool hazard detectors (this module's docstring)
    over one parsed python file's functions/methods. `dispatched` (the
    submit/target corpus for `self-join-deadlock`) is built once over the
    whole file since a submit site and its callee can live in different
    functions."""
    t = cast("Tree", tree)
    dispatched = _dispatched_callee_names(t.root_node)
    for func_node, class_prefix, fname in _iter_py_functions(t.root_node):
        body = _child(func_node, "body")
        if body is None:
            continue
        calls = [
            (_py_call_callee_text(c), _node_text(c), c.start_point[0] + 1)
            for c in _iter_calls(body)
        ]
        fqname = f"{class_prefix}{fname}"
        _check_pool_inside_pool(rel, fqname, calls, out)
        _check_pipe_wait(rel, fqname, calls, out)
        _check_self_join(rel, fqname, fname, calls, dispatched, out)
