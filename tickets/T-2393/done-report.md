## Done report

Added `frob ticket close <id> --no-behavior-change --no-behavior-change-
reason TEXT|--no-behavior-change-reason-file PATH` -- the first-class
front door for BUG002's pre-existing `frob:no-behavior-change
reason="..."` body directive (T-1616), replacing the hand-edit that was
the only way to reach it.

Implementation:
`frob.app.ticket_runner._close_cmd._apply_no_behavior_change_directive`
writes the directive via `frob.tickets.set_body` (T-2392's validated
mutation path, this ticket's own precedent) BEFORE `_close` computes
`mutation_evidence`, so the SAME `_no_behavior_change_reason` parser
BUG002 already reads (`frob.gates._mutation_evidence`) sees it. Reason is
mandatory (exits 1 if blank/missing). CLI flags added to
`_add_ticket_close_parser` (src/frob/_cli_parsers/_ticket/_closeout.py),
AppConfig fields in src/frob/app/config.py.

BUG002 was NOT touched or weakened: TestGateNotWeakened::
test_confirmatory_only_without_directive_still_refused proves a ticket
with genuinely confirmatory-only evidence and no directive is still
refused; test_directive_present_inverts_to_must_still_pass proves this
front door reaches the SAME pre-existing T-1616 inversion logic, not a
new/separate one.

Friction encountered (as briefed): the same _config_external.py lease
collision T-2392 hit reappeared here initially -- but T-2387 landed mid-
session and released its lease, so this ticket picked up the scope and
wired BOTH T-2392's and T-2393's new AppConfig fields into
_STRING_FIELDS/_PATH_FIELDS/_BOOL_FLAGS directly, closing the gap for
real (not just documenting it). tests/unit/test_app_config_flag_
coverage.py's existing static check (find_dropped_cli_flags) confirms
zero dropped flags with these fields present; TestRealArgvParsing adds
two explicit real-argv-through-the-real-parser tests (T-1927/T-2387's
own precedent shape) for `frob ticket body` and `frob ticket close
--no-behavior-change`. Dropped the T-2402 follow-up (absorbed here)
since its fix landed as part of this ticket instead.

BUG002: repro test committed alone first (fe8fdb6cc), confirmed
FAILED_AT_PARENT, fix committed on top, --designate-repro validated
against fe8fdb6cc as base-ref.

### Changed
```
 docs/modules/tickets-data-storage.md       |  23 ++++
 src/frob/_cli_parsers/_ticket/_closeout.py |  32 ++++++
 src/frob/app/config.py                     |   9 ++
 src/frob/app/ticket_runner/_close_cmd.py   |  86 +++++++++++++++
 tests/test_bug002_no_behavior_change.py    | 163 +++++++++++++++++++++++++++++
 tickets/T-2393/ticket.md                   |  55 +++++++++-
 tickets/T-2402/ticket.md                   |   5 +-
 7 files changed, 368 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_flag_writes_directive_before_close` (pytest node id, verified passing when recorded)
- `tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_reason_missing_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/test_bug002_no_behavior_change.py::TestNoBehaviorChangeCli::test_flag_absent_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_bug002_no_behavior_change.py::TestGateNotWeakened::test_confirmatory_only_without_directive_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_bug002_no_behavior_change.py::TestGateNotWeakened::test_directive_present_inverts_to_must_still_pass` (pytest node id, verified passing when recorded)
- `tests/test_bug002_no_behavior_change.py::TestRealArgvParsing::test_close_no_behavior_change_flags_survive_real_argv_parsing` (pytest node id, verified passing when recorded)
- `tests/test_bug002_no_behavior_change.py::TestRealArgvParsing::test_body_append_flags_survive_real_argv_parsing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, DUP001@tests/test_bug002_no_behavior_change.py, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/dev-friction/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, invalid-argument-type@src/frob/app/ticket_runner/_close_cmd.py
