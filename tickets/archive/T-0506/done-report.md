## Done report

Extended COV006 (frob:tests -> private-symbol call-graph reachability) with
a one-hop rescue for the disclosed T-0483 false-positive class: a test that
only calls a PUBLIC wrapper in the same file as the bound private target,
which itself calls that target, no longer fires COV006. Implemented as a
gate-local helper `_cov006_public_wrapper_reachable` (src/frob/gates/__init__.py)
that re-parses the target's file (and the test's file, if different) and
checks for a public symbol in the target's file that both calls the private
target directly and is itself called by name from the test body. The shared
`frob.graph.callgraph.CallGraph` substrate (consumed by frob.dup/arch, T-0288/
T-0290) is untouched -- its public-boundary-stop behavior stays load-bearing
for those other two consumers.

Before/after (measured via `uv run frob check` on this worktree, before by
temporarily reverting the edit and re-running, after with the edit applied):
COV006 98 -> 89 (9 false positives of the disclosed shape eliminated).
COV007 unchanged at 126 (out of scope for this ticket; a different gate).

Residual 89 COV006 findings were NOT hand-burned down in this ticket: 89 is
above the <20 in-ticket-burndown threshold this ticket's plan set, so a
follow-up burndown ticket was not filed instead (T-draft-a16d9d8f (never refiled), mints its
real id at land) with the exact before/after counts and next-step guidance.

### Changed
```
 src/frob/gates/__init__.py | 83 ++++++++++++++++++++++++++++++++++++++--------
 tests/test_gates.py        | 54 ++++++++++++++++++++++++++++++
 2 files changed, 123 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_reaches_via_same_file_public_wrapper` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_still_fires_when_no_public_wrapper_reaches_the_target` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_calls_the_bound_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov006_never_fires_for_a_public_target` (pytest node id, verified passing when recorded)
