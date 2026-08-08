## Done report

T-1836: verified already fixed, no code change needed. The failure log
(attempt 1, 2026-08-08) already documented this: T-1817 exempted
tickets/<id>/* in gates/__init__.py's _b9_exempt_file, and T-1819 gave
scope_matches a ticket_id param that treats tickets/<id>/** as implicitly
in scope, wired at _scope_gate_check_file. src/frob/tickets/_models.py
(this ticket's declared scope) is out of my own reach anyway -- it is on
this session's explicit forbidden-files list (another agent holds it) --
so no edit was attempted or needed either way.

Re-verified independently this session:
`frob check --only scope --ticket T-1836` reports 0 SCOPE001 errors.
`tests/test_tickets.py::TestScopeMatching::test_own_shard_always_in_scope`
passes, covering exactly this behavior.

### Changed
```
 tickets/T-1836/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestScopeMatching::test_own_shard_always_in_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 778 warning(s), 742 waived
- error-findings: DOCENUM001@docs/modules/gates.md
