## Done report

LEDGER_PATH ('tickets.md') was always implicitly in scope for every
ticket, but predates the sharded per-ticket store (tickets/<id>/
ticket.md, tickets/<id>/done-report.md), so routine frob ticket start/
sweep auto-commits touching a ticket's own shard tripped a false
SCOPE001 -- the sibling gap T-1817 already closed for the unscoped B9
path (frob.gates._b9_exempt_file); this closes it for scope_matches'
own per-ticket declared-scope check (SCOPE001/scope_gate).

scope_matches gained an optional ticket_id keyword (default None,
every pre-T-1819 call site unaffected): when given, tickets/<ticket_
id>/** is implicitly appended to the matched globs, mirroring LEDGER_
PATH's tickets.md-always-in-scope treatment. _scope_gate_check_file
(src/frob/gates/__init__.py, SCOPE001's own check) now passes
ticket_id=ticket.id through -- the only call site changed, since it is
the one place a false SCOPE001 was actually observed.

Left B10's open-scope-ownership check (_dirt_owned_by_no_open_ticket's
sibling _covered_by_open_scope, src/frob/gates/__init__.py ~1490) and
every other scope_matches call site untouched -- they were not the
reported bug and default ticket_id=None keeps them byte-identical to
before.

### Changed
```
 tickets/T-1819/ticket.md | 26 +++++++++++++++++++++++++-
 1 file changed, 25 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestScopeMatching::test_own_shard_always_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_scope001_own_sharded_ledger_shard_implicitly_in_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_scope001_another_tickets_shard_still_out_of_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 7 error(s), 1371 warning(s), 740 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/registry/_staleness.py, COV001@src/frob/tickets/_doable.py, E501@/home/logan/projects/frob/.claude/worktrees/refusal-attrib/src/frob/registry/_staleness.py, TEST001@src/frob/registry/_staleness.py
