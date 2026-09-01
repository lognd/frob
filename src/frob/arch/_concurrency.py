"""Structural fork/pool hazard checks (T-0695): call-graph reachability
signals for the fork/thread/pipe deadlock shapes that cost this repo a
6-hour CI hang (T-0265/T-0581, docs/audits/perf.md H3). Every detector here
is a FAIL-CLOSED, syntactic co-occurrence heuristic over one parsed python
file -- it does not trace runtime ordering (mp_context, submit-before-open,
lock state) the way T-0581's actual fix reasons about; it flags the
STRUCTURAL shape that made the bug possible in the first place, exactly the
"advisory on opaque dispatch" posture the ticket calls for. A function that
is provably safe today still trips the check if it keeps the structural
co-occurrence in one body (this repo's own `_run_combined_jobs`, though
runtime-fixed by T-0581, tripped it until T-0767 hoisted each pool's
construction into its own helper): like every other `frob.arch` category
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
  `Thread(target=f)`) AND whose dispatch site also passed it the
  dispatcher's OWN pool/thread object (`pool.submit(f, pool)`, `Thread(
  target=f, args=(t,))` where `t` is the `Thread` being constructed), and
  whose OWN body calls `.join()`/`.shutdown()`/`.close()` on that SAME
  object -- a worker blocking on the very dispatcher that is running it.
  (T-3571: narrowed to require this correlation -- a dispatched function
  calling `.shutdown()`/`.close()`/`.join()` on an unrelated object it was
  merely also handed, such as `_socketd.py::_idle_monitor` shutting down
  the `server` it polls, is the standard safe pattern, not a self-join.)
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


def _receiver_text(callee_text: str) -> str | None:
    """The object expression a dotted call is made on (`pool` from
    `pool.submit(...)`) -- `None` for a bare-name callee with no
    receiver."""
    if "." not in callee_text:
        return None
    return callee_text.rsplit(".", 1)[0]


def _assigned_name(call_node: Node) -> str | None:
    """The variable name a call node's result is bound to, when the call
    is the direct right-hand side of a plain `name = Thread(...)`
    assignment -- `None` otherwise (unassigned, tuple-unpacked, or an
    attribute/subscript target)."""
    parent = call_node.parent
    if parent is None or parent.type != "assignment":
        return None
    left = _child(parent, "left")
    if left is None or left.type != "identifier":
        return None
    return _node_text(left)


def _call_arg_texts(call_node: Node) -> list[str]:
    """Raw source text of every positional/keyword argument at a call
    site, in source order -- used to test whether the dispatcher's own
    receiver object was passed through to the dispatched callable. A
    keyword argument's `tuple`/`list` value (`Thread(..., args=(server,
    stop))`) is flattened to its own elements' text rather than the
    tuple's whole text, since that is how `Thread(target=f, args=(...))`
    actually threads positional arguments through to `f` -- without this,
    `args=(t,)` never textually equals the bare receiver name `t`."""
    args = _child(call_node, "arguments")
    if args is None:
        return []
    out: list[str] = []
    for a in args.named_children:
        if a.type == "keyword_argument":
            val = _child(a, "value")
            if val is not None and val.type in ("tuple", "list"):
                out.extend(_node_text(e) for e in val.named_children)
            else:
                out.append(_node_text(val) if val is not None else "")
        else:
            out.append(_node_text(a))
    return out


class _DispatchRecord:
    """One submit/start dispatch site: the candidate callee `names` it
    targets, and `self_pass_names` -- the subset of the dispatcher's own
    args whose text equals the dispatch call's own `receiver` object
    (`pool.submit(worker, pool)`'s `pool` argument, or a `Thread(target=f,
    args=(monitor,))`'s `args` tuple element matching the assigned `Thread`
    variable). Non-empty `self_pass_names` is the correlation signal
    `_check_self_join` requires: the dispatcher does not just target the
    function, it also hands the function ITS OWN pool/thread object back,
    which is what makes a same-named join/shutdown/close inside that
    function a genuine self-join rather than an unrelated foreign call
    (T-3571 -- `_idle_monitor` is dispatched via `Thread(target=_idle_
    monitor, args=(server, ...))` but shuts down `server`, never the
    dispatching `Thread`, so its `self_pass_names` is empty and it must
    not fire)."""

    __slots__ = ("names", "self_pass_names")

    def __init__(self, names: set[str], self_pass_names: set[str]) -> None:
        """Store the dispatch site's candidate callee `names` and its
        `self_pass_names` correlation set (see class docstring)."""
        self.names = names
        self.self_pass_names = self_pass_names


def _dispatch_records(root: Node) -> list[_DispatchRecord]:
    """Every submit/start dispatch site in the module as a
    `_DispatchRecord` -- the corpus `_check_self_join` uses both to find
    whether a function is dispatched at all, and, per T-3571, whether the
    dispatcher's own pool/thread object was also passed to it (see
    `_DispatchRecord`)."""
    records: list[_DispatchRecord] = []
    for call_node in _iter_calls(root):
        callee = _py_call_callee_text(call_node)
        if _SUBMIT_LIKE_RE.search(callee):
            names = set(_first_arg_names(call_node))
            if not names:
                continue
            receiver = _receiver_text(callee)
            arg_texts = _call_arg_texts(call_node)[1:]  # skip the target itself
            self_pass = {t for t in arg_texts if receiver is not None and t == receiver}
            records.append(_DispatchRecord(names, self_pass))
        elif _THREAD_CTOR_RE.search(callee):
            names = set(_target_kwarg_names(call_node))
            if not names:
                continue
            receiver = _assigned_name(call_node)
            arg_texts = _call_arg_texts(call_node)
            self_pass = {t for t in arg_texts if receiver is not None and t == receiver}
            records.append(_DispatchRecord(names, self_pass))
    return records


def _param_names(func_node: Node) -> set[str]:
    """A function definition's own parameter names, bare identifiers only
    -- used to test whether a join/shutdown/close call's receiver is one
    of `fqname`'s own parameters (T-3571's correlation requirement)."""
    params = _child(func_node, "parameters")
    if params is None:
        return set()
    return {_node_text(p) for p in params.named_children if p.type == "identifier"}


# frob:waive ARCH001 reason="two related checks (pool-inside-pool, fork-after-threads) sharing one pass's classified call lists (process_pool/thread_pool/thread_ctor/thread_start/fork); splitting either check into a helper would require threading all five derived lists across a new boundary without reducing the shared classification they both read"  # noqa: E501
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
    dispatch_records: list[_DispatchRecord],
    param_names: set[str],
    out: list[ArchSuggestion],
) -> None:
    """`self-join-deadlock`: `fqname`'s own body calls `.join()`/
    `.shutdown()`/`.close()` on some pool/thread object, `fqname` (or its
    bare name) is itself submitted/started as a pool/thread task somewhere
    in the module, AND (T-3571 narrowing) that same dispatch site also
    passed `fqname` its OWN dispatcher object -- so the join/shutdown/close
    receiver, resolved through `fqname`'s own parameters, correlates back
    to the dispatching pool/thread rather than to an unrelated domain
    object `fqname` happens to also hold (`_DispatchRecord.self_pass_
    names`/`_param_names`). Without this correlation, ANY function that is
    both dispatched as a task and calls `.shutdown()`/`.close()`/`.join()`
    on some parameter fires regardless of whether that parameter is
    actually the dispatcher -- the false positive this ticket fixes
    (`_idle_monitor` is dispatched via `Thread(target=_idle_monitor,
    args=(server, ...))` and shuts down `server`, never the dispatching
    `Thread`)."""
    matching = [r for r in dispatch_records if fname in r.names or fqname in r.names]
    if not matching:
        return
    correlated_names = {n for r in matching for n in r.self_pass_names} & param_names
    if not correlated_names:
        return
    joins = [
        (t, ln)
        for c, t, ln in calls
        if (
            _JOIN_CALL_RE.search(c)
            or _SHUTDOWN_CALL_RE.search(c)
            or _CLOSE_CALL_RE.search(c)
        )
        and _receiver_text(c) in correlated_names
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


# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_fork_after_threads_fires_when_fork_follows_thread_start  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_fork_before_threads_does_not_fire  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_pipe_wait_deadlock_fires_without_communicate  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_pipe_wait_deadlock_does_not_fire_with_communicate  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_self_join_deadlock_fires_when_dispatched_task_joins_its_pool  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_self_join_deadlock_does_not_fire_on_undispatched_join  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_self_join_deadlock_does_not_fire_on_foreign_object_shutdown  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_self_join_deadlock_fires_on_genuine_thread_self_join  # noqa: E501
# frob:tests tests/unit/arch_suite/test_concurrency.py::TestForkPoolHazards.test_self_join_deadlock_discharges_on_real_repo_socketd_idle_monitor  # noqa: E501
def _check_fork_pool_hazards(tree: object, rel: str, out: list[ArchSuggestion]) -> None:
    """Run all four fork/pool hazard detectors (this module's docstring)
    over one parsed python file's functions/methods. `dispatched` (the
    submit/target corpus for `self-join-deadlock`) is built once over the
    whole file since a submit site and its callee can live in different
    functions."""
    t = cast("Tree", tree)
    dispatch_records = _dispatch_records(t.root_node)
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
        _check_self_join(
            rel, fqname, fname, calls, dispatch_records, _param_names(func_node), out
        )
