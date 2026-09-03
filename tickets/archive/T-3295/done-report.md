## Done report

MEASUREMENT (done before any design, per instruction): the owner's cited
2656/21:1 figures were a git-grep LINE count, not a directive count (every
continuation line and prose mention counted separately). Re-measured
against the graph-resolved population WAIVE009 actually iterates
(_waive_edges(snapshot)): 1468 real frob:waive directives, of which 13
(0.9%) trip _reason_promises_followup. Corrected denominator against
main's 124 frob:debt entries: ~12:1, not 21:1. This is an afternoon, not
a ratchet -- confirmed by the actual fix size below.

FIX: waive009_violations (src/frob/gates/_waive.py) now fires on ANY
promise-phrase reason, unconditionally -- the queue-consulted
ticket-resolution branch that used to make a resolvable-ticket citation
pass is gone, along with the queue parameter itself (dropped from the
signature; the call site in gates/__init__.py updated). T-2606's original
conclusion read `frob:waive RULE reason="deferred, see T-1234"` as clean;
per the owner's own framing, naming a ticket makes the promise
accountable, it does not make the classification correct. WAIVE009's
catalog row in docs/modules/gates.md corrected to match.

DETECTOR CEILING (explicit, per instruction -- do not read 13 as the size
of the problem): 13/1468 is a LOWER BOUND set by what
_reason_promises_followup's curated phrase set can recognise
syntactically (grep-shaped regexes over prose, not semantic
understanding). A reason like "this is wrong but out of scope here" is
debt by the owner's own definition and would NOT trip this detector. The
real misclassification count in this repo is unknown; the detector is
the limiting factor, not evidence that 13 is the whole problem.

DETECTOR FALSE POSITIVE (found, reported, NOT used to weaken the
detector): tests/test_tickets_gate_claim_evidence.py's SCOPE001 waiver
matched "once the lease clears" phrasing but describes a PERMANENT
git-history scope binding (T-1399/T-1235 both long done; the file's
scope citation is fixed by history and will never change) -- promise-
shaped language describing something that is not deferred work at all.
Reworded in place (kept as frob:waive, stale "once X clears" framing
removed) rather than converted; the next person tuning
_reason_promises_followup should know this phrasing class exists.

DISPOSITION OF THE 13, checking each cited follow-up's premise before
converting (per instruction) -- 6 of 13 were fully discharged directly,
not converted to debt:
- 5 sites (bind/clean/fmt/map/test_runner.py, shared T-2492 boilerplate
  reason): DELETED outright. Verified T-2491 (the cited follow-up) is
  DONE and its Done report explicitly landed the promised
  docs/modules/app.md sync -- re-measured, the doc now documents the
  guard. Transcribing this into frob:debt would have manufactured fake
  obligation for work already finished.
- 1 site (_leases.py::is_effectively_in_progress): its cited follow-up
  T-2003 is DONE and its Done report added the promised anchor
  (docs/modules/tickets-landing.md, confirmed present) -- added the
  frob:doc directive directly onto the symbol and dropped the waiver.
  No debt needed; the work was already done, only the code-side citation
  was missing.
- 6 sites (4x process/parsers/common.py citing T-2391's measurement
  fields; _docstatus.py's docstatus_gate; _rapid_sweep.py's
  revalidate_dispatchable_sweep_tickets): re-measured each cited doc,
  confirmed the promised sync genuinely never happened despite the
  blocking leases having long cleared. Converted to frob:debt: 4 sites
  cite the already-open T-3206; 2 sites needed new tickets (T-3348 for
  the DOC011 catalog row, T-3349 for tickets-verify-sweep.md), since no
  existing open ticket tracked either gap.
- 1 site: the SCOPE001 false positive above, reworded not converted.

LANDING SEQUENCE (per coordinator direction): land this fix +6 debt
entries first (REL001 correctly blocks release while they're open --
that is the fix working, not collateral: these were real, unfixed
obligations sitting behind waivers pretending the rule did not apply).
Then discharge all 6 by actually doing the doc syncs T-3206/T-3348/T-3349
describe, closing those tickets -- net effect: 13 misclassified waivers
gone, 6 hidden obligations actually discharged, zero new errors left on
the floor.

ARCHITECTURE FINDING, filed as T-3355, deliberately NOT fixed here (a
real design call, not this ticket's scope): frob:debt does not actually
suppress the gate finding it documents suppressing.
docs/guides/extending/comment-dsl-directives.md states "frob:debt
suppresses a GATE FINDING (the symptom)" but _apply_waivers (the actual
suppression mechanism run_gates calls) only reads EdgeKind.WAIVE via
_waive_edges/_waivers_by_rule -- EdgeKind.DEBT is never consulted there.
Verified empirically: converting the 6 sites above to frob:debt made
their AFFECT001/COV001 findings reappear LIVE rather than staying
suppressed as documented.

Evidence: tests/test_waive_gate.py (TestWaive009Violations,
TestWaive009PromisePhraseDetection, TestWaive009TicketIdExtraction,
TestWaive009Wiring -- 22 node ids, all passing), tests/unit/test_process.py
(38 node ids, all passing), tests/test_tickets_gate_claim_evidence.py,
tests/unit/test_land_cross_ticket_leakage.py, tests/unit/test_app_runners_batch5.py,
tests/unit/test_app_runners_t0875_leaf_collision.py, tests/test_app.py,
tests/unit/test_rapid_sweep.py -- 288 node ids total, all passing.
frob test --base main: 13/13 selected python tests passing.

Filed: T-3348 (add DOC011 catalog row for docstatus_gate), T-3349 (sync
docs/modules/tickets-verify-sweep.md for T-2521), T-3355 (frob:debt
suppression-mechanism finding, architecture-level, deferred to owner).

Gates: frob check --ticket T-3295 clean on the diff-scoped checks
(SCOPE/PREWORK/COV002/AFFECT/FMT against this ticket's own touched set).
AFFECT001/COV001 on the 6 converted sites are the newly-visible debt
described above, not a defect in this diff -- next step (T-3206/T-3348/
T-3349) discharges them.

### Changed
```
 docs/modules/gates.md                      |   4 +-
 docs/modules/process.md                    |  43 +++++++++
 docs/modules/tickets-verify-sweep.md       |  19 ++++
 src/frob/app/bind_runner.py                |   4 -
 src/frob/app/clean_runner.py               |   5 --
 src/frob/app/fmt_runner.py                 |   4 -
 src/frob/app/map_runner.py                 |   5 --
 src/frob/app/test_runner.py                |   4 -
 src/frob/app/ticket_runner/_rapid_sweep.py |   9 +-
 src/frob/gates/__init__.py                 |   9 +-
 src/frob/gates/_docstatus.py               |  10 +--
 src/frob/gates/_waive.py                   |  82 +++++++++++------
 src/frob/process/parsers/common.py         |  27 ++----
 src/frob/tickets/_leases.py                |   7 +-
 tests/test_tickets_gate_claim_evidence.py  |  18 ++--
 tests/test_waive_gate.py                   |  58 +++++++-----
 tickets/T-3295/done-report.md              | 139 +++++++++++++++++++++++++++++
 tickets/T-3295/ticket.md                   | 128 +++++++++++++++++++++++++-
 tickets/archive/T-2606/ticket.md           |  17 +++-
 tickets/archive/T-2639/ticket.md           |   9 +-
 20 files changed, 468 insertions(+), 133 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_no_ticket_id_errors` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_resolvable_ticket_id_still_errors` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_unresolvable_ticket_id_errors` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_draft_ticket_id_still_errors` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Violations::test_no_promise_phrase_untouched` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Wiring::test_unresolvable_promise_fires_through_run_gates` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Wiring::test_resolvable_promise_also_fires_through_run_gates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 78 error(s), 5050 warning(s), 880 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/verify_release_ci_status.py, COV007@src/frob/tickets/_done_report.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@docs/modules/cli.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/gates/_comment_placement.py, DOC007@src/frob/gates/_docstring_archaeology.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DOC011@docs/guides/release.md, DRIFT001@scripts/fleet_status.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/doctor.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/gates/_comment_placement.py, DRIFT002@src/frob/gates/_docstring_archaeology.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3295, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
