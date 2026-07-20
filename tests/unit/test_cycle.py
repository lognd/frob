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


# frob:waive DUP001 reason="parallel test methods within test_cycle.py (2 \
# sites) sharing an arrange-act scaffold typical of exhaustive per-case \
# coverage; extracting would obscure per-case intent"
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


# frob:waive DUP001 reason="parallel test methods within test_cycle.py (2 \
# sites) sharing an arrange-act scaffold typical of exhaustive per-case \
# coverage; extracting would obscure per-case intent"
def test_cycle_not_duplicated():
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    g.add_edge("a", "c")  # extra edge inside the same SCC
    cycles = find_cycles(g)
    assert len(cycles) == 1
