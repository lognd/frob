"""PERF012: duplicate-identical-subprocess-spawn-within-one-call-path
detector (T-0919) -- the INTERPROCEDURAL sibling of PERF008
(`frob.perf._loop_effects.loop_invariant_effect_violations`).

Motivated by the T-0919 incident: `frob ticket done-report`'s (and `frob
ticket land`'s) internal `_check_gates_summary_fn`/`_check_gate_findings_fn`
closures each independently spawned their OWN full `python -m frob check
--ticket <id>` subprocess -- textually IDENTICAL argv and kwargs -- from the
SAME calling function, serially, doubling an already-slow (~600s-timeout)
foreground cost for output that is fully re-derivable from a single run. No
existing PERF rule caught this shape: PERF008 only fires on a loop-
invariant effectful call INSIDE a loop -- this is a duplicate effect
reachable from two DISTINCT call sites in ONE function body (however many
hops deep each one is), with no loop involved at all.

INTERPROCEDURAL BY CONSTRUCTION: this module does NOT re-implement its own
one-off call graph. It reuses `frob.perf._effect_summaries.EffectGraph`
(T-0922: promoted out of `_loop_effects.py` into its own shared substrate
module -- see that module's own docstring) -- the SAME shared EFFECT-
SUMMARY substrate PERF008 already builds -- via `EffectGraph.
summary(symref)`, which returns the FULL transitively-reachable `(kind,
arg)` multiset for any function, however many calls deep, propagated
through sibling callees, cousins, and diamonds alike (cycle-safe, budget-
bounded). This is what makes the detector genuinely interprocedural rather
than same-function-only: `f()` calling `g()` calling `h()` which spawns,
where `f()` ALSO calls `i()` calling `j()` which spawns the SAME argv, is
caught exactly the same way as two direct sibling calls in `f()` are --
the duplicate can be split arbitrarily deep and across arbitrarily
different callees, as long as both paths originate from call sites inside
the SAME function body.

DETECTION (python only, matching this package's existing per-rule
python-first/best-effort-elsewhere tiering -- see PERF001-004's own
docstring in `frob.perf._rules`): for each function/method symbol `F`,
walk `F`'s own direct call sites (only the calls textually IN `F`'s body,
not nested arbitrarily deep -- the STARTING points of the interprocedural
walk). For each call site, if it is ITSELF a spawn call, its own
occurrence is `(kind, arg)` directly; otherwise resolve the callee by
short name (every ambiguous candidate tried, matching `EffectGraph`'s own
best-effort posture) and union each candidate's full `summary(...)` --
however deep that callee's own call graph goes. Attribute the resulting
occurrence set to THIS call site (its own source line -- two separate
calls to the SAME helper still count as two separate costs paid, matching
the real T-0919 shape where two DIFFERENT named closures happened to share
one leaf spawn). If two or more of `F`'s own call sites (by line) end up
sharing the SAME `(kind, arg)` occurrence, `F` is paying for the same
expensive effect more than once on one call path -- PERF012 fires once per
`F`, naming the duplicate call sites/lines and the shared argument shape.
WARN-tier, waivable (`frob:waive PERF012 reason="..."`) for a genuinely
deliberate independent re-run (e.g. intentionally re-measuring fresh state
between the two calls).

UNKNOWN POLICY (T-0922 acceptance criterion (c)): `EffectGraph.summary`
now surfaces `Unknown` explicitly instead of silently contributing
nothing for an unresolvable call site/argument/budget cutoff (see
`_effect_summaries.Unknown`'s own docstring for why it deliberately never
compares equal to another `Unknown`). PERF012's grouping key is `(kind,
arg)` equality (`by_occurrence` in `_def_violations`): because an
`Unknown` instance is never equal to any other value (not even another
`Unknown`), it can NEVER be grouped with anything and therefore can NEVER
by itself cause a duplicate finding. `Unknown` occurrences still flow all
the way into each call site's own occurrence set (`_entry_occurrences`
now emits one for every call this rule cannot bind, rather than an empty
set) so the set genuinely represents "everything this call path reaches,
including the parts we could not resolve" -- but PERF012's actual
FIRING policy is unaffected: it degrades toward MISSING a duplicate that
happens to route through an unresolved edge, never toward manufacturing
one. This is the same fail-open posture the rest of this substrate takes,
made explicit and inspectable rather than an implicit consequence of
`None` being filtered out silently.

GENERALITY: `EffectGraph`'s own needle tables (`_SPAWN_DOTTED`/
`_FS_WALK_DOTTED`/`_FS_WALK_ATTRS`/`_SPAWN_BARE` in `_effect_summaries.py`)
already cover process-spawn AND directory-walk effects, not just
`subprocess.run` -- this rule inherits BOTH kinds for free by reusing that
same substrate, matching the user directive that "subprocess.run is ONE
EXAMPLE" of the expensive-operation class this must generalize over.
Extending the needle tables to cover network calls/heavy parses is a
follow-up widening of `_effect_summaries.py`'s own tables (both PERF008
and PERF012 gain it simultaneously, by construction, once added there) --
tracked as its own todo rather than silently expanded here.

# frob:todo T-0919 non-python (typescript/rust/cpp) coverage for PERF012
# is out of this ticket's scope, same posture as PERF001-004/PERF008's
# existing python-first tiering -- track any follow-up need as its own
# ticket rather than silently expanding this one.
# frob:todo T-0919 widen _effect_summaries.py's needle tables (network
# calls, heavy parses) beyond process-spawn/directory-walk -- PERF008 and
# PERF012 both inherit any such widening automatically since they share
# EffectGraph, but choosing the right needle set is its own research
# task, not bundled into this ticket.
"""
# frob:waive INV006 reason="T-0919 first-turn-on: this module's design- rationale \
# prose ('this module does NOT re-implement...', 'the SAME shared EFFECT-SUMMARY \
# substrate...') is source-level commentary describing already-implemented internal \
# behavior, verifiable by reading the code it annotates, rather than a separate \
# cross-module contract needing its own tracked invariant -- same disposition as the \
# identical T-0585/T-0775 calibration-batch waivers already carried by other \
# first-turn-on modules in this package"

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from tree_sitter import Node

from frob.gates._models import Severity, Violation
from frob.lang import child_by_field as _child_by_field
from frob.lang import node_text as _node_text
from frob.lang import raw_tree as _raw_tree
from frob.lang._models import ParsedFile
from frob.logging import get_logger
from frob.perf._effect_summaries import (
    UNKNOWN_KIND,
    EffectOccurrence,
    Unknown,
    _callee_dotted,
    _callee_short_name,
    _contains_splat,
    _direct_effect,
    _infer_receiver_class,
    _normalize_arg_text,
)
from frob.perf._effect_summaries import EffectGraph as _EffectGraph

_log = get_logger(__name__)

__all__ = ["duplicate_spawn_violations"]


#: Compound-statement node types whose body is CONDITIONAL/repeated
#: relative to the enclosing function body -- a call inside one of these
#: is NOT an unconditional sibling of a call outside it (T-0919: this is
#: what turns a real "try cache, fall back to build" pattern -- `if
#: loaded.is_err: loaded = build_graph(...)` -- from a false PERF012 hit
#: into a correctly-excluded one, since the fallback branch's call only
#: ever runs when the FIRST call already failed, never unconditionally
#: alongside it). `for`/`while` are included here too: PERF008 already
#: owns loop-body effect detection with its own loop-invariance semantics
#: -- a call inside a loop is not this rule's population.
_CONDITIONAL_KINDS = frozenset(
    {
        "if_statement",
        "try_statement",
        "with_statement",
        "for_statement",
        "while_statement",
        "match_statement",
    }
)


def _iter_top_level_calls(body: Node) -> list[Node]:
    """Every `call` node inside `body`, EXCLUDING any call lexically nested
    inside a conditional/repeated compound statement (`_CONDITIONAL_KINDS`)
    or a nested `def` -- these are `F`'s own UNCONDITIONAL "entry" call
    sites for the interprocedural walk (T-0919): two calls that are both
    unconditional siblings of the SAME function body are the real
    duplicated-cost shape (both always execute on every call to `F`); a
    call gated behind an `if`/`try`/loop is not comparable the same way
    (it may run zero or many times, and a try/except fallback is by
    definition mutually exclusive with the path it falls back FROM, never
    a genuine duplicate). A call inside a nested closure belongs to THAT
    closure's own scan when it is visited as its own top-level `def`, not
    to the outer function's entry set, avoiding double-attributing the
    same call site to two different enclosing functions."""
    hits: list[Node] = []
    stack = [body]
    while stack:
        node = stack.pop()
        if node.type == "call":
            hits.append(node)
            # Do not descend into a call's own arguments looking for MORE
            # top-level call sites of `body` -- a call nested inside this
            # call's arguments is still lexically "inside body" and a
            # legitimate further entry point, so we DO want to keep
            # walking; only a nested `function_definition`/conditional
            # stops descent.
            stack.extend(node.children)
            continue
        if node.type == "function_definition" or node.type in _CONDITIONAL_KINDS:
            continue
        stack.extend(node.children)
    return hits


def _entry_occurrences(
    call: Node, graph: _EffectGraph, from_path: str, source: str | bytes
) -> frozenset[EffectOccurrence]:
    """T-0919/T-0922: the occurrence set attributed to one call site
    `call` -- itself directly, if `call` is a spawn/fs-walk call, else
    every occurrence transitively reachable from its callee name, resolved
    via `EffectGraph.resolve_scoped` (same-file-preferred, NOT an
    unfiltered by-name union -- see that method's own docstring for why: a
    common short name like `run` resolving to dozens of unrelated
    project-wide symbols and unioning ALL of their summaries would
    cross-contaminate completely unrelated call paths, a real over-firing
    bug this scoping fixes rather than a hypothetical one).

    T-0922: a call this function cannot bind at all -- its own argument
    list is unrecoverable, its callee is not a simple bare/dotted name, or
    `resolve_scoped` returns no candidate -- now yields an explicit
    `(UNKNOWN_KIND, Unknown(reason))` singleton instead of `frozenset()`
    (silently empty). See this module's own Unknown-policy note: an
    `Unknown` can never itself pair up with another occurrence under
    `_def_violations`'s equality-keyed grouping, so this can only ever
    ADD visibility, never a false duplicate."""
    effect = _direct_effect(call)
    if effect is not None:
        args = _child_by_field(call, "arguments")
        if args is None or _contains_splat(args):
            reason = (
                "unresolvable argument text"
                if args is None
                else "a *args/**kwargs splat argument whose real content is "
                "caller-dependent (T-1018)"
            )
            return frozenset(
                {
                    (
                        UNKNOWN_KIND,
                        Unknown(
                            f"{reason} for a {effect} call "
                            f"at {from_path}:{call.start_point[0] + 1}"
                        ),
                    )
                }
            )
        return frozenset({(effect, _normalize_arg_text(_node_text(args)))})
    short = _callee_short_name(call)
    if short is None:
        return frozenset(
            {
                (
                    UNKNOWN_KIND,
                    Unknown(
                        f"call at {from_path}:{call.start_point[0] + 1} has no "
                        f"simple bare/dotted callee name to resolve"
                    ),
                )
            }
        )
    dotted = _callee_dotted(call)
    receiver_class = _infer_receiver_class(source, dotted[0]) if dotted else None
    candidates = graph.resolve_scoped(short, from_path, receiver_class)
    if not candidates:
        return frozenset(
            {
                (
                    UNKNOWN_KIND,
                    Unknown(
                        f"unresolvable/ambiguous callee {short!r} at "
                        f"{from_path}:{call.start_point[0] + 1}"
                    ),
                )
            }
        )
    # T-1053: lru_cache blindness -- if EVERY resolved candidate is itself
    # decorated `@lru_cache`/`@cache`, repeated calls to it from distinct
    # call sites are cache hits after the first, not a real duplicate cost
    # paid twice; contribute no occurrence at all so this call site can
    # never pair up with another as a PERF012 duplicate. An AMBIGUOUS
    # resolution where only some candidates are memoized is left alone
    # (fail open), same posture as `EffectGraph.callee_is_memoized`.
    if all(graph.is_memoized(c) for c in candidates):
        return frozenset()
    acc: set[EffectOccurrence] = set()
    for candidate in candidates:
        acc |= graph.summary(candidate)
    return frozenset(acc)


def _split_clean_runs(
    clean_lines: set[int], all_effect_lines: set[int]
) -> list[list[int]]:
    """T-1018 calibration: split `clean_lines` (this occurrence's own call
    sites whose FULL reachable-effect set is exactly this ONE occurrence --
    see `_def_violations`) into maximal runs with no OTHER effectful call
    site (`all_effect_lines`, any occurrence, resolved or `Unknown`)
    strictly between two consecutive members.

    Motivation: two call sites sharing an occurrence are only a genuine
    "paid for the same thing twice, share it instead" duplicate when
    NOTHING effectful happens between them -- the real T-0919 shape
    (`check_gates()` immediately followed by `check_gate_findings()`, both
    independently spawning the identical `frob check --ticket <id>`, one
    right after the other). The T-1018 over-fire (20 -> 1777 findings)
    traced to a DIFFERENT, extremely common shape this used to conflate
    with that one: a read-only, naturally-repeatable call (`git rev-parse
    HEAD`) invoked BEFORE and AFTER an intervening call that mutates state
    -- a before/after state-change assertion, not a redundant recomputation
    (`tests/test_ticket_land.py`'s `_rev_parse(...)`-before, `_apply_gate_
    rule_sync(...)`-mutate, `_rev_parse(...)`-after idiom was the single
    largest cluster). A call site whose own summary reaches something OTHER
    than this occurrence (multi-effect, or an `Unknown` member alongside
    it) is treated the same as a wholly unrelated intervening call: its
    presence between two same-occurrence call sites means something this
    substrate cannot fully characterize happened in between, so the two
    ends are no longer assumed interchangeable. A call site whose ENTIRE
    reachable effect is cleanly just this one occurrence never breaks a
    run (matches every T-0919/T-0922 true-positive fixture, none of which
    have anything between their two duplicate call sites)."""
    if not clean_lines:
        return []
    sorted_lines = sorted(clean_lines)
    runs: list[list[int]] = [[sorted_lines[0]]]
    for prev_line, cur_line in zip(sorted_lines, sorted_lines[1:]):
        interrupted = any(prev_line < other < cur_line for other in all_effect_lines)
        if interrupted:
            runs.append([cur_line])
        else:
            runs[-1].append(cur_line)
    return runs


def _def_violations(
    path: str, func_def: Node, graph: _EffectGraph, source: str | bytes
) -> list[Violation]:
    """PERF012 hits for one `def` node: every direct call site's own
    occurrence set (`_entry_occurrences`), grouped by `(kind, arg)`; any
    occurrence shared by 2+ DISTINCT call-site LINES, with nothing
    effectful intervening between the shared lines (T-1018:
    `_split_clean_runs`), is a duplicate. `Unknown` members (T-0922) never
    group with anything (see `Unknown`'s own docstring -- identity-only
    equality), so they can never by themselves manufacture a duplicate
    finding here."""
    body = _child_by_field(func_def, "body")
    if body is None:
        return []
    by_occurrence: dict[EffectOccurrence, set[int]] = {}
    # T-1018: per-call-site full occurrence set, keyed by line, so
    # `_split_clean_runs` can tell a "clean" singleton call site (its
    # ENTIRE reachable effect is exactly one occurrence) from a
    # multi-effect/uncertain one that should break a run rather than
    # silently extend it.
    occurrences_by_line: dict[int, set[EffectOccurrence]] = {}
    for call in _iter_top_level_calls(body):
        occs = _entry_occurrences(call, graph, path, source)
        line = call.start_point[0] + 1
        if occs:
            occurrences_by_line.setdefault(line, set()).update(occs)
        for occurrence in occs:
            by_occurrence.setdefault(occurrence, set()).add(line)
    all_effect_lines = set(occurrences_by_line)
    violations: list[Violation] = []
    line = func_def.start_point[0] + 1
    name_node = _child_by_field(func_def, "name")
    func_name = _node_text(name_node) if name_node is not None else "?"
    for (kind, arg), lines in by_occurrence.items():
        if kind == UNKNOWN_KIND:
            continue
        clean_lines = {
            ln for ln in lines if occurrences_by_line.get(ln) == {(kind, arg)}
        }
        for run in _split_clean_runs(clean_lines, all_effect_lines):
            if len(run) < 2:
                continue
            # frob:waive PERF004 reason="run is this loop's own per-run list, not a shared re-sort"  # noqa: E501
            line_list = ", ".join(str(n) for n in sorted(run))
            violations.append(
                Violation(
                    rule="PERF012",
                    severity=Severity.WARN,
                    file=path,
                    line=line,
                    message=(
                        f"PERF012: {path}:{line} `{func_name}` has {len(run)} "
                        f"call sites (lines {line_list}) that each independently "
                        f"reach a {kind} call with the SAME argument shape -- "
                        f"share one result between them instead of paying for it "
                        f"{len(run)} times, or add a reasoned frob:waive "
                        f"PERF012 justifying an independent re-run"
                    ),
                )
            )
    return violations


def _file_violations(path: str, graph: _EffectGraph) -> list[Violation]:
    """Every PERF012 hit in one python source file: every top-level `def`
    (function/method) is its own independent scan (`_def_violations`)."""
    result = _raw_tree(Path(path))
    if result.is_err:
        return []
    tree, source, language = result.danger_ok
    if language != "python":
        return []
    violations: list[Violation] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "function_definition":
            violations.extend(_def_violations(path, node, graph, source))
        stack.extend(node.children)
    return violations


# frob:doc docs/modules/perf.md#duplicate-identical-subprocess-spawn-detector-perf012-t-0919  # noqa: E501
# frob:tests tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.test_two_helpers_spawning_identical_subprocess_is_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.test_two_helpers_spawning_different_subprocess_args_is_not_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.test_single_helper_call_is_not_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.test_multi_hop_duplicate_via_different_intermediate_callees_is_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.test_call_site_varying_argument_is_not_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.test_three_hop_duplicate_split_across_sibling_callees_is_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn.test_unresolvable_dynamic_dispatch_callee_never_manufactures_a_duplicate  # noqa: E501
# frob:ticket T-0919
# frob:ticket T-0922
# frob:waive DUP001 reason="dup grouped this with \
# _loop_effects.py::loop_invariant_effect_violations on the shared per-file \
# driver-loop shape -- see that function's own DUP001 waiver for full reasoning \
# (T-0861)"
def duplicate_spawn_violations(
    files: Sequence[ParsedFile], graph: _EffectGraph | None = None
) -> tuple[Violation, ...]:
    """PERF012: a function/method whose body has two or more call sites
    that each (directly, or transitively via `EffectGraph.summary`'s
    interprocedural walk -- however many hops deep, however split across
    sibling/cousin callees) reach a process-spawn/directory-walk effect
    with the textually-identical (whitespace-normalized) argument shape --
    the exact T-0919 anti-pattern (`_check_gates_summary_fn`/
    `_check_gate_findings_fn` each independently spawning `frob check
    --ticket <id>`), generalized to any call-graph depth/shape. WARN-tier
    (waivable with a reasoned `frob:waive PERF012 reason="..."`), never a
    silent error. See this module's docstring for its Unknown policy
    (T-0922 criterion (c)): an unresolvable binding degrades to a
    non-grouping `Unknown` occurrence, never a manufactured duplicate.

    `graph`: an optional pre-built `EffectGraph` to SHARE with a sibling
    PERF008 run in the same `perf_rules` pass (T-0919: avoids re-indexing
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
        "perf012: scanned %d python file(s), %d violation(s)",
        len(seen_paths),
        len(violations),
    )
    return tuple(violations)
