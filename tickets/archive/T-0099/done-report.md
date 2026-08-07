## Done report

Verified actual behavior directly (not from ticket memory): in
`src/frob/strata/_facts.py::FactBase.propagated_demand`, a flow's `rate`
is only used if `flow.rate.base_value()` (`_models.py::Quantity.base_value`)
returns `Ok`; if it returns `Err` (e.g. unknown unit), `rate` stays `None`
and the edge is passed to `strata_core.propagated_demand` exactly like a
flow with no declared rate at all -- the Rust kernel
(`strata-core/src/lib.rs::propagated_demand`, `incoming_undeclared` map)
then recurses into the source node's own propagated demand. Confirmed the
ticket's premise is correct: unresolvable rates PROPAGATE upstream demand,
they do not drop to 0 or silently error.

Changed:
- docs/strata/kernel.md#capacity-semantics -- new "Unresolvable rate:
  propagates, does not drop" paragraph spelling out the behavior, why
  (fails toward overcounting per charter law 2, not undercounting), and
  pointing at the pin test.
- src/frob/strata/_facts.py::FactBase.propagated_demand -- docstring now
  explicitly documents the unresolvable-rate case instead of leaving it
  implied by "declared rate, if any".
- tests/unit/strata/test_capacity.py::TestPropagatedDemand::test_unresolvable_rate_propagates_upstream_demand
  -- new pin test: a flow declaring `rate=Quantity(value=5, unit="bogus-unit")`
  is treated as undeclared and the target's demand comes from the
  upstream source (10.0), not 0 and not the unresolvable 5.
- tickets.md -- extended this ticket's scope to
  `tests/unit/strata/**` and `tickets.md` (mechanics) to cover the pin
  test and this Done report.

Evidence:
tests/unit/strata/test_capacity.py::TestPropagatedDemand::test_unresolvable_rate_propagates_upstream_demand

Filed: none.

Gates: `frob check --ticket T-0099 --json` -- ruff-check/ty clean on
touched files; ruff-format clean on my two touched Python files
(`src/frob/strata/_facts.py`, `tests/unit/strata/test_capacity.py` --
verified directly with `ruff format --check`); the reported
ruff-format failure is pre-existing on `src/frob/strata/_breach.py` /
`tests/unit/strata/test_breach.py`, files I did not touch (another
agent's in-flight work per CLAUDE.md note on T-0093). One remaining
gates SCOPE001 on `tests/test_tickets_evidence_cli.py`: an untracked
file left over from another in-progress agent's ticket (T-0106,
`--evidence` CLI wiring) that surfaced when this worktree merged main;
not created or touched by this ticket, outside its scope, and outside my
authority to resolve (waiving it would require touching T-0106's ticket
record). `frob check` full run (no --ticket filter) gate diagnostics
count: 91, unchanged. `uv run pytest tests/unit/strata -q`: all green
(240 collected, 0 failures).
