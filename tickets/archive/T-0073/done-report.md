## Done report

Changed: strata-core/src/parse/mod.rs::Parser.parse_scenario (grammar: `scenario
ID { rewrite* claim* }`, rewrite := remove/scale/trust, claim reuses
assert/assume); src/frob/strata/_ast.py::RemoveDecl/ScaleDecl/TrustDecl/
ScenarioDecl + Module.scenarios; src/frob/strata/_elaborate.py::
_validate_scenarios/_elaborate_rewrite/_elaborate_scenario (fail-closed
UnknownReference/UnknownLevel); src/frob/strata/_scenarios.py (new):
ScenarioResult, evaluate_scenarios (rewrite a KernelModel copy, cascade
RemoveNode to flows/boundaries, ScaleRate deny-by-default on unrated
flows via new StrataError.UnratedFlow, SetTrust), then re-run
evaluate_claims. docs/strata/kernel.md#scenario added.
Evidence: tests/unit/strata/test_scenarios.py::TestEvaluateScenarios::
test_remove_node_cascades_to_flows_and_boundaries,
test_scale_rate_fails_closed_on_unrated_flow,
TestElaborateScenario::test_fails_closed_on_unknown_trust_level (see
evidence: YAML); full `uv run pytest tests/unit/strata -q` green (122
tests), cargo test green (75), ruff/ty clean.
Filed: none.
Gates: `frob check --ticket T-0073` is NOT clean -- 3 SCOPE001 violations
on strata-core/src/parse.rs, docs/strata/kernel.md, tickets.md: the
ticket's declared scope (`src/frob/strata/**`, `tests/unit/strata/**`)
does not cover the grammar/docs files the mission spec explicitly
required editing (Rust parser grammar + kernel.md#scenario anchor).
BLOCKER: ticket scope needs `strata-core/src/parse.rs` and
`docs/strata/**` added before `frob check --ticket T-0073` can pass;
left open, not closed, for the orchestrator to widen scope and re-sweep.
Also: TEST002 flags `evaluate_scenarios` "0 collected unit case(s)"
despite bound `frob:tests` on all 8 new unit tests -- the pre-existing
`evaluate_claims` shows the identical false-positive, so this is a
systemic tooling gap, not new debt.
