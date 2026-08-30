## Done report

Root cause: NOT the 11 gate errors themselves -- they are a symptom.
`frob.app.check_runner._refuse_ticket_lease_mismatch` already short-
circuits correctly for a MUTATING invocation (`--stamp-baseline`/
`--stamp-coverage`): it fires before any gate/stage runs and its
refusal ("frob ticket start <id>") is the sole output.

`tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::
test_ticket_lease_recorded_elsewhere_refuses` drove `frob check` with
`--only gates` -- a READ, which T-1556 (landed after this test) made
`_check_is_mutating`/`ticket_lease_pin` deliberately skip (a plain
`--ticket` read writes no lease-protected state, so a reviewer can
re-verify a ticket's gates without holding its lease). That change
made the CLI-level refusal never fire for this test's invocation
shape; the test kept passing only because `gate:PRE`'s (PRE001) OLD
remediation text happened to also contain the literal substring
"frob ticket start" -- a coincidence, not the lease-pin refusal
firing. T-3301 (F-031) later corrected PRE001's own remediation to
"frob ticket sweep <id>" (`frob ticket start` refuses on an already-
in-progress ticket, so "start" was actively wrong advice there), which
removed the accidental substring match and surfaced this ticket's
real, pre-existing gap: the test exercised a code path T-1556 already
made exempt.

Fix: updated the system test to drive the invocation shape the pin
check still actually covers (`--stamp-baseline`, mutating), matching
`_refuse_ticket_lease_mismatch`'s own T-1556 contract, and added a
new `test_refusal_short_circuits_before_any_gate_runs` that pins the
ordering invariant by name: on a lease mismatch, no `gate:<NAME>`
report line appears anywhere in the output (i.e. no gate ever ran),
not just that the refusal text is present somewhere. No production
code changed -- the short-circuit in `check_runner.run()` /
`_refuse_ticket_lease_mismatch` was already correct for the
invocation shape it is actually contracted to cover.

Evidence: both new/updated tests pass locally 5/5 with -p no:xdist.
Also reran tests/test_tickets_leases.py (T-1556's own coverage, out
of this ticket's scope) to confirm no regression: 32/32 pass.

Filed: none.

Gates: frob check --ticket T-3469 --only gates-fast clean on the
ticket-scoped gates (gate:SCOPE 0 errors, gate:PRE 0 errors after
`frob ticket sweep T-3469`); repo-wide unscoped gate counts in that
same run are pre-existing and out of this ticket's scope per its own
NOTE line.

### Changed
```
 tickets/T-3469/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_refusal_short_circuits_before_any_gate_runs` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 15 error(s), 4194 warning(s), 864 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
