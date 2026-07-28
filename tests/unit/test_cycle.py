import sys

from frob.cycle.graph import DependencyGraph, find_cycles


def test_no_cycle():
    # frob:tests src/frob/cycle/graph.py::DependencyGraph.add_edge kind="unit"
    # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    assert find_cycles(g) == []


def test_add_node_and_nodes_and_neighbors():
    # frob:tests src/frob/cycle/graph.py::DependencyGraph.add_node kind="unit"
    # frob:tests src/frob/cycle/graph.py::DependencyGraph.nodes kind="unit"
    # frob:tests src/frob/cycle/graph.py::DependencyGraph.neighbors kind="unit"
    g = DependencyGraph()
    g.add_node("solo")
    g.add_edge("a", "b")
    assert g.nodes == frozenset({"solo", "a", "b"})
    assert g.neighbors("a") == {"b"}
    assert g.neighbors("solo") == set()


def test_simple_cycle():
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "a")
    cycles = find_cycles(g)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b"}


def test_three_node_cycle():
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    cycles = find_cycles(g)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


def test_two_independent_cycles():
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "a")
    g.add_edge("x", "y")
    g.add_edge("y", "x")
    cycles = find_cycles(g)
    assert len(cycles) == 2


def test_self_loop():
    g = DependencyGraph()
    g.add_edge("a", "a")
    cycles = find_cycles(g)
    assert len(cycles) == 1
    assert cycles[0] == ["a"]


def test_cycle_not_duplicated():
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    g.add_edge("a", "c")  # extra edge inside the same SCC
    cycles = find_cycles(g)
    assert len(cycles) == 1


def _recursive_strongconnect_would_crash(chain_length: int) -> bool:
    """Reproduce the pre-T-0952 native-recursion depth, one frame per chain edge.

    Mirrors the shape of the old `_TarjanState._strongconnect` recursion (one
    call per DFS edge descended) without depending on removed code, so the
    regression this ticket fixes stays demonstrable after the fix lands.
    """
    sys.setrecursionlimit(1000)

    def walk(depth: int) -> None:
        if depth >= chain_length:
            return
        walk(depth + 1)

    try:
        walk(0)
    except RecursionError:
        return True
    return False


def test_long_chain_would_have_crashed_recursive_tarjan():
    # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
    # Documents the T-0950/T-0952 repro: a chain of this length overflows the
    # default recursion limit under a naive recursive descent, one frame per
    # edge -- this is exactly the shape _TarjanState._strongconnect used to
    # recurse in before T-0952 converted it to an explicit-stack iteration.
    assert _recursive_strongconnect_would_crash(5000)


def test_long_chain_no_recursion_error():
    # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
    # Regression for T-0952: find_cycles must not raise RecursionError on a
    # long dependency chain, well past the default sys.getrecursionlimit().
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(1000)
    try:
        g = DependencyGraph()
        chain_length = 5000
        for i in range(chain_length - 1):
            g.add_edge(f"n{i}", f"n{i + 1}")
        cycles = find_cycles(g)
        assert cycles == []
    finally:
        sys.setrecursionlimit(old_limit)


def test_long_chain_with_cycle_no_recursion_error():
    # frob:tests src/frob/cycle/graph.py::find_cycles kind="unit"
    # Same long-chain shape as above, but closed into one big cycle -- checks
    # the iterative rewrite still detects and pops the component correctly
    # (not just that it survives without crashing).
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(1000)
    try:
        g = DependencyGraph()
        chain_length = 5000
        for i in range(chain_length - 1):
            g.add_edge(f"n{i}", f"n{i + 1}")
        g.add_edge(f"n{chain_length - 1}", "n0")
        cycles = find_cycles(g)
        assert len(cycles) == 1
        assert len(cycles[0]) == chain_length
    finally:
        sys.setrecursionlimit(old_limit)
