"""T-0702 demand-declaration grammar + propagation unit coverage
(`frob.strata._facts.FactBase.aggregate_demand`) -- mirrors
`test_reliability.py`'s "build via `parse_module`/`elaborate`, assert on
the resulting `FactBase`" convention: the grammar->field wiring itself is
covered by `strata-core/src/parse.rs`'s own unit tests (`parses_node_
users_and_rate` et al.), this file covers end-to-end propagation and the
declared-vs-zero distinction the acceptance criterion cares about.
"""

from __future__ import annotations

from frob.strata import Node, Quantity, elaborate, parse_module
from frob.strata._facts import AggregateDemand, build_facts


def _facts_for(source: str):
    module = parse_module(source).danger_ok
    model = elaborate(module).danger_ok
    return build_facts(model).danger_ok


class TestAggregateDemand:
    # frob:tests \
    # tests/unit/strata/test_demand.py::TestAggregateDemand.test_two_entry_nodes_sum_at\
    # _fan_in
    def test_two_entry_nodes_sum_at_fan_in(self):
        """T-0702 acceptance criterion: two entry nodes declaring users
        300000/200000 both flowing into one resource sum to 500000."""
        facts = _facts_for(
            """module m
            node entry_a : trusted { users 300000; }
            node entry_b : trusted { users 200000; }
            store db : trusted { }
            flow f1: entry_a -> db { }
            flow f2: entry_b -> db { }
            """
        )
        result = facts.aggregate_demand("db")
        assert result == AggregateDemand(declared=True, value=500000.0, witness=("db",))

    # frob:tests \
    # tests/unit/strata/test_demand.py::TestAggregateDemand.test_no_demand_declared_is_\
    # undeclared_not_zero
    def test_no_demand_declared_is_undeclared_not_zero(self):
        """T-0702 acceptance criterion: with no `users`/`rate` declared
        anywhere, a node reports UNDECLARED, not a silent zero."""
        facts = _facts_for(
            """module m
            node entry_a : trusted { }
            store db : trusted { }
            flow f1: entry_a -> db { }
            """
        )
        result = facts.aggregate_demand("db")
        assert result.declared is False
        assert result.value == 0.0

    # frob:tests \
    # tests/unit/strata/test_demand.py::TestAggregateDemand.test_demand_declared_elsewh\
    # ere_not_reaching_node_is_undeclared
    def test_demand_declared_elsewhere_not_reaching_node_is_undeclared(self):
        """A node with declared demand that does NOT flow toward the
        target still leaves the target UNDECLARED, not zero -- the
        distinction is per-target reachability, not global presence."""
        facts = _facts_for(
            """module m
            node entry_a : trusted { users 100; }
            node unrelated_sink : trusted { }
            store db : trusted { }
            flow f1: entry_a -> unrelated_sink { }
            """
        )
        result = facts.aggregate_demand("db")
        assert result.declared is False

    # frob:tests \
    # tests/unit/strata/test_demand.py::TestAggregateDemand.test_rate_and_users_compose\
    # _additively
    def test_rate_and_users_compose_additively(self):
        """A node declaring BOTH `users` and `rate` composes them
        additively, not exclusively (module docstring)."""
        facts = _facts_for(
            """module m
            node entry_a : trusted { users 100; rate 50 req/s; }
            store db : trusted { }
            flow f1: entry_a -> db { }
            """
        )
        result = facts.aggregate_demand("entry_a")
        assert result == AggregateDemand(
            declared=True, value=150.0, witness=("entry_a",)
        )

    # frob:tests \
    # tests/unit/strata/test_demand.py::TestAggregateDemand.test_self_declaring_node_re\
    # ports_its_own_demand
    def test_self_declaring_node_reports_its_own_demand(self):
        """A node that itself declares demand reports it directly, with no
        inbound flow needed at all."""
        facts = _facts_for("module m\nnode entry_a : trusted { users 42; }")
        result = facts.aggregate_demand("entry_a")
        assert result == AggregateDemand(
            declared=True, value=42.0, witness=("entry_a",)
        )

    # frob:tests \
    # tests/unit/strata/test_demand.py::TestAggregateDemand.test_fanout_multiplies_prop\
    # agated_demand
    def test_fanout_multiplies_propagated_demand(self):
        """Demand propagation still respects `fanout` the same way
        `propagated_demand` does -- T-0702 builds on the existing
        propagation kernel unchanged."""
        facts = _facts_for(
            """module m
            node entry_a : trusted { users 100; }
            node relay : trusted { }
            store db : trusted { }
            flow f1: entry_a -> relay { fanout 2; }
            flow f2: relay -> db { }
            """
        )
        result = facts.aggregate_demand("db")
        assert result.declared is True
        assert result.value == 200.0


class TestNodeUsersRateFields:
    # frob:tests \
    # tests/unit/strata/test_demand.py::TestNodeUsersRateFields.test_node_defaults_to_n\
    # one
    def test_node_defaults_to_none(self):
        """A plain `Node` (no `users`/`rate` declared) keeps both `None`
        -- backward compatible with every pre-T-0702 `Node(...)` call
        site."""
        node = Node(id="n", trust="trusted")
        assert node.users is None
        assert node.rate is None

    # frob:tests \
    # tests/unit/strata/test_demand.py::TestNodeUsersRateFields.test_node_accepts_expli\
    # cit_users_and_rate
    def test_node_accepts_explicit_users_and_rate(self):
        """`Node.users`/`Node.rate` round-trip a direct construction (the
        `_elaborate.py`/`_infra.py` wiring's target shape)."""
        node = Node(
            id="n",
            trust="trusted",
            users=1000.0,
            rate=Quantity(value=50.0, unit="req/s"),
        )
        assert node.users == 1000.0
        assert node.rate is not None
        assert node.rate.value == 50.0


def test_store_users_and_rate_elaborate_same_as_node():
    """T-0261 node/store symmetry: a `store`'s `users`/`rate` clauses
    elaborate onto `Node.users`/`Node.rate` exactly like `node`'s do."""
    # frob:tests \
    # tests/unit/strata/test_demand.py::test_store_users_and_rate_elaborate_same_as_node
    facts = _facts_for("module m\nstore db : trusted { users 500000; }")
    node = facts.nodes["db"]
    assert node.users == 500000.0
