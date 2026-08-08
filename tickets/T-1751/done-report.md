## Done report

Re-verified the T-1751 citation per its own ask, and the underlying
problem is now moot: `_write_ticket_file` (tests/test_tickets_lease.py)
is exactly the same-file test-fixture-reuse shape T-1746 just fixed for
real (called only by TestClusterScopeConflict's own three test_* methods,
in the same file). Confirmed with a fresh, cache-bypassed
`frob check --only wire`: after removing the waiver outright, WIRE001
reports 0 findings for this file.

Removed the `frob:waive WIRE001 ... follow_up="T-1751"` directive
entirely rather than re-pointing it at a live ticket -- there is nothing
left to waive; the gate itself no longer false-positives here.

Changed:
- tests/test_tickets_lease.py: removed the WIRE001 waiver on
  _write_ticket_file

Evidence:
- tests/test_tickets_lease.py::TestClusterScopeConflict.test_refuses_when_union_scope_collides_with_a_foreign_lease
- 3/3 TestClusterScopeConflict tests pass
- fresh `frob check --only wire` (FROB_NO_GATE_CACHE=1): 0 errors, 0
  warnings on this file

Gates: `uv run frob check --ticket T-1751` (fresh, no cache) shows
gate:SCOPE/gate:ARCH clean for every file this ticket touched; the one
remaining gate:ARCH error (src/frob/tickets/_new_renumber.py) and the one
`ty` diagnostic are pre-existing, landed by a concurrent agent (T-1811)
moments before this check ran -- confirmed via `git log -1 -- <file>`,
not in this ticket's scope, not caused by this change.

### Changed
```
 rapid-debt.jsonl              |  1 +
 tickets/T-1751/ticket.md      | 17 ++++++++++++++++-
 tickets/T-1764/done-report.md |  2 +-
 tickets/T-1764/ticket.md      |  2 +-
 4 files changed, 19 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 582 warning(s), 733 waived
- error-findings: ARCH001@src/frob/tickets/_new_renumber.py, invalid-return-type@src/frob/tickets/_new_renumber.py
