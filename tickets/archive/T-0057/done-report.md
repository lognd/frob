## Done report

Delivered src/frob/strata/_claims.py: evaluate_claims walks claims in
declaration order (one result per claim, none droppable). noflow refutes
with the first witness path through the barrier-respecting closure and
supports trust-level endpoint expansion; reach is PROVED(exists)-with-
witness whose refutation is correctly a forall; bounds cover AGE (worst-
path staleness, inf-on-cycle refutes as unbounded), RATE (demand),
UTILIZATION (percent vs replica ceiling, refusing undeclared capacity),
SIZE (declared flow quantity), LATENCY (deny-by-default refute until
phase-2 path budgets); wrong-dimension limits fail the evaluation closed.
Assumes close ASSUMED with owner/review and overdue flagging. 12 new
unit tests; docs anchor docs/strata/kernel.md#claim-evaluation. Ticket
check exit 0, ruff clean, 37 strata tests green.
