## Done report

G10 (docs/audits/strata.md): FactBase's native Rust kernels had no
differential/property tests proving agreement with an independent
reference implementation. Discovered that reachable/worst_age/demand
(the plain rate-sum pyfunction) were ALREADY covered by
tests/unit/strata/test_kernel_properties.py (pre-existing, not written
by this ticket) -- so this ticket's actual gap was propagated_demand
(the fanout-multiplied, cycle-aware kernel FactBase.propagated_demand
actually calls; distinct from the simpler demand pyfunction), the
single most safety-critical of the three since a silent undercount here
can falsely PROVE a RATE/UTILIZATION bound claim.

Added a genuinely independent oracle: a Gauss-Seidel numeric fixpoint
iteration (materially different algorithm from the kernel's recursive-
with-active-stack approach), differential-tested via hypothesis against
strata_core.propagated_demand across random graphs with declared/
undeclared rates, fanout multipliers, and cycles (fed and unfed).

While designing the property, found and confirmed (before weakening the
assertion) a genuine kernel over-approximation: propagated_demand's
`rate_sources` fed-cycle detection is magnitude- and destination-blind
(any node sourcing ANY declared-rate edge, even rate=0.0 or an edge
unrelated to the cycle, is treated as "fed"), so a numerically-0 cycle
can be reported +inf. Confirmed via two counterexamples (a literal
rate=0.0 self-loop; a node sourcing an unrelated declared-rate edge)
that this is the SAFE direction (charter law 2: never undercount, may
over-report unbounded) rather than a soundness bug. The property test
therefore asserts the sound direction only (kernel must never report
finite when the oracle proves unbounded; may report +inf when the
oracle is finite) rather than exact equality, and TestZeroDeclaredRate-
FedCycle pins the current disclosed behavior as a permanent regression
witness. Not Filed T-draft-7f21bb07 (never refiled) for a maintainer decision (tighten the
kernel's magnitude check, or fix its "positive-rate" docstring wording)
-- not resolved here, since choosing kernel semantics is a design
decision outside a testing-harness ticket.

All of tests/unit/strata/test_kernel_properties.py passes (14 tests,
including the 3 new: the property, its determinism twin, and the pinned
regression). ruff/frob check clean for this ticket's scope.

### Changed
```
 design/frob.strata                    |  14 ++-
 src/frob/strata/_selfconform.py       | 133 +++++++++++++++++++---
 src/frob/strata/_threat.py            |  47 +++++++-
 tests/test_vet_containment.py         |   4 +
 tests/unit/strata/test_selfconform.py |  72 ++++++++++++
 tests/unit/strata/test_threat.py      |  78 +++++++++++++
 tickets.md                            | 208 ++++++++++++++++++++++++++++++++--
 7 files changed, 524 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/unit/strata/test_kernel_properties.py::test_propagated_demand_matches_fixpoint_oracle` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_kernel_properties.py::test_propagated_demand_is_deterministic` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_kernel_properties.py::TestZeroDeclaredRateFedCycle::test_self_loop_fed_by_literal_zero_rate_reports_unbounded` (pytest node id, verified passing when recorded)
