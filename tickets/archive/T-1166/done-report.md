## Done report

Disposition for T-1166 (serve daemon capability-boundary creep, T-1094/
T-1096): chose option (a) from the ticket body -- the daemon's own
socket/watch-file effects (pidfile/lease-state open/write/unlink, its own
event-bus socket write, its own idle-monitor self-wake socket connect)
are the daemon's OWN process boundary, not a delegated call into another
node's owned resource, so they are honestly declared rather than
refactored away. design/frob.strata's `serve` node already declares
`may "fs"; may "net";` for this reason (pre-existing, not touched here).

Updated `TestDeployServeMutateNodeSplitConformance::
test_serve_declares_zero_may_and_exercises_zero_effects`'s synthetic
fixture to grant `may=("fs", "net")` (mirroring the real design node)
instead of zero `may`, with a docstring explaining the T-1166 disposition
and why the guard's original purpose (catching a FUTURE undeclared
capability, e.g. `exec`) is still preserved. Kept the test's original
method name unchanged -- T-0440's archived Done report (tickets-
archive.md) cites this exact pytest node id as evidence, and renaming it
would break that already-closed, out-of-scope ticket's evidence
resolution (COV003).

Verified: `pytest tests/unit/strata/test_effects.py::
TestDeployServeMutateNodeSplitConformance` all 3 pass. `frob sys
sync-interface --check`: no drift.

### Changed
```
 tests/unit/strata/test_effects.py | 38 ++++++++++++++++++++++++++++----------
 tickets.md                        |  5 +++--
 2 files changed, 31 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 2099 warning(s), 497 waived
- error-findings: none (measured, zero errors)
