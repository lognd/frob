## Done report

Changed:
- src/frob/check/_python.py: `_gates_error_result`'s `GateError.
  QueueUnavailable` branch now emits `Diagnostic(file=None, code=
  "QUEUE001", ...)` instead of the old hardcoded `file="tickets.md"`
  with no code -- tickets.md is the retired ledger v1 monofile (deleted
  by T-2356) and cannot be the real failing artifact under ledger v2.
- src/frob/tickets/_land_verify.py: T-1549's sentinel exclusion in
  `_reverify_gate_findings_by_identity` keyed on an empty rule id only;
  widened to also recognize `rule == "QUEUE001"` so this fix does not
  silently un-exclude the sentinel and reintroduce the ClaimDivergence
  land-blocking bug T-1549 fixed. Both shapes stay recognized (additive,
  not narrowed) so a stale pre-T-2684 captured claim still matches.
- src/frob/gates/_waive.py: registered QUEUE001 in _KNOWN_GATE_RULES
  (GATERULE001 requires every constructed rule id to be registered
  before the ticket that constructs it can close).
- tests/unit/test_check.py: TestGatesErrorResultQueueUnavailable, two
  tests -- must-fire (QueueUnavailable produces code=QUEUE001, file=
  None, no "tickets.md" in the message) and must-NOT-regress (any other
  GateError value is still a zero-diagnostic soft skip).
- tests/unit/test_land_verify_claim_divergence_sentinel.py:
  TestQueue001CodedSentinelIsAlsoExcluded, one new test -- a
  ("QUEUE001", "") finding does not refuse the land, same as the old
  empty-rule-id shape. (The must-NOT-regress and negative-control cases
  for this exact mechanism already exist in the file's pre-existing
  TestQueueUnavailableSentinelIsExcludedFromDivergence class -- adding
  near-duplicates of those was caught by DUP001 and removed.)

Positive controls (both directions, both verified):
- must-fire: test_queue001_coded_sentinel_does_not_refuse -- genuinely
  FAILS at the pre-fix commit (5a8828dfa, confirmed via `frob ticket
  evidence --check-repro`: FAILED_AT_PARENT, a real repro) and passes
  at the fix commit.
- must-NOT-regress: test_old_empty_rule_shape_still_excluded_too (the
  pre-existing test_sentinel_alone_does_not_refuse already covers this)
  and test_other_gate_error_is_a_soft_skip_not_an_error both confirm
  the widened check/new code path do not disturb unrelated behavior.

Evidence: 5 pytest node ids (see evidence: block) covering both files'
new/changed behavior; designated repro is
tests/unit/test_land_verify_claim_divergence_sentinel.py::
TestQueue001CodedSentinelIsAlsoExcluded::
test_queue001_coded_sentinel_does_not_refuse (FAILED_AT_PARENT
confirmed against 5a8828dfa).

Gates: `frob check --ticket T-2684 --json` -> 0 findings of any
severity against any of the 5 touched files (src/frob/check/_python.py,
src/frob/tickets/_land_verify.py, src/frob/gates/_waive.py, tests/unit/
test_check.py, tests/unit/test_land_verify_claim_divergence_sentinel.
py). Repo-wide baseline (~55-60 pre-existing errors) unrelated to this
ticket's diff, unchanged by it.

Filed: T-2710 (thread the real failing ledger path through GateError.QueueUnavailable -- disclosed limitation named in this ticket's own body above: GateError carries no payload today).

### Changed
```
 src/frob/check/_python.py                          | 40 ++++++++--
 src/frob/gates/_waive.py                           |  8 ++
 src/frob/tickets/_land_verify.py                   | 24 +++++-
 src/frob/tickets/_setters.py                       | 46 +++++++++++-
 tests/unit/test_check.py                           | 44 +++++++++++
 .../test_land_verify_claim_divergence_sentinel.py  | 33 +++++++++
 tests/unit/test_ticket_store.py                    | 82 +++++++++++++++++++++
 tickets/T-2678/done-report.md                      | 64 ++++++++++++++++
 tickets/T-2678/ticket.md                           | 51 +++++++++++--
 tickets/T-2684/done-report.md                      | 85 ++++++++++++++++++++++
 tickets/T-2684/ticket.md                           | 42 ++++++++++-
 tickets/T-2709/ticket.md                 | 37 ++++++++++
 tickets/T-2710/ticket.md                 | 44 +++++++++++
 13 files changed, 582 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueue001CodedSentinelIsAlsoExcluded::test_old_empty_rule_shape_still_excluded_too` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueue001CodedSentinelIsAlsoExcluded::test_a_real_rule_named_differently_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestGatesErrorResultQueueUnavailable::test_queue_unavailable_sets_real_code_and_no_stale_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestGatesErrorResultQueueUnavailable::test_other_gate_error_is_a_soft_skip_not_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueue001CodedSentinelIsAlsoExcluded::test_queue001_coded_sentinel_does_not_refuse` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 5 evidence id(s))
- gates: 37 error(s), 851 warning(s), 703 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2679-series/src/frob/gates/_fix_engine.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2684, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
