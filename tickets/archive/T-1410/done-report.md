## Done report

Computed gate_claims_verified in _close_gate_claims_for_ticket
(frob.app.ticket_runner._close_cmd) and wired it into
_close_guards_for_ticket, so both `frob ticket close` and `frob ticket
reverify` now pass it to transition()/reverify_close_guard(). Detects
every "0 <RULE> findings under <glob>" acceptance criterion
(frob.tickets._evidence._gate_claim_criteria), spawns
`frob check --only gates` once (there is no CLI path-glob filter for gate
violations, so scoping means filtering the returned (rule, file) identity
set by fnmatch against the glob, not narrowing what runs), and refuses
(fails closed on any refused/unparsable spawn) when a live finding for the
named rule survives under the named glob.

Wired the same shape into `frob ticket land`: land()/_land_locked() gained
a new injected `check_gate_claims` callable (mirroring covers_scope's own
calling convention), invoked post-merge alongside the existing D-05/T-0754
post-merge checks, refusing with LandError.ClaimDivergence (reused, no new
LandError variant needed) when unmet. The CLI wiring (_land_gate_claims_fn
in _land_cmd.py) reuses _close_gate_claims_for_ticket's exact computation
against the worktree rather than duplicating it.

Measured cost: a single `--only gates` pass on this repo runs ~113s wall
(per the existing docs comment on frob.check._STAGE_GROUPS) -- slow enough
to name, not slow enough to skip; the spawn carries its own 600s
subprocess timeout, independent of any foreground/session cap, matching
every other guarded_subprocess_run call already in this module.

Verification of the original T-1276 defect: TestCloseRefusesT1276ShapeEndToEnd
drives the REAL `frob ticket close` entry point (ticket_runner._close)
against a ticket carrying T-1276's exact criterion text ("0 TEST005
findings under src/frob/app/**") bound only to an unrelated passing
evidence id, with every OTHER close guard bypassed so the refusal is
isolated to gate_claims_verified. Before T-1410 this ticket closed done
(gate_claims_verified was never computed, always None/permissive) --
test_close_refuses_when_live_findings_remain_under_the_glob now confirms
SystemExit and the ticket staying in-progress; the sibling
test_close_succeeds_once_the_glob_is_actually_clean confirms the same
path still closes once the glob is genuinely clean. Also added
TestCloseGateClaimsForTicket for the underlying helper's own None/False/
True/refused-spawn behavior.

Fixed PERF004 (sorted() call flagged inside a per-criterion for loop) by
extracting _matching_gate_claim_files as its own module-level helper.
Synced design/frob.strata's cli/testsuite interface= declarations via
`frob sys sync-interface` for the two new public helpers and two new test
classes, and moved docs/modules/tickets.md#frob-ticket-land's land()
signature block in the same diff (AFFECT001).

Not run as part of this ticket (coordinator-only per playbook section
3c/6b): the full unscoped suite and make coverage.

### Changed
```
 tickets.md | 31 +++++++++++++++++++++++++++++--
 1 file changed, 29 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_no_gate_claim_criterion_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_live_finding_under_the_named_glob_returns_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_no_matching_finding_returns_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket::test_refused_spawn_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd::test_close_refuses_when_live_findings_remain_under_the_glob` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd::test_close_succeeds_once_the_glob_is_actually_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 1789 warning(s), 699 waived
- error-findings: none (measured, zero errors)
