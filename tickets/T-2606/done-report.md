## Done report

WAIVE009 (`src/frob/gates/_waive.py`): a `frob:waive` reason that promises
deferred/future work (a follow-up ticket, "once X clears", "will file",
"a ... ticket will/updates/handles/fixes/tracks ...") but names no ticket
id that resolves in the queue is now an ERROR-tier gate finding. This
closes the exact T-2588/T-2598 gap this ticket was filed from: a
follow-up promised entirely in prose, with no ticket id anywhere in the
reason, previously had no mechanism that could ever surface it -- the
only record of the debt lived inside the comment suppressing the finding
it deferred.

Design notes:

- `_reason_promises_followup(reason)` is a narrow, calibrated phrase
  scan (not a general future-tense detector -- that would fire on
  ordinary "this will not affect X" reasoning that promises nothing to
  file). `_reason_ticket_ids(reason)` extracts every bare `T-\d+` (and
  `T-draft-<hex>`) token anywhere in the reason -- a wider net than
  WAIVE006's binding-phrase-only capture, since a WAIVE009 promise
  phrase's own presence is already the binding signal.
- If ANY extracted id resolves in the ticket queue (or is a
  `T-draft-*` id, mirroring WAIVE007's own exemption for in-flight
  drafts), the waiver passes WAIVE009 -- WAIVE006/007 already own that
  id's own staleness/dangling-ref honesty from there.
- Deliberately does NOT touch AFFECT001, or weaken any existing rule --
  this only adds a NEW check over the waiver comment itself.

Cut disclosed: `src/frob/gates/__init__.py` (where every other WAIVE00*
self-check is wired into `_assemble_gate_report`) was under T-2580's
live in-progress lease for this ticket's entire working window, and
`docs/modules/gates.md` (the gate catalog, for WAIVE009's own
subsection) was under T-2377's live lease at the same time -- both
`frob ticket scope --add` attempts refused with `ScopeLeaseConflict`.
WAIVE009 is fully implemented, unit-tested, and registered in
`_KNOWN_GATE_RULES`, but does NOT yet fire inside a real `frob check`
run until that one-line wiring call lands. Filed as a follow-up:
T-2639 (renumbers at land), scoped to exactly those two files,
with the one-line wiring call and the doc subsection spelled out in its
own plan.

Measured: `uv run pytest tests/test_waive_gate.py -p no:cacheprovider -q`
-- 54 passed, 0 failed (14 new WAIVE009 tests plus the 40 pre-existing
WAIVE006/007/RuleCensus/WAIVE004-dead-count tests in the same file, all
still green). `uv run frob check --only lint --ticket T-2606` -- 0 new
errors from this change (the two E501s this diff introduced were fixed
in the same pass); the remaining 2 errors/223 warnings in that run are
pre-existing and outside this ticket's scope (an unrelated F401 in
`ticket_runner/__init__.py`, a claude-config-drift finding, and the
repo-wide CRLF->LF reformat backlog from T-2611, all confirmed
unattributable to this diff).

### Changed
```
 src/frob/gates/_waive.py           | 148 +++++++++++++++++++++++++++++++++++++
 tests/test_waive_gate.py           | 128 +++++++++++++++++++++++++++++++-
 tickets/T-2606/ticket.md           |  41 +++++++++-
 tickets/T-2639/ticket.md |  76 +++++++++++++++++++
 4 files changed, 389 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_no_ticket_id_errors` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_resolvable_ticket_id_passes` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_unresolvable_ticket_id_errors` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_draft_ticket_id_resolves` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_no_promise_phrase_untouched` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_known_gate_rule_ids_includes_waive009` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_follow_up_ticket_phrasing_promises` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_once_x_clears_phrasing_promises` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_will_file_phrasing_promises` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_ordinary_reason_does_not_promise` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_historical_ticket_mention_does_not_promise` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009TicketIdExtraction::test_extracts_bare_mention` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009TicketIdExtraction::test_extracts_multiple` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009TicketIdExtraction::test_no_mention_yields_empty` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/gates/_waive.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t2606-t2622/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2606, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/gates/_waive.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
