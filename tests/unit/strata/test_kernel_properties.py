"""Property tests for the strata-core Rust kernel (docs/strata/kernel.md#strata-core).

Hypothesis generates random small graphs and checks `strata_core.reachable`,
`strata_core.worst_age`, and `strata_core.demand` against pure-Python
brute-force oracles written in this file. This is the hardening pass for
T-0065 (age propagation): the kernel already implements the age collapse
(BFS closure, memoized longest-path DFS, rate sum), this file is what
proves it over the space of graphs, not just the handful of examples in
test_facts.py.

T-0144: the module used to do a bare module-level `import strata_core`,
which hard-fails `pytest --collect-only` (not just this module's tests)
in any environment without the native extension built -- breaking
`frob ticket evidence` for every ticket, not just strata ones. Guarded
via `pytest.importorskip` (the same natives-less precedent as
`tests/unit/test_dup_core.py`'s `frob_core` skip) so collection always
succeeds and this module's tests skip loudly instead of erroring.
"""

# frob:ticket T-0144
from __future__ import annotations

import math
from itertools import combinations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

strata_core = pytest.importorskip(
    "strata_core",
    reason="strata_core native extension not built -- run `make core`",
)

# frob:tests strata-core/src/lib.rs::reachable kind="unit"
# frob:tests strata-core/src/lib.rs::worst_age kind="unit"
# frob:tests strata-core/src/lib.rs::demand kind="unit"
# frob:tests strata-core/src/lib.rs::propagated_demand kind="unit"

_NODE_IDS = tuple(f"n{i}" for i in range(12))


def _node_ids(n: int) -> tuple[str, ...]:
    """The first `n` deterministic node ids used across every strategy."""
    return _NODE_IDS[:n]


@st.composite
def _plain_edges(
    draw: st.DrawFn,
) -> tuple[tuple[str, ...], list[tuple[str, str, str, bool, bool]]]:
    """A random directed graph (cycles allowed) up to 12 nodes / 25 flows.

    Edges reference node indices (not ids directly) so hypothesis can shrink
    toward small node counts; each edge carries a random barrier flag and
    (T-0282) a random transitive flag -- a non-transitive edge's `dst` is
    reachable but the closure must not chain past it (strata-core/src/
    lib.rs::reachable's terminal-edge support).
    """
    n = draw(st.integers(min_value=1, max_value=12))
    nodes = _node_ids(n)
    num_edges = draw(st.integers(min_value=0, max_value=25))
    edges: list[tuple[str, str, str, bool, bool]] = []
    for i in range(num_edges):
        src = draw(st.sampled_from(nodes))
        dst = draw(st.sampled_from(nodes))
        barrier = draw(st.booleans())
        transitive = draw(st.booleans())
        edges.append((f"f{i}", src, dst, barrier, transitive))
    return nodes, edges


@st.composite
def _dag_edges(
    draw: st.DrawFn,
) -> tuple[tuple[str, ...], list[tuple[str, str, str, float]]]:
    """A random DAG (edges only from lower to higher node index) with random ages."""
    n = draw(st.integers(min_value=1, max_value=8))
    nodes = _node_ids(n)
    pairs = list(combinations(range(n), 2))  # i < j, guarantees acyclic
    chosen = draw(
        st.lists(st.sampled_from(pairs), max_size=min(20, len(pairs)), unique=True)
        if pairs
        else st.just([])
    )
    edges: list[tuple[str, str, str, float]] = []
    for i, (a, b) in enumerate(chosen):
        age = draw(
            st.floats(
                min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False
            )
        )
        edges.append((f"f{i}", nodes[a], nodes[b], age))
    return nodes, edges


@st.composite
def _cyclic_edges(
    draw: st.DrawFn,
) -> tuple[tuple[str, ...], list[tuple[str, str, str, float]]]:
    """A random graph (cycles allowed) with non-negative ages, up to 6 nodes.

    Ages are biased toward exact 0.0 (and small integers) rather than drawn
    uniformly over a wide float range, so hypothesis actually forms
    zero-net-weight cycles that REACH the target -- the case the earlier
    memoized-DFS `worst_age` got wrong (T-0065 reviewer round: it treated
    ANY revisit as unbounded, not just a positive-weight one). A uniform
    float draw almost never lands on exactly 0.0, so that regression class
    was invisible to the original generator.
    """
    n = draw(st.integers(min_value=1, max_value=6))
    nodes = _node_ids(n)
    num_edges = draw(st.integers(min_value=0, max_value=12))
    edges: list[tuple[str, str, str, float]] = []
    for i in range(num_edges):
        src = draw(st.sampled_from(nodes))
        dst = draw(st.sampled_from(nodes))
        age = draw(st.sampled_from([0.0, 0.0, 0.0, 1.0, 2.0]))
        edges.append((f"f{i}", src, dst, age))
    return nodes, edges


# frob:waive PERF004 reason="one sort per adjacency list to make BFS traversal order deterministic, not resorted per iteration; oracle only runs over hypothesis-generated small graphs"
def _bfs_oracle(
    nodes: tuple[str, ...],
    edges: list[tuple[str, str, str, bool, bool]],
    src: str,
    through_barriers: bool,
) -> dict[str, tuple[str, ...]]:
    """Pure-Python BFS reference for `strata_core.reachable`.

    T-0282: a non-transitive edge (`transitive=False`) discovers its `dst`
    but does not enqueue it for further expansion -- it can be the LAST hop
    of a witness path, never a middle link.
    """
    outgoing: dict[str, list[tuple[str, str, str, bool, bool]]] = {}
    for e in edges:
        outgoing.setdefault(e[1], []).append(e)
    for outs in outgoing.values():
        outs.sort(key=lambda e: e[0])

    paths: dict[str, tuple[str, ...]] = {src: (src,)}
    frontier = [src]
    while frontier:
        nxt_frontier: list[str] = []
        for current in frontier:
            for flow_id, _s, d, barrier, transitive in outgoing.get(current, ()):
                if not through_barriers and barrier:
                    continue
                if d not in paths:
                    paths[d] = (*paths[current], flow_id, d)
                    if transitive:
                        nxt_frontier.append(d)
        frontier = nxt_frontier
    return paths


def _assert_valid_witness(
    path: tuple[str, ...],
    edges_by_id: dict[str, tuple[str, str]],
    src: str,
) -> None:
    """A witness path alternates node/flow ids and every hop matches a real edge."""
    assert path[0] == src
    node_positions = path[0::2]
    flow_positions = path[1::2]
    for idx, flow_id in enumerate(flow_positions):
        assert flow_id in edges_by_id
        expected_src, expected_dst = edges_by_id[flow_id]
        assert node_positions[idx] == expected_src
        assert node_positions[idx + 1] == expected_dst


# frob:waive PERF003 reason="dict/set comprehensions over the oracle output plus a real BFS-walk loop, over hypothesis-generated small graphs; not a cross join"
@settings(max_examples=60, deadline=None)
@given(_plain_edges(), st.booleans())
def test_reachable_matches_bfs_oracle(graph, through_barriers) -> None:
    """`strata_core.reachable` matches a pure-Python BFS oracle, witnesses valid."""
    nodes, edges = graph
    if not nodes:
        return
    src = nodes[0]
    got = strata_core.reachable(edges, src, through_barriers)
    want = _bfs_oracle(nodes, edges, src, through_barriers)
    assert set(got) == set(want)

    edges_by_id = {e[0]: (e[1], e[2]) for e in edges}
    barrier_by_id = {e[0]: e[3] for e in edges}
    transitive_by_id = {e[0]: e[4] for e in edges}
    for node, path in got.items():
        path = tuple(path)
        _assert_valid_witness(path, edges_by_id, src)
        assert path[-1] == node
        if not through_barriers:
            for flow_id in path[1::2]:
                assert not barrier_by_id[flow_id]
        # T-0282: a non-transitive edge may only be the LAST hop of any
        # witness path -- it never has a further edge chained past it.
        flow_hops = path[1::2]
        for flow_id in flow_hops[:-1]:
            assert transitive_by_id[flow_id]


def _longest_path_to_target(
    nodes: tuple[str, ...],
    edges: list[tuple[str, str, str, float]],
    target: str,
) -> tuple[float, tuple[str, ...]]:
    """Brute-force: enumerate every simple path ending at `target`, keep the oldest."""
    incoming: dict[str, list[tuple[str, str, str, float]]] = {}
    for e in edges:
        incoming.setdefault(e[2], []).append(e)

    best_age = 0.0
    best_path: tuple[str, ...] = (target,)

    def dfs(
        node: str, visited: set[str], acc_age: float, acc_path: tuple[str, ...]
    ) -> None:
        nonlocal best_age, best_path
        if acc_age > best_age:
            best_age = acc_age
            best_path = acc_path
        for flow_id, s, d, age in incoming.get(node, ()):
            if s in visited:
                continue
            dfs(s, visited | {s}, acc_age + age, (s, flow_id, *acc_path))

    dfs(target, {target}, 0.0, (target,))
    return best_age, best_path


@settings(max_examples=60, deadline=None)
@given(_dag_edges())
def test_worst_age_matches_longest_path_oracle_on_dags(graph) -> None:
    """On acyclic graphs, `worst_age` equals brute-force longest-path search."""
    nodes, edges = graph
    if not nodes:
        return
    target = nodes[-1]
    got_age, got_path = strata_core.worst_age(edges, target)
    want_age, want_path = _longest_path_to_target(nodes, edges, target)

    assert math.isclose(got_age, want_age, rel_tol=1e-9, abs_tol=1e-9)

    edges_by_id = {e[0]: (e[1], e[2]) for e in edges}
    ages_by_id = {e[0]: e[3] for e in edges}
    got_path = tuple(got_path)
    if len(got_path) == 1:
        assert got_age == 0.0
    else:
        _assert_valid_witness(got_path, edges_by_id, got_path[0])
        assert got_path[-1] == target
        summed = sum(ages_by_id[f] for f in got_path[1::2])
        assert math.isclose(summed, got_age, rel_tol=1e-9, abs_tol=1e-9)


@settings(max_examples=60, deadline=None)
@given(_cyclic_edges())
def test_worst_age_cycle_property(graph) -> None:
    """A positive-age cycle reaching target is +inf; otherwise the DAG oracle holds."""
    nodes, edges = graph
    if not nodes:
        return
    target = nodes[0]

    # Detect: does some node on a positive-age simple cycle also reach target?
    outgoing: dict[str, list[tuple[str, str, str, float]]] = {}
    for e in edges:
        outgoing.setdefault(e[1], []).append(e)

    def reaches_target(start: str) -> bool:
        seen = {start}
        frontier = [start]
        while frontier:
            nxt = []
            for cur in frontier:
                for _fid, _s, d, _age in outgoing.get(cur, ()):
                    if d == target:
                        return True
                    if d not in seen:
                        seen.add(d)
                        nxt.append(d)
            frontier = nxt
        return start == target

    def find_positive_cycle_reaching_target() -> bool:
        for start in nodes:

            def dfs(node: str, visited: set[str], acc: float) -> bool:
                for _fid, _s, d, age in outgoing.get(node, ()):
                    if d == start:
                        if acc + age > 0.0 and reaches_target(start):
                            return True
                    elif d not in visited:
                        if dfs(d, visited | {d}, acc + age):
                            return True
                return False

            if dfs(start, {start}, 0.0):
                return True
        return False

    got_age, _got_path = strata_core.worst_age(edges, target)

    if find_positive_cycle_reaching_target():
        assert got_age == float("inf")
    else:
        want_age, _want_path = _longest_path_to_target(nodes, edges, target)
        assert math.isclose(got_age, want_age, rel_tol=1e-9, abs_tol=1e-9)


@settings(max_examples=40, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.sampled_from(_node_ids(6)),
            st.floats(
                min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
            ),
        ),
        max_size=25,
    ),
    st.sampled_from(_node_ids(6)),
)
def test_demand_matches_sum_oracle(rates, target_node) -> None:
    """`strata_core.demand` equals the sum of rates matching the target node."""
    got = strata_core.demand(rates, target_node)
    want = sum(r for dst, r in rates if dst == target_node)
    assert got == want


@settings(max_examples=30, deadline=None)
@given(_plain_edges(), st.booleans())
def test_reachable_is_deterministic(graph, through_barriers) -> None:
    """Calling `reachable` twice on the same input yields identical results."""
    nodes, edges = graph
    if not nodes:
        return
    src = nodes[0]
    first = strata_core.reachable(edges, src, through_barriers)
    second = strata_core.reachable(edges, src, through_barriers)
    assert {k: tuple(v) for k, v in first.items()} == {
        k: tuple(v) for k, v in second.items()
    }


@settings(max_examples=30, deadline=None)
@given(_dag_edges())
def test_worst_age_is_deterministic(graph) -> None:
    """Calling `worst_age` twice on the same input yields identical results."""
    nodes, edges = graph
    if not nodes:
        return
    target = nodes[-1]
    first = strata_core.worst_age(edges, target)
    second = strata_core.worst_age(edges, target)
    assert (first[0], tuple(first[1])) == (second[0], tuple(second[1]))


@settings(max_examples=30, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.sampled_from(_node_ids(6)),
            st.floats(
                min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
            ),
        ),
        max_size=25,
    ),
    st.sampled_from(_node_ids(6)),
)
def test_demand_is_deterministic(rates, target_node) -> None:
    """Calling `demand` twice on the same input yields identical results."""
    first = strata_core.demand(rates, target_node)
    second = strata_core.demand(rates, target_node)
    assert first == second


# G10 (docs/audits/strata.md): `propagated_demand` (fanout-multiplied,
# cycle-aware, unlike the plain rate-sum `demand` pyfunction already
# covered above) had no differential/property coverage at all -- the
# single most safety-critical remaining kernel per this ticket's own
# framing, since a silent undercount here can make a RATE/UTILIZATION
# bound claim falsely PROVED (the exact bug class T-0065's `worst_age`
# reviewer round already found once, in the sibling kernel).
@st.composite
def _demand_edges(
    draw: st.DrawFn,
) -> tuple[tuple[str, ...], list[tuple[str, str, str, float | None, float]]]:
    """A random directed graph (cycles allowed) with declared or undeclared
    per-edge rates and a fanout multiplier, up to 6 nodes / 14 flows --
    small enough for the O(iterations * edges) fixpoint oracle below to
    stay fast, large enough to form both fed and unfed cycles."""
    n = draw(st.integers(min_value=1, max_value=6))
    nodes = _node_ids(n)
    num_edges = draw(st.integers(min_value=0, max_value=14))
    edges: list[tuple[str, str, str, float | None, float]] = []
    for i in range(num_edges):
        src = draw(st.sampled_from(nodes))
        dst = draw(st.sampled_from(nodes))
        has_rate = draw(st.booleans())
        rate = (
            draw(
                st.floats(
                    min_value=0.0,
                    max_value=100.0,
                    allow_nan=False,
                    allow_infinity=False,
                )
            )
            if has_rate
            else None
        )
        fanout = draw(st.sampled_from([1.0, 1.0, 2.0, 0.5]))
        edges.append((f"f{i}", src, dst, rate, fanout))
    return nodes, edges


def _fixpoint_demand_oracle(
    nodes: tuple[str, ...],
    edges: list[tuple[str, str, str, float | None, float]],
    target: str,
) -> float:
    """Independent reference for `strata_core.propagated_demand`: plain
    Gauss-Seidel fixpoint iteration over `demand[n] = sum(declared
    contributions) + sum(demand[src] * fanout for each undeclared-rate
    inbound edge)`, deliberately NOT the Rust kernel's recursive-with-
    active-stack algorithm (a materially different computation path is
    the point of a differential oracle -- a shared bug in both would
    otherwise go undetected).

    An unfed cycle (no path from any declared-rate source reaches it)
    keeps circulating exactly 0 forever, since its base contribution and
    every upstream value inside the cycle is 0 -- the fixpoint is stable
    at 0.0, matching the kernel's documented behavior. A fed cycle whose
    net per-lap multiplier exceeds 1 diverges: the target's value keeps
    growing between round `n` and round `2n`, which this oracle reports
    as `+inf`, same as the kernel's cycle-detection witness path does
    (this oracle drops witness paths entirely -- callers needing one
    already have `TestReviewerRegression`-style direct kernel tests for
    that; this property only needs the NUMBER to agree)."""
    declared_contrib: dict[str, float] = dict.fromkeys(nodes, 0.0)
    undeclared_in: dict[str, list[tuple[str, float]]] = {n: [] for n in nodes}
    for _flow_id, src, dst, rate, fanout in edges:
        if rate is None:
            undeclared_in[dst].append((src, fanout))
        else:
            declared_contrib[dst] += rate * fanout

    demand = dict.fromkeys(nodes, 0.0)
    rounds = 2 * len(nodes) + 4
    checkpoint = demand[target]
    for i in range(rounds):
        demand = {
            n: declared_contrib[n]
            + sum(demand[src] * fanout for src, fanout in undeclared_in[n])
            for n in nodes
        }
        if i == len(nodes) + 1:
            checkpoint = demand[target]
    if (
        not math.isclose(checkpoint, demand[target], rel_tol=1e-9, abs_tol=1e-9)
        and demand[target] > checkpoint
    ):
        return float("inf")
    return demand[target]


@settings(max_examples=80, deadline=None)
@given(_demand_edges())
def test_propagated_demand_matches_fixpoint_oracle(graph) -> None:
    """`strata_core.propagated_demand` agrees with an independent
    Gauss-Seidel fixpoint oracle on the SOUND direction charter law 2
    cares about: it must NEVER report a finite value lower than the true
    (oracle) value -- that would be a silent undercount, the falsely-
    PROVED failure class T-0065's `worst_age` reviewer round already
    found once. The kernel MAY report `+inf` in cases the oracle proves
    are actually finite (its `rate_sources` fed-cycle detection is
    magnitude- and destination-blind -- see `TestZeroDeclaredRateFedCycle`
    and this ticket's Done report for the disclosed, filed-not-fixed
    over-approximation) -- that direction is the documented, ACCEPTABLE
    fail-safe one ("fails toward overcounting load, not undercounting
    it"), so it is allowed here, not asserted away. When the kernel does
    NOT report unbounded, its value must match the oracle exactly (no
    tolerance for "close enough but not equal" once both sides agree the
    graph is finite)."""
    nodes, edges = graph
    if not nodes:
        return
    target = nodes[-1]
    got_value, _got_witness = strata_core.propagated_demand(edges, target)
    want_value = _fixpoint_demand_oracle(nodes, edges, target)

    if got_value == float("inf"):
        return  # kernel's allowed conservative direction (see docstring)
    assert want_value != float("inf"), (
        f"kernel reported a FINITE demand ({got_value}) for a graph the "
        f"independent oracle proves is unbounded ({want_value}) -- this "
        f"is the disallowed undercount direction, a real soundness bug"
    )
    assert math.isclose(got_value, want_value, rel_tol=1e-6, abs_tol=1e-6)


@settings(max_examples=30, deadline=None)
@given(_demand_edges())
def test_propagated_demand_is_deterministic(graph) -> None:
    """Calling `propagated_demand` twice on the same input yields the
    same value (the witness path may differ in a tie, but the VALUE --
    the number a RATE/UTILIZATION claim is actually compared against --
    must not)."""
    nodes, edges = graph
    if not nodes:
        return
    target = nodes[-1]
    first_value, _ = strata_core.propagated_demand(edges, target)
    second_value, _ = strata_core.propagated_demand(edges, target)
    assert first_value == second_value


class TestZeroDeclaredRateFedCycle:
    """G10 differential-testing follow-up (docs/audits/strata.md), found
    BY the new `test_propagated_demand_matches_fixpoint_oracle` property
    while writing this ticket: `propagated_demand`'s `rate_sources` (the
    "is this node forward-reachable from a rate declaration" set used to
    decide whether an undeclared-rate cycle is 'fed', hence unbounded)
    is populated by ANY declared rate, magnitude-blind -- `Some(r) =>
    rate_sources.insert(...)` never checks `r > 0.0`. The function's own
    docstring says "POSITIVE-rate cycles ... are unbounded", but the code
    flags a cycle fed ONLY by a literal `rate=0.0` declaration as `+inf`
    too, even though that cycle's true numeric value converges to exactly
    0.0 (confirmed: the independent fixpoint oracle above converges to
    0.0 for this exact shape). This is disclosed here as a genuine
    docstring/implementation discrepancy for a maintainer decision (fix
    the code to check magnitude, or fix the docstring to say "declared-
    rate" not "positive-rate") -- NOT silently resolved either way by
    this ticket, whose job is proving kernel/oracle agreement, not
    picking a semantics. Kept as a permanent regression pin so the
    CURRENT behavior cannot silently change without this test's author
    noticing (frob:tests binds it to the exact kernel line the WHY
    comment above `propagated_demand` names)."""

    # frob:tests strata-core/src/lib.rs::propagated_demand kind="unit"
    def test_self_loop_fed_by_literal_zero_rate_reports_unbounded(self) -> None:
        edges = [
            ("f0", "n0", "n0", None, 1.0),
            ("f1", "n0", "n0", 0.0, 1.0),
        ]
        value, _witness = strata_core.propagated_demand(edges, "n0")
        assert value == float("inf")


class TestReviewerRegression:
    """T-0065 reviewer round: the memoized-DFS `worst_age` was REJECTED here.

    Verified counterexample: `best[node]` computed under one caller's
    active-set was silently reused by a caller with a different
    active-set, undercounting the true longest simple path. An undercount
    here is the worst possible bug class for this tool -- it can make an
    `AGE bound claim <= v` FALSELY PROVED. Kept permanently as both a cargo
    test (`worst_age_reviewer_regression_context_dependent_memo` in
    strata-core/src/lib.rs) and this pytest, calling `strata_core.worst_age`
    directly.
    """

    # frob:tests strata-core/src/lib.rs::worst_age kind="unit"
    def test_context_dependent_memo_undercount(self) -> None:
        edges = [
            ("e0", "B", "A", 0.0),
            ("e1", "B", "T", 0.0),
            ("e2", "A", "T", 3.0),
            ("e3", "A", "B", 0.0),
            ("e4", "C", "B", 1.0),
        ]
        age, path = strata_core.worst_age(edges, "T")
        assert age == 4.0
        assert tuple(path) == ("C", "e4", "B", "e0", "A", "e2", "T")

    # frob:tests strata-core/src/lib.rs::worst_age kind="unit"
    def test_adversarial_shared_node_divergent_entry_a(self) -> None:
        """A shared node (M) is entered once via a heavy chain, once via a
        light chain, both feeding forward into the same target -- exactly
        the shape where a caller-context-dependent memo would undercount.
        """
        edges = [
            ("e0", "heavy_src", "M", 5.0),
            ("e1", "light_src", "M", 1.0),
            ("e2", "M", "target", 2.0),
        ]
        age, path = strata_core.worst_age(edges, "target")
        assert age == 7.0
        assert tuple(path) == ("heavy_src", "e0", "M", "e2", "target")

    # frob:tests strata-core/src/lib.rs::worst_age kind="unit"
    def test_adversarial_shared_node_divergent_entry_b(self) -> None:
        """A node (M) sits on a zero-net cycle AND is also reachable from an
        external positive-age source; the cycle must not truncate the
        external path's contribution when M is later revisited via it.
        """
        edges = [
            ("e0", "M", "N", 0.0),
            ("e1", "N", "M", 0.0),
            ("e2", "ext", "M", 6.0),
            ("e3", "N", "target", 4.0),
        ]
        age, path = strata_core.worst_age(edges, "target")
        assert age == 10.0
        assert tuple(path) == ("ext", "e2", "M", "e0", "N", "e3", "target")

    # frob:tests strata-core/src/lib.rs::worst_age kind="unit"
    def test_adversarial_three_way_convergence(self) -> None:
        """Three independent chains of different lengths converge on the
        same intermediate node before the final hop to target.
        """
        edges = [
            ("e0", "s1", "hub", 1.0),
            ("e1", "s2", "hub", 9.0),
            ("e2", "s3", "hub", 4.0),
            ("e3", "hub", "target", 1.0),
        ]
        age, path = strata_core.worst_age(edges, "target")
        assert age == 10.0
        assert tuple(path) == ("s2", "e1", "hub", "e3", "target")
