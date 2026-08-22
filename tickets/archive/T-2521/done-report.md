## Done report

DETERMINATION: candidate 1 (NOT_MEASURED collapsing into NOT_PRESENT),
not candidate 2 (path shape) -- established by direct evidence, not
assumption.

Path-shape check: read all seven dropped tickets' bodies directly.
T-2515's drop reason quotes the identity in NORMALIZED relative form
(src/frob/testing/_collect_kotlin.py), proving _normalize_identities
(T-2036) correctly relativized the recorded absolute-path identity
before the comparison ran. Path shape was NOT the cause of these
specific drops.

Incompleteness check: read T-2504's own deferred-sweep log
(.frob/rapid-sweep/T-2504-5f01c7b01120.log). It shows NO BUDGET001
deferral warning and a genuinely completed run: "recorded rolling
baseline of 0 error(s)" / "deferred unscoped sweep CLEAN (0 error(s))".
Confirmed the two files named in the dropped tickets (created by T-2409
and T-2492, both landed well before T-2504, both never touched since)
could not have been genuinely fixed-then-regressed -- their content is
unchanged. Reproduced live: ran `frob check --budget 480 --json` on
main just now (a genuinely completed run, no BUDGET001) and confirmed
E501/F811 both present with severity=error for these exact files.

Traced the mechanism: frob.process.parsers.ruff.parse_ruff_json's
malformed-JSON fallback returns ToolResult(exit_code=1, diagnostics=[],
summary="malformed JSON: ...") -- unlike sibling helpers tool_crash_
result/tool_disabled_result (frob.process.parsers.common), it does NOT
attach an error Diagnostic explaining the failure, violating this
repo's own loud-not-silent convention. Both consumers of a `frob check
--json` payload's error-finding identity set --
_verify.py::_collect_error_findings (deferred sweep) and
_rapid_sweep.py::_matching_error_diagnostics (doable-time
revalidation) -- only ever iterate `diagnostics`, never check
`exit_code`. A ruff-check crash under fleet contention (plausible: 7
tickets auto-dropped in one sweep suggests heavy concurrent load at
that moment) reads as "ran, found nothing" to both, exactly matching
the measured "0 errors" outcome.

FIX: added _incomplete_tool_results (frob.app.ticket_runner._verify) --
a STRUCTURAL check (exit_code nonzero AND no error-severity diagnostic
present), never a substring match on summary prose. Wired into both
consumers: a run with any incomplete tool result now returns None
(unmeasured), the same posture --budget deferral already had. Auto-drop
reason text (_maybe_drop_resolved_ticket) now names what was actually
measured via a threaded measurement_note parameter instead of only
asserting absence.

REQUIRED BEHAVIOUR:
1. Auto-drop refuses on incomplete measurement -- both call sites now
   propagate None through the exact same "never drop on None" path the
   --budget check already used; no new drop logic needed, only a wider
   completeness signal feeding the existing refusal.
2. Drop reason states completeness -- measurement_note threaded through
   _maybe_drop_resolved_ticket/_close_resolved_sweep_tickets/_close_and_
   log_resolved_sweep_tickets/revalidate_dispatchable_sweep_tickets;
   each caller supplies text naming exactly what ran (a full unscoped
   run with no deferral/failure, vs. a scoped direct re-check of N
   identities).
3. Path normalization both sides -- already correct (T-2036); added an
   explicit end-to-end positive control (test below) proving an
   absolute-recorded identity matches a relative-measured one through
   the real drop path, not just the isolated _normalize_identities unit
   tests.

POSITIVE CONTROLS, both directions, all present:
- genuinely-vanished ticket still auto-drops:
  test_drops_a_fully_resolved_sweep_ticket (pre-existing, still green
  after this change -- confirms the fix does not disable the
  mechanism).
- live ticket does not drop on incomplete measurement:
  test_failed_silent_tool_result_yields_none_not_a_partial_set (the
  reproduced defect shape, verify.py level) and
  test_failed_silent_tool_result_is_unmeasurable_not_zero
  (_rapid_sweep.py level, doable-time path).
- failed-but-loud tool (control against over-refusing):
  test_failed_but_loud_tool_result_does_not_block_measurement --
  proves a tool that failed AND reported a real error diagnostic does
  NOT get treated as incomplete, so the fix does not quietly disable
  auto-drop for every crash.
- absolute-vs-relative identity match:
  test_absolute_recorded_identity_matches_relative_vanished_entry, an
  end-to-end test through the real drop path.

NOT done in this ticket, per its own explicit instruction: re-filing
the ~66 lost identities from the seven dropped tickets. Most are
already visible in the current unscoped floor.

Also not done: patching parse_ruff_json (and the sibling eslint.py
malformed-JSON fallback with the identical shape) to attach a real
error Diagnostic matching tool_crash_result's convention -- the fix
above closes the auto-drop hazard structurally regardless of whether
that upstream gap is ever closed, and touching process/parsers/ is
outside this ticket's scope; worth a follow-up if the coordinator wants
the underlying silent-tool-result convention closed everywhere, not
just guarded against at this one consumer.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py     |  70 ++++++++++++--
 src/frob/app/ticket_runner/_verify.py          | 114 ++++++++++++++++++++++-
 tests/unit/test_rapid_sweep.py                 |  66 ++++++++++++++
 tests/unit/test_ticket_runner_gate_findings.py | 119 ++++++++++++++++++++++++
 tickets/T-2521/done-report.md                  | 117 ++++++++++++++++++++++++
 tickets/T-2521/ticket.md                       | 121 ++++++++++++++++++++++++-
 6 files changed, 595 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_failed_silent_tool_result_yields_none_not_a_partial_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_failed_but_loud_tool_result_does_not_block_measurement` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_absolute_recorded_identity_matches_relative_vanished_entry` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_drops_a_fully_resolved_sweep_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestIdentitiesStillReproducing::test_failed_silent_tool_result_is_unmeasurable_not_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2521/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2521/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2521/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2521/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2521/tests/unit/test_ticket_runner_repro_merge_base.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2521/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2521, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
