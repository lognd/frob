"""PERF008: loop-invariant effectful call detector (T-0775).

Motivated by the 2026-07-22 rev-parse incident (T-0773): `frob ticket list`
spawned `git rev-parse --git-common-dir` dozens of times because the LOOP
(one iteration per ticket row) and the EFFECT (a subprocess spawn, three
calls deep through `frob.gitio.run_argv`) live in different modules/
functions -- no per-function syntactic PERF heuristic (PERF001-004, all
scoped to one function body) can ever see this shape.

Two pieces, both best-effort and deliberately over-recall (the repo
philosophy: "undecidable invariance leans toward firing"):

1. DIRECT EFFECT DETECTION (`frob.perf._effect_summaries._direct_effect`):
   a call is directly effectful if its own dotted callee name matches a
   known process-spawn or filesystem-walk pattern -- the same small,
   hand-picked needle tables `frob.vet._capability_registry` uses for the
   "exec"/"fs" capability kinds, narrowed here to the spawn and
   directory-walk subset this ticket actually names (T-0775's acceptance
   criteria never mention bare file read/write, so the broader "fs"/
   "fs-read"/"fs-write" registry kinds are intentionally NOT pulled in
   here -- that would fire on every `open()` call in a loop, a different
   and much noisier check no ticket has asked for).

2. TRANSITIVE CALL-GRAPH REACHABILITY (`frob.perf._effect_summaries.
   EffectGraph`, T-0922: promoted out of this module into its own shared
   substrate module -- see that module's docstring for the full public
   surface and the Unknown policy every consuming rule documents): a
   small, local, whole-project, NAME-based call graph -- deliberately NOT
   `frob.graph.callgraph.build_call_graph` (which only ever resolves
   PRIVATE callees, by design, to stop its own BFS at the public-API
   boundary). The real T-0773 incident crosses that exact boundary (the
   effectful call lives behind `frob.gitio.run_argv`, a PUBLIC function
   called from a private helper in a completely different package). This
   substrate needs the opposite resolution rule -- every candidate,
   public or private, is a real edge.

DETECTION: for each `for`/`while` loop (Python only for now -- an
accepted scope cut, matching PERF001-004's existing python-first/other-
language-best-effort tiering; see this module's own TODO below), for
each call site lexically inside that loop's body (attributed to its
INNERMOST enclosing loop when loops nest), determine whether the call is
itself directly effectful OR transitively reaches a directly-effectful
callee via `EffectGraph.reachable_effect`. If so, and every argument at
the call site is LOOP-INVARIANT (its source text names neither the
loop's own bound variable(s) nor any name assigned anywhere in the loop's
body), fire PERF008 naming the call site, the effectful callee, and why
its arguments look invariant. WARN-tier, not ERROR: `frob:waive` with a
reason is always available (T-0775's own acceptance: "re-reading mutable
state can be deliberate under concurrency, so this is warn-tier with an
unwaivable-style justification requirement, not a silent error").

UNKNOWN POLICY (T-0922 acceptance criterion (c)): PERF008 only ever asks
`EffectGraph.reachable_effect(name)`, the cheap yes/no/first-hit question
-- an unresolvable or ambiguous callee name simply yields `None` (no
effect found via this name), so an unresolvable binding can only ever
produce a MISSED finding here, never a false one and never a crash. This
rule does not consume `EffectGraph.summary`'s richer, argument-carrying
`Unknown` members at all (it has no notion of "argument shape", only
"loop-invariant or not") -- PERF012 (`frob.perf._dup_spawn`) is the
consumer whose Unknown policy is about `summary`'s explicit `Unknown`
occurrences; see that module's own docstring.

# frob:todo T-0775 non-python (typescript/rust/cpp) coverage for PERF008
# is out of this ticket's scope, same posture as PERF001-004's existing
# python-first tiering -- track any follow-up need as its own ticket
# rather than silently expanding this one.
"""
# frob:waive INV006 reason="T-0775 first-turn-on: this module's 'deliberately \
# NOT'/'only ever' exclusivity language (module docstring, _EffectGraph docstring) is \
# source-level design-rationale prose describing already-implemented internal \
# behavior, verifiable by reading the code it annotates, rather than a separate \
# cross-module contract needing its own tracked invariant -- same disposition as the \
# identical T-0585 calibration-batch waiver already carried by _redundancy.py and \
# _rules.py in this same package"

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from tree_sitter import Node

from frob.gates._models import Severity, Violation
from frob.lang import child_by_field as _child_by_field
from frob.lang import node_text as _node_text
from frob.lang import raw_tree as _raw_tree
from frob.lang._models import ParsedFile
from frob.logging import get_logger
from frob.perf._effect_summaries import EffectGraph as _EffectGraph
from frob.perf._effect_summaries import (
    _callee_dotted,
    _callee_short_name,
    _direct_effect,
    _infer_receiver_class,
)

_log = get_logger(__name__)

__all__ = ["loop_invariant_effect_violations"]

_LOOP_KINDS = frozenset({"for_statement", "while_statement"})

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ASSIGN_TARGET_RE = re.compile(r"(?<![=!<>])\b([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)")


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


def _call_site_effect(
    call_node: Node, source: str | bytes, graph: _EffectGraph
) -> tuple[str, str] | None:
    """One loop call site's `(effect, effect_name)` -- a direct
    spawn/fs-walk effect first, else one resolved through the effect graph
    with the T-1053 memoized-callee skip and receiver-class narrowing;
    `None` when no effect is reachable from this call site."""
    effect = _direct_effect(call_node)
    if effect is not None:
        func = _child_by_field(call_node, "function")
        return effect, (_node_text(func) if func is not None else "?")
    short_name = _callee_short_name(call_node)
    if short_name is None:
        return None
    # T-1053: lru_cache blindness -- a call to a callee that is itself
    # decorated `@lru_cache`/`@cache` pays its real cost at most once per
    # distinct argument tuple, not once per loop-invariant call site;
    # hoisting/memoizing advice is a false positive here since the callee
    # already memoizes.
    if graph.callee_is_memoized(short_name):
        return None
    # T-1053: receiver-conflation -- narrow an ambiguous dotted call's
    # by-name resolution to the receiver's actually-inferred class when a
    # cheap textual `receiver = ClassName(...)` constructor assignment is
    # found nearby.
    dotted = _callee_dotted(call_node)
    receiver_class = _infer_receiver_class(source, dotted[0]) if dotted else None
    hit = graph.reachable_effect(short_name, receiver_class)
    if hit is None:
        return None
    return hit[0], hit[1]


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
    tree, source, language = result.danger_ok
    if language != "python":
        return []
    violations: list[Violation] = []
    for call_node, loop in _iter_loop_call_sites(tree.root_node):
        resolved = _call_site_effect(call_node, source, graph)
        if resolved is None:
            continue
        effect, effect_name = resolved
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
# frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_loop_invariant_spawn_call_three_hops_deep_is_flagged  # noqa: E501
# frob:tests tests/unit/perf/test_loop_effects.py::TestPerf008LoopInvariantEffect.test_unresolvable_callee_does_not_crash_and_does_not_fire  # noqa: E501
# frob:ticket T-0775
# frob:ticket T-0922
# frob:enforces CHK-GATE-PERF008
def loop_invariant_effect_violations(
    files: Sequence[ParsedFile],
    graph: _EffectGraph | None = None,
) -> tuple[Violation, ...]:
    """PERF008: a loop body's call site that is directly, or transitively
    (via `frob.perf._effect_summaries.EffectGraph`), a process-spawn/
    directory-walk effect, called with arguments that never reference the
    loop's own bound variable(s) or anything derived from them inside the
    loop body -- see this module's docstring for the full detector and
    Unknown policy. WARN-tier (waivable with a reasoned `frob:waive
    PERF008 reason="..."`), never a silent error.

    `graph`: an optional pre-built `EffectGraph` to SHARE with a sibling
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
