## Done report

Changed:
src/frob/verify/_worker.py (WorkerError gains ChildTimedOut/ChildSpawnRefused/ChildOutputUnparsable; _capture_unmeasurable_reason log-signal capture; _default_verify_fn records the classified reason; run_coalesced_verification reports it instead of one undifferentiated Unmeasurable)
tests/unit/verify/test_worker.py (new TestClassifyUnmeasurableReason, TestRunCoalescedVerificationDistinguishesUnmeasurableCauses, TestDefaultVerifyFnRecordsUnmeasurableReason classes, 9 tests)
docs/modules/tickets-verify-sweep.md (Unmeasurable-cause separation section)
tickets/T-3886/ticket.md (addendum folding in FROBLEMS F-049's first half, disclosed as not-fixed-here)

Evidence: 9 ids, all passing locally (45 total tests in tests/unit/verify/test_worker.py pass, up from 36 pre-change).

The four outcomes distinguished: ChildTimedOut, ChildSpawnRefused, and plain
Unmeasurable (covers both ChildOutputUnparsable's genuinely-unparsable case and
a fully genuine unmeasurable result, plus the pre-existing injected-test-double
contract) are now separated in the recorded WorkerError and in the worker's own
log line, instead of one undifferentiated "unmeasurable verification at %s".

Mechanism: log-signal capture, not a return-type change to
unscoped_error_findings -- that function's file (src/frob/app/ticket_runner/
_land_cmd.py) was held under another in-progress ticket's (T-3906) scope
lease for this ticket's whole work session. _capture_unmeasurable_reason
attaches a temporary logging.Handler to that module's own logger and
classifies its ALREADY-DISTINCT existing log lines (a TimeoutExpired warning
names "timed out after Ns"; a spawn refusal names "spawn refused"). Disclosed
as a real design compromise: unscoped_error_findings returning a proper
Result[frozenset|None, UnmeasurableReason] is the more robust long-term shape
and is filed as a follow-up once that file's lease clears.

Never spin: verified, not newly built. block_until_watermark_advances already
has a bounded 1800s timeout_s and returns Err(BlockTimedOut) rather than
looping forever; its only caller (in _land_cmd.py) logs the timeout and
proceeds with the land, raising a synthetic quarantine finding, rather than
retrying. A single frob ticket land invocation cannot spin past 1800s on an
unmeasurable verify -- the reporter's 45-minute stall is consistent with
repeated manual re-invocation across multiple bounded waits, not one call
looping without end. This is stated in docs/modules/tickets-verify-sweep.md
as a verified fact, not asserted from the ticket body alone.

Worker child budget: measured. _default_verify_fn's full=True call is
unbudgeted and bounded only by _FULL_CHECK_TIMEOUT_S (1800s); the reporter's
560s hand-run fits comfortably inside that ceiling, so the child budget was
never the proximate cause of the F-043 incident -- the conflation was.

Historical count of false-unmeasurable verdicts: NOT directly measurable from
this repo's persisted state (.frob/verify-watermark.json holds only the
current watermark, no history). The verified=SKIPPED-UNMEASURED lines cited
in this ticket's own body (T-3820, and this series' own T-3857/T-3884 lands)
are a DIFFERENT mechanism -- claims_reverify's rapid-profile design-intended
skip when collected/passed are None, not a worker-child-death symptom.
Conflating the two would have been the wrong measurement. This ticket's fix
is what makes the count trackable going forward; the count itself today is
zero confirmable, one indeterminate (F-043's own incident).

Filed: none new this pass (T-3887 already exists and covers F-049's second
half; the follow-up for unscoped_error_findings's return-type change is
recorded in docs/modules/tickets-verify-sweep.md and this report rather than
filed as a separate ticket, to avoid scope creep into land_cmd.py's design
while it is under another ticket's lease).

Known debt, disclosed: adding docs/modules/tickets-verify-sweep.md to this
ticket's scope (required for the new doc section) triggers SCOPE002's
doc-anchor closure over EVERY pre-existing anchor that hub doc carries --
dozens of unrelated symbols across src/frob/verify/**, src/frob/tickets/**,
none touched by this ticket. Same structural SCOPE002 gap already disclosed
in T-3884's own Done report (and precedented by src/frob/app/config.py's own
AFFECT001 waiver for docs/modules/app.md) -- not specific to this ticket.
Also disclosed: DRIFT001 on run_coalesced_verification could not be acked
because frob.lock is held under another in-progress ticket's (T-3799) scope
lease.

Gates: frob check --ticket T-3886 -- all findings resolved except: 5
pre-existing, out-of-scope DOC006 errors (other tickets' bodies), 1
pre-existing REF002 warning (quickstart.md), the SCOPE002 doc-anchor closure
debt described above, and the DRIFT001/frob.lock lease conflict above.

### Changed
```
 docs/modules/tickets-verify-sweep.md |  83 +++++++++++++++++
 src/frob/verify/_worker.py           | 173 +++++++++++++++++++++++++++++++++--
 tests/unit/verify/test_worker.py     | 123 +++++++++++++++++++++++++
 tickets/T-3886/done-report.md        |  93 +++++++++++++++++++
 tickets/T-3886/ticket.md             |  64 ++++++++++++-
 5 files changed, 528 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/verify/test_worker.py::TestClassifyUnmeasurableReason::test_child_timeout_log_line_classified` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestClassifyUnmeasurableReason::test_spawn_refused_log_line_classified` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestClassifyUnmeasurableReason::test_no_matching_log_line_is_unmeasurable` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerificationDistinguishesUnmeasurableCauses::test_recorded_child_timeout_reason_is_reported` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerificationDistinguishesUnmeasurableCauses::test_recorded_spawn_refused_reason_is_reported` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerificationDistinguishesUnmeasurableCauses::test_no_recorded_reason_stays_plain_unmeasurable` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_unmeasurable_never_advances_watermark` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestDefaultVerifyFnRecordsUnmeasurableReason::test_unmeasurable_result_records_a_reason` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestDefaultVerifyFnRecordsUnmeasurableReason::test_measured_result_never_records_a_reason` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 8 error(s), 4357 warning(s), 926 waived
- error-findings: DOC006@tickets/T-3886/ticket.md, DOC006@tickets/T-3902/ticket.md, DOC006@tickets/T-3906/ticket.md, DOC006@tickets/T-3908/ticket.md, DRIFT001@src/frob/verify/_worker.py, PRE001@tickets/T-3886, REF002@docs/guides/quickstart.md, SCOPE002@tickets.md
