## Done report

Deviated from the ticket's literal plan (a Tier-A auto-fix that re-runs
`done-report` on `ClaimDivergence`) after root-causing the actual
incident: today's four-burned-attempt `ClaimDivergence` refusal named an
EMPTY rule id against `tickets.md`. Traced that to `frob.check._python.
_gates_error_result`, which synthesizes a sentinel `Diagnostic(file=
"tickets.md", ...)` with no `code=` whenever `run_gates` itself fails
with `GateError.QueueUnavailable` (a malformed ledger entry, not a real
gate result). `scope_matches` treats `tickets.md`/`LEDGER_PATH` as
implicitly in scope for every ticket, so `_reverify_gate_findings_by_
identity` (`src/frob/tickets/_land_verify.py`) let this identity-less
sentinel reach `scoped_new` unconditionally -- presenting as a brand-new
in-scope finding and refusing the land with `ClaimDivergence` for EVERY
ticket landing while the ticket queue happened to be unreadable.

This is exactly the "cannot be satisfied because something upstream is
broken" case the brief asked to distinguish from a genuinely stale
claim: the T-1531 manual recipe (re-run `done-report` to refresh a
stale capture) cannot fix it, because the refresh's own fresh capture
run hits the identical queue failure and reproduces the identical
sentinel -- which is exactly what happened today, four times. Building
the Tier-A auto-retry the ticket's plan describes would have automated
retrying a case that structurally cannot succeed, turning a four-attempt
diagnosis into an unbounded one -- the brief's own explicit warning.

Fix: filter any `(rule_id, file)` pair with an empty `rule_id` out of
`fresh_findings` before the scope-based comparison in
`_reverify_gate_findings_by_identity`, logging a distinct WARNING that
names it as an infrastructure-failure sentinel (never a real finding)
and explicitly says a done-report refresh will NOT fix it -- point at
repairing the ticket queue instead. A real, non-empty-rule-id new
in-scope finding still refuses exactly as before; the filter narrows
what counts as evidence of divergence, it does not weaken the check
itself.

Out-of-scope, left alone: `frob.check._python._gates_error_result`
itself (produces the sentinel) is outside this ticket's declared scope
and outside `src/frob/tickets/**`; not touched.

### Changed
```
 rapid-debt.jsonl                                   |   7 +
 src/frob/app/telemetry.py                          |  14 ++
 src/frob/app/ticket_runner/_land_cmd.py            |  96 ++++++++++-
 src/frob/app/ticket_runner/_new.py                 |  10 ++
 src/frob/tickets/_land_verify.py                   |  45 ++++++
 .../test_land_verify_claim_divergence_sentinel.py  | 118 ++++++++++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    | 177 +++++++++++++++++++++
 tickets/T-1549/done-report.md                      |  63 ++++++++
 tickets/T-2141/done-report.md                      |  53 ++++++
 tickets/T-2141/ticket.md                           |  16 +-
 tickets/T-2303/done-report.md                      |  84 ++++++++++
 tickets/T-2303/ticket.md                           |   9 +-
 tickets/T-2691/ticket.md                 |  58 +++++++
 tickets/T-2692/ticket.md                 |  42 +++++
 tickets/T-2693/ticket.md                 |  52 ++++++
 15 files changed, 839 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence::test_sentinel_alone_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence::test_real_new_in_scope_finding_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence::test_sentinel_plus_real_finding_still_refuses_on_the_real_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 34 error(s), 751 warning(s), 700 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
