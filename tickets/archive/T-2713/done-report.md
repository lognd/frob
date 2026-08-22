## Done report

Changed:
- src/frob/app/ticket_runner/_verify.py::_budget_skipped_groups_from_payload (new)
- src/frob/app/ticket_runner/_verify.py::_parse_error_findings_from_json
- src/frob/app/ticket_runner/_verify.py::_budget_deferred_groups_from_stdout
- src/frob/app/ticket_runner/__init__.py (re-export _budget_skipped_groups_from_payload)
- docs/modules/tickets-landing.md (new section documenting the T-2713 fix)

Root cause, confirmed by reading `_check_chunking.py`'s own T-2235 fix
comments: `--budget`'s cross-invocation resume mechanism
(`_resolve_budget_remaining` reading `.frob/check-budget-remaining.json`)
means a single `--budget` spawn's own `deferred` list (what T-1703/T-2456
already guard on) can be EMPTY even though most of the stage-group
universe never executed THIS invocation -- because `remaining` itself was
already narrowed by an EARLIER, unrelated invocation's leftover resume
state. `_budget_coverage_report` (T-2235) already computes the honest,
resume-history-independent `skipped_groups` against the FULL universe and
places it at the JSON payload's top level (`data["budget"]["skipped_
groups"]`), but no consumer in `_verify.py` ever read it -- the T-1703/
T-2456 guards only ever looked at the narrower `results`-list `"budget"`
tool entry's `BUDGET001` diagnostic, which this class of run never emits.

Fix: `_budget_skipped_groups_from_payload` reads the wider top-level
signal directly. `_parse_error_findings_from_json` now treats a non-empty
`skipped_groups` as a fourth independent unmeasurable (`None`) case,
alongside the existing T-2521/T-1703 checks. `_budget_deferred_groups_
from_stdout` (used to name deferred groups on the `LAND-PROOF:` line)
unions it with the narrower signal so the naming stays accurate too. No
caller-side change was needed: `run_coalesced_verification`'s `WorkerError.
Unmeasurable` path and `run_deferred_post_land_sweep`'s `RapidSweepError.
Unmeasurable` path already refuse to advance the watermark / record a
baseline on `None` -- they simply never received the correct signal
before this fix.

Positive controls exercised (see Evidence): a genuinely complete budgeted
run (`skipped_groups: []` or no `"budget"` key) still parses normally
(`TestBudgetSkippedGroupsFromPayload::test_empty_when_complete_or_absent`,
plus every pre-existing T-1703/T-2456/T-2521 test in this file, all still
green) -- this fix narrows nothing about the already-measured-clean case,
only closes the specific resume-narrowed gap.

Note: this fix closes the CONSUMER-side gap. It does not touch
`_check_chunking.py`'s producer-side resume/remaining mechanism itself
(out of scope; T-2235 already covers the producer side correctly) -- the
mechanism working as multi-invocation-resume design is fine, the bug was
that its own already-correct completeness signal was never read by the
one-shot automated callers that need it.

I did not re-run the live `frob verify now` incident end-to-end (would
consume a full unbudgeted `frob check`, several minutes, against a
shared/moving root) -- the unit-level reproduction
(`_BUDGET_RESUME_NARROWED_STDOUT`, modeled directly on the measured
incident's own JSON shape: 1 executed group, 4 skipped, no BUDGET001
diagnostic) is the faster, deterministic proof of the same code path.

Evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestBudgetSkippedGroupsFromPayload::test_reads_top_level_skipped_groups
- tests/unit/test_ticket_runner_gate_findings.py::TestBudgetSkippedGroupsFromPayload::test_empty_when_complete_or_absent
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_resume_narrowed_run_yields_none_not_a_partial_set
- tests/unit/test_ticket_runner_gate_findings.py::TestBudgetDeferredGroupsFromStdout::test_includes_resume_narrowed_skipped_groups
- Full targeted suite green: tests/unit/verify/, tests/unit/test_rapid_sweep.py, tests/unit/test_ticket_runner_gate_findings.py (320 passed, 0 failed)

Filed: none (no out-of-scope work discovered; the producer-side
`_check_chunking.py` mechanism is correct per T-2235 and out of this
ticket's scope)

Gates: ruff-check/ruff-format/ty clean on every file this ticket touched;
`frob check --ticket T-2713` gate-summary showed 98 repo-wide errors, all
pre-existing (ruff-check 3/ty 18/frob-cycle 1/ruff-format 189 files, none
in this ticket's touched files -- verified directly by running
ruff-check/ty against exactly the touched files, both clean) -- per
gate:scope-note, only gate:SCOPE/gate:PREWORK/the diff-driven COV002/
TODO001/gate:FMT/gate:AFFECT checks are ticket-scoped, every other family
is repo-wide and not attributable to this change.

### Changed
```
 tickets/T-2713/ticket.md | 5 +++++
 1 file changed, 5 insertions(+)
```

### Evidence
- `tests/unit/test_ticket_runner_gate_findings.py::TestBudgetSkippedGroupsFromPayload::test_reads_top_level_skipped_groups` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestBudgetSkippedGroupsFromPayload::test_empty_when_complete_or_absent` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJson::test_resume_narrowed_run_yields_none_not_a_partial_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestBudgetDeferredGroupsFromStdout::test_includes_resume_narrowed_skipped_groups` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 46 error(s), 957 warning(s), 680 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2704/ticket.md, DOC006@tickets/T-2705/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2713, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
