## Done report

T-4478: hoisted the per-iteration sorted(paths) in _cross_ticket_leakage_violations into one sorted() pass over flattened (other_id, path) pairs, eliminating the flagged PERF004. This is a behavior-preserving perf fix (identical output order, tests unchanged), so frob ticket evidence --check-repro correctly reports PASSED_AT_PARENT/confirmatory-only rather than a real repro; verification instead: frob check --only perf on this worktree shows zero PERF004 hits in src/frob/tickets/_land.py (was 1 before the fix).

### Changed
```
 src/frob/tickets/_land.py | 49 ++++++++++++++++++++++++++++-------------------
 tickets/T-4478/ticket.md  |  2 ++
 2 files changed, 31 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_cross_ticket_leakage_gate.py::TestCrossTicketLeakageGate::test_leaked_sibling_scope_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 4917 warning(s), 968 waived
- error-findings: DRIFT001@src/frob/doctor.py, PRE001@tickets/T-4478, REF002@docs/design/macos-portability.md
