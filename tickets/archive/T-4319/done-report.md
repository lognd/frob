## Done report

Widened TICK010 (`_tick010_stale_lease_report` in
src/frob/gates/_tickets_gate.py) to consult the EXISTING
`frob.tickets._leases.lease_staleness_reason` judgement's `"holder-dead"`
shape, instead of building a new detector. The path-gone check (T-0714)
stays exactly as before, still WARN; a second pass
(`_tick010_holder_dead_pass`, split out to keep both functions under
ARCH001's 60-line threshold) asks `lease_staleness_reason` the same
question `orphaned_leases`/`release_orphaned_lease` already ask, over the
same raw parse (`_parse_lease_files_cached`), and reports every
`"holder-dead"` lease as an ERROR under the SAME rule id (TICK010) rather
than inventing TICK015 -- a new rule id would have required registering it
in src/frob/gates/_waive.py's `_KNOWN_GATE_RULES`, which sits outside this
ticket's declared scope; reusing TICK010 kept the fix inside the single
file this ticket scopes.

Severity decision, recorded per the ticket's ask: ERROR, not WARN. A stuck
lease actively blocks other work (measured: one of the three incidents had
already refused a legitimate scope change on an unrelated ticket by the
time it was found by hand), and `Severity.ERROR` is what actually makes
`frob check` exit non-zero (`vet_runner`/`_land_cmd` both gate on it) --
the one way a single finding among several thousand lines of check output
is guaranteed to be seen rather than scrolled past, which is the literal
"how does a reader see this" answer the ticket asked for. The
misjudge-a-slow-agent risk stays guarded where it already lived:
`lease_staleness_reason` only returns `"holder-dead"` once the lease TTL
has elapsed AND no process is cwd'd into the worktree AND no `land` is in
progress for the ticket -- the same three-signal bar `orphaned_leases`/
`release_orphaned_lease` already require before a human is even allowed to
release it (T-1876's read-only posture on that helper is untouched). This
rule adds no judgement on top of that; it only decides how loudly an
already-conservative verdict gets reported.

The ERROR message names the exact remedy, matching the existing WARN
message's convention: `frob worktree release-lease <TICKET-ID>`.

Verification forced the condition rather than observing a healthy tree
(two new tests in tests/test_gates_tick009_tick010.py under
TestTick010StaleLeaseReport):
- test_holder_dead_lease_reports_as_error_with_remedy: writes a real,
  on-disk, non-terminal ticket plus a lease file whose worktree directory
  genuinely exists but whose recorded_at is 48h in the past (past
  LEASE_TTL_SECONDS), with nothing cwd'd into that worktree and no
  land.lock held -- forcing lease_staleness_reason's actual "holder-dead"
  path -- and asserts tickets_gate reports exactly one ERROR TICK010
  violation naming the ticket id and the release-lease remedy.
- test_live_holder_lease_is_silent: the same present worktree and real
  ticket, but a fresh recorded_at -- asserts zero TICK010 violations, so
  a slow-but-live agent is never misjudged. This is the negative control
  the ticket explicitly required; without it a silently-always-ERROR
  implementation would have passed the positive test alone.

Both tests, the full tests/test_ticket_leases.py suite (154 tests,
unaffected), and the touched-set `frob test --base main` run green.

Scope: the ticket's own declared scope (src/frob/gates/_tickets_gate.py)
plus tests/test_gates_tick009_tick010.py (my own new tests) were added via
`frob ticket scope T-4319 --add`. Widening scope to this one shared,
multi-rule file (TICK001-014 all live here, already LARGE001-waived as one
family) also pulled in SCOPE002's exhaustive doc/test-coverage closure
check over every OTHER pre-existing _tickN_* function's own frob:doc/
frob:tests targets, unrelated to this change -- acknowledged via
`frob ticket scope-ack T-4319` rather than chasing the closure (adding
docs/modules/gates.md alone cascaded into 700+ further closure warnings,
since it is a project-wide shared catalog doc; that is this file's own
chronic breadth, not new breadth from T-4319).

Found but out of scope: `frob check` also reports 3 pre-existing ERRORs
(INV003/INV004/REF002) against docs/modules/verify-rapid-debt-visibility.md,
landed by a different, already-merged ticket (T-4324) and untouched by this
diff. Filed as a new ticket (draft id T-4337, docs kind, scoped to
that one file) rather than fixed here.

### Changed
```
 tickets/T-4319/done-report.md      | 87 ++++++++++++++++++++++++++++++++++++++
 tickets/T-4319/ticket.md           |  5 ++-
 tickets/T-4337/ticket.md | 47 ++++++++++++++++++++
 3 files changed, 138 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_holder_dead_lease_reports_as_error_with_remedy` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_live_holder_lease_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 4697 warning(s), 955 waived
- error-findings: INV003@docs/modules/verify-rapid-debt-visibility.md, INV004@docs/modules/verify-rapid-debt-visibility.md, REF002@docs/modules/verify-rapid-debt-visibility.md
