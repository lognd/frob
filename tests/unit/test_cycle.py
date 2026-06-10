from frob.cycle.graph import DependencyGraph, find_cycles


def test_no_cycle():
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    assert find_cycles(g) == []


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
