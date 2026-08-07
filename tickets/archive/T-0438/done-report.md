## Done report

Added tests/test_gates.py::TestGateOrderSetEquality::test_canonical_gate_order_matches_all_gates,
pinning set(_CANONICAL_GATE_ORDER) == _ALL_GATES plus a no-duplicate-names
assertion, bound via frob:tests on both _CANONICAL_GATE_ORDER and
_ALL_GATES. Now a gate added to _ALL_GATES without a matching canonical-order
entry (or vice versa) fails this test at CI time instead of silently
dropping from output. The invariant already holds on main (verified during
the T-0436 docblocks landing); this is the standing regression guard.

Evidence: the one test (passes). Implemented by the easy-wins sweeper,
coordinator inline-reviewed (test-only, low risk) and landed via 3-way.
