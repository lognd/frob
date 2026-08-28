## Done report

Changed:
- src/frob/gates/_waive.py::waive010_violations (new)
- src/frob/gates/_waive.py::_waive010_violation (new)
- src/frob/gates/_waive.py::_reason_reads_as_deferred_work (new)
- src/frob/gates/_waive.py::_WAIVE010_DEFERRED_PHRASE_RES (new)
- src/frob/gates/_waive.py::_KNOWN_GATE_RULES (added WAIVE010)
- src/frob/gates/__init__.py (wired waive010_violations into run_gates,
  alongside waive009_violations)
- docs/modules/gates.md (WAIVE010 rule-catalog row + frob:enumerates
  members list)
- tests/test_waive_gate.py::TestWaive010Violations (new)
- tests/test_waive_gate.py::TestReasonReadsAsDeferredWork (new)

Discriminator (WARN severity, as required):
`_reason_reads_as_deferred_work` fires on WORDING only -- it reuses
WAIVE009's own curated `_WAIVE009_PROMISE_PHRASE_RES` set (already
tuned against this repo's real waivers) plus four bare temporal words
the owner named directly: "until", "pending", "for now", "temporarily".
It deliberately does NOT take a TicketQueue and does NOT key on whether
a cited ticket resolves -- that was the measured trap: 767 waivers cite
only RESOLVED tickets, and a resolved-ticket citation is also the
NORMAL shape of the legitimate PROVENANCE case ("T-1024: deliberately
dead because <reasoning established there>" -- the ticket is why, not
what fixes it). Citation-resolution state cannot separate PROVENANCE
from DEFERRED WORK; only wording can, so this rule ignores citation
state entirely and fires purely on temporal/promise phrasing. Verified
directly: a fixture with a PROVENANCE-shaped reason citing a ticket
(test_provenance_reasoning_does_not_warn) stays silent; a fixture with
a DEFERRED-WORK-shaped reason citing a RESOLVED ticket still warns
(test_promise_phrase_with_resolved_ticket_still_warns).

Real-repo calibration (measured, not estimated): ran waive010_violations
directly against this worktree's own graph snapshot.
- First pass: 14 findings. Hand-reviewed all 14 against their surrounding
  reason text. One was a clear FALSE POSITIVE: bare `\bpending\b` matched
  the word "pending" inside the FILENAME
  `pending-background-guard.py` (a real sibling hook this repo's own
  comments reference), not temporal wording.
- Fixed: added `(?<!-)`/`(?!-)` guards to the `until`/`pending` patterns
  so they no longer match inside a hyphenated identifier/filename.
  Re-measured: 13 findings, filename false positive gone. Added two
  regression tests for this exact shape
  (test_pending_inside_a_filename_does_not_match,
  test_until_inside_a_hyphenated_token_does_not_match).
- Disclosed residual false-positive class (not fixed, out of a WARN
  rule's reasonable precision bar per this ticket's own instruction to
  favor a small honest miss rate over a large one): two of the 13
  remaining hits use "until" in a way that is NOT about the waiver's own
  temporariness -- src/frob/serve/_events.py uses "read frames until a
  match or timeout" (describing loop control flow, not the waiver's
  duration), and src/frob/tickets/_worktree_sweep.py uses "untouched by
  recent diffs until now" (historical narration, not a live promise).
  Two more (src/frob/gates/_waive.py's own top-of-file waiver and
  tests/test_tickets_gate_claim_evidence.py) narrate a PAST lease
  conflict that has since been explicitly reviewed and reaffirmed
  permanent -- genuinely borderline, since the reason text as written
  still reads temporal even though the current intent is not. These
  four are left firing (WARN, not ERROR) rather than special-cased,
  since a bespoke exemption for each real site risks becoming the same
  regex-chasing this ticket's own instructions warned against; a human
  reviewing a WARN can reword the four flagged reasons to state their
  now-permanent intent plainly, which stops the rule (this is called out
  directly in the WAIVE010 violation message).
- Net: 9 of 13 flagged sites are unambiguous DEFERRED-WORK misuse (a doc
  sync/wiring/lease-clearing promise embedded only in prose); 4 are a
  disclosed, narrow, WARN-only residual. 13 total against a corpus of
  2117 frob:waive uses is not the "huge false-positive rate" the ticket
  asked me to avoid shipping.

Filed: none

Gates: `frob check --only lint --ticket T-3062` -- ruff-check clean, this
ticket's own touched files (_waive.py, gates/__init__.py,
test_waive_gate.py) not present in the repo-wide ruff-format debt list.
`pytest tests/test_waive_gate.py` (deselecting the one pre-existing,
unrelated TestWaive006RealRepo failure on src/frob/gates/_rule_id_scan.py,
a file this ticket never touches) -- 73 passed before this change, 85
passed after (12 new).

### Changed
```
 tickets/T-3062/ticket.md | 41 ++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 40 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive010Violations::test_bare_until_wording_warns` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive010Violations::test_pending_wording_warns` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive010Violations::test_promise_phrase_with_resolved_ticket_still_warns` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive010Violations::test_provenance_reasoning_does_not_warn` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive010Violations::test_plain_permanent_reason_does_not_warn` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive010Violations::test_known_gate_rule_ids_includes_waive010` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestReasonReadsAsDeferredWork::test_until_matches` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestReasonReadsAsDeferredWork::test_for_now_matches` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestReasonReadsAsDeferredWork::test_temporarily_matches` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestReasonReadsAsDeferredWork::test_plain_reason_does_not_match` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestReasonReadsAsDeferredWork::test_pending_inside_a_filename_does_not_match` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestReasonReadsAsDeferredWork::test_until_inside_a_hyphenated_token_does_not_match` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 61 error(s), 1218 warning(s), 860 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3063/ticket.md, DOC006@tickets/T-3066/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3062, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
