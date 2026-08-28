---
id: T-2391
title: 'a zero-findings gate result is ambiguous: unmeasured and inapplicable gates
  report as green'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/parsers/common.py
- src/frob/check/__init__.py
- tests/unit/test_process.py
- tests/unit/test_check_measurement.py
- docs/commands/check.md
- tests/unit/test_app_runners_batch6.py
- tickets/T-3202/**
- tickets/T-3203/**
- tickets/T-3204/**
- tickets/T-3205/**
- tickets/T-3206/**
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/parsers/common.py
  reason: 'well-chosen subset: type-level MEASURED/NOT_MEASURED distinction as a computed
    ToolResult field (derived from existing UNRESOLVED-severity signal, no per-gate
    migration needed) plus CheckResult roster/JSON exposure; src/frob/check/_python.py
    and tests/unit/test_check.py excluded (leased by in-progress T-3191); new dedicated
    test file avoids that conflict; remainder filed as follow-up tickets'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'well-chosen subset: type-level MEASURED/NOT_MEASURED distinction as a computed
    ToolResult field (derived from existing UNRESOLVED-severity signal, no per-gate
    migration needed) plus CheckResult roster/JSON exposure; src/frob/check/_python.py
    and tests/unit/test_check.py excluded (leased by in-progress T-3191); new dedicated
    test file avoids that conflict; remainder filed as follow-up tickets'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_process.py
  reason: 'well-chosen subset: type-level MEASURED/NOT_MEASURED distinction as a computed
    ToolResult field (derived from existing UNRESOLVED-severity signal, no per-gate
    migration needed) plus CheckResult roster/JSON exposure; src/frob/check/_python.py
    and tests/unit/test_check.py excluded (leased by in-progress T-3191); new dedicated
    test file avoids that conflict; remainder filed as follow-up tickets'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_check_measurement.py
  reason: 'well-chosen subset: type-level MEASURED/NOT_MEASURED distinction as a computed
    ToolResult field (derived from existing UNRESOLVED-severity signal, no per-gate
    migration needed) plus CheckResult roster/JSON exposure; src/frob/check/_python.py
    and tests/unit/test_check.py excluded (leased by in-progress T-3191); new dedicated
    test file avoids that conflict; remainder filed as follow-up tickets'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/commands/check.md
  reason: 'doc-closure: adding a new public ToolResult/CheckResult field requires
    updating this anchor doc'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: T-2486's byte-identical JSON contract test hardcodes ToolResult's field
    set; adding measurement/measurement_reason genuinely changes that shape and this
    pre-existing test's expected dict must be updated in the same change
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tickets/T-3202/**
  reason: frob ticket new for the four required T-2391 follow-up tickets writes tickets/T-draft-*/ticket.md
    before renumbering -- a machinery side effect of filing this ticket's own required
    follow-up work, not scope creep (T-3172 precedent)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3203/**
  reason: frob ticket new for the four required T-2391 follow-up tickets writes tickets/T-draft-*/ticket.md
    before renumbering -- a machinery side effect of filing this ticket's own required
    follow-up work, not scope creep (T-3172 precedent)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3204/**
  reason: frob ticket new for the four required T-2391 follow-up tickets writes tickets/T-draft-*/ticket.md
    before renumbering -- a machinery side effect of filing this ticket's own required
    follow-up work, not scope creep (T-3172 precedent)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3205/**
  reason: frob ticket new for the four required T-2391 follow-up tickets writes tickets/T-draft-*/ticket.md
    before renumbering -- a machinery side effect of filing this ticket's own required
    follow-up work, not scope creep (T-3172 precedent)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tickets/T-3206/**
  reason: frob ticket new for the doc-anchor follow-up ticket writes tickets/T-3206/ticket.md
    -- machinery side effect (T-3172 precedent)
  actor: logan
  at: '2026-08-28'
- op: add
  glob: rapid-debt.jsonl
  reason: close's REL001-preflight-skipped debt line is machinery bookkeeping written
    by frob ticket close itself, not scope creep
  actor: logan
  at: '2026-08-28'
- op: add
  glob: rapid-debt.jsonl
  reason: close's REL001-preflight-skipped debt line is machinery bookkeeping written
    by frob ticket close itself, not scope creep
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_process.py::TestToolResultMeasurement::test_measured_when_zero_diagnostics
- tests/unit/test_process.py::TestToolResultMeasurement::test_not_measured_when_every_diagnostic_is_unresolved_info
- tests/unit/test_process.py::TestToolResultMeasurement::test_measured_when_unresolved_mixes_with_a_real_warning
- tests/unit/test_process.py::TestToolResultMeasurement::test_non_gate_tool_is_never_not_measured
- tests/unit/test_process.py::TestToolResultMeasurement::test_json_discloses_measurement
- tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_empty_when_every_result_measured
- tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_lists_every_not_measured_result
- tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_section_absent_when_everything_measured
- tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_section_present_and_names_the_gate_and_reason
- tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_json_exposes_measurement_without_a_dedicated_key
- tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active
designated_repro_test: null
acceptance:
- text: Given a gate that could not run (budget truncation, refused spawn, missing
    tool, parse failure), when frob check reports, then that gate is reported as NOT_MEASURED
    with its reason in both human and --json output, and is never counted as a zero-findings
    pass.
  evidence:
  - tests/unit/test_process.py::TestToolResultMeasurement::test_measured_when_zero_diagnostics
  - tests/unit/test_process.py::TestToolResultMeasurement::test_not_measured_when_every_diagnostic_is_unresolved_info
  - tests/unit/test_process.py::TestToolResultMeasurement::test_measured_when_unresolved_mixes_with_a_real_warning
  - tests/unit/test_process.py::TestToolResultMeasurement::test_non_gate_tool_is_never_not_measured
  - tests/unit/test_process.py::TestToolResultMeasurement::test_json_discloses_measurement
  - tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_empty_when_every_result_measured
  - tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_lists_every_not_measured_result
  - tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_section_absent_when_everything_measured
  - tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_section_present_and_names_the_gate_and_reason
  - tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_json_exposes_measurement_without_a_dedicated_key
  - tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active
- text: Given a frob check run where any gate is unmeasured, when it completes, then
    the exit code and the printed summary both distinguish that run from one where
    every gate measured and found nothing.
  evidence:
  - tests/unit/test_process.py::TestToolResultMeasurement::test_measured_when_zero_diagnostics
  - tests/unit/test_process.py::TestToolResultMeasurement::test_not_measured_when_every_diagnostic_is_unresolved_info
  - tests/unit/test_process.py::TestToolResultMeasurement::test_measured_when_unresolved_mixes_with_a_real_warning
  - tests/unit/test_process.py::TestToolResultMeasurement::test_non_gate_tool_is_never_not_measured
  - tests/unit/test_process.py::TestToolResultMeasurement::test_json_discloses_measurement
  - tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_empty_when_every_result_measured
  - tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_lists_every_not_measured_result
  - tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_section_absent_when_everything_measured
  - tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_section_present_and_names_the_gate_and_reason
  - tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection::test_json_exposes_measurement_without_a_dedicated_key
  - tests/unit/test_app_runners_batch6.py::TestJsonStdoutStructuralGuard::test_legitimate_json_payload_is_byte_identical_with_guard_active
acceptance_amendments:
- op: remove
  index: 3
  old_text: Given a converted gate that returns a bare empty finding list without
    a status, when the meta-check runs, then it is reported, proving the doctrine
    is enforced structurally rather than by convention.
  new_text: null
  reason: deferred to follow-up T-3202 (GATESTATUS001 meta-check) -- see
    T-2391's own Done report for the explicit cut; T-1662's own standard forbids implementing
    a lexical-pattern-matching meta-check without a design pass first
  actor: logan
  at: '2026-08-28'
- op: remove
  index: 1
  old_text: Given a project declaring no surface for a given gate, when that gate
    runs, then it reports NOT_APPLICABLE with an explanation rather than a silent
    zero.
  new_text: null
  reason: deferred to follow-up T-3205 (per-gate NOT_APPLICABLE self-declaration
    for a hardcoded-layout-style gate) -- see T-2391's own Done report for the explicit
    cut; needs a per-gate declared-surface resolver this generic aggregation-layer
    change cannot provide
  actor: logan
  at: '2026-08-28'
threat: null
component: gates
labels:
- doctrine
- fail-loudly
anchor: false
anchor_reason: null
land_commit: null
---
USER DOCTRINE, 2026-08-18: "a zero-findings result must follow the
fail-loudly doctrine." A gate reporting zero must PROVE it measured
something. Today a zero is ambiguous across four very different states,
and the reporting layer collapses all of them into "green":

    measured, genuinely clean          -> green, correct
    could not run (budget/spawn/parse) -> reads as green, WRONG
    nothing to measure (no declared
      surface for this project)        -> reads as green, WRONG
    matcher silently never fired
      (path shape, stale identity)     -> reads as green, WRONG

Only the first is a pass. The other three are UNMEASURED, and reporting
them as zero is how this repo has repeatedly shipped a false green.

SIX MEASURED INSTANCES, ALL FROM THIS DRIVE -- this is not speculative:

1. BUDGET TRUNCATION. `frob check --budget 480` ran 15 of 52 gates and
   reported 3 errors; the full unbudgeted run takes 274s. A budgeted
   zero is not a zero, and nothing in the output said so unless
   gate-summary was read by hand.
2. HARDCODED LAYOUT (T-2384). 22 files gate on a literal "src/frob/"
   prefix. Against any other project the candidate set is empty and the
   gate reports a clean zero while enforcing nothing.
3. INERT WAIVERS (T-2314). 116 frob:waive directives never matched
   because perf_gate emitted absolute paths against relative waiver
   edges. 169 raw findings, 0 waived, and no error anywhere -- the
   directives read as honoured to anyone grepping for them.
4. RED TEST NOBODY READ (T-2387). `find_dropped_cli_flags`'s own test
   (tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags
   ::test_current_tree_has_zero_dropped_flags) is RED ON MAIN, failing
   on 3 genuinely dropped flags. The detector worked perfectly; the
   result was simply not surfaced anywhere an operator looks.
5. FAILED COMMAND READS AS ZERO. Empty output from an ERRORED command
   is indistinguishable from a genuine zero unless the exit code is
   checked separately.
6. SWEEP FALSE GREEN (T-1703). A post-land sweep reported CLEAN on a
   dirty tree: a budget-truncated check read as zero, and ty/dup output
   was never parsed at all.

THE FIX IS A TYPE CHANGE, NOT A REPORT TWEAK. A gate result must stop
being "a list of findings" (whose emptiness is ambiguous) and become an
explicit status:

    MEASURED(findings)   the gate ran to completion; len may be 0
    NOT_MEASURED(reason) budget-truncated, spawn refused, tool missing,
                         parse failure, timeout
    NOT_APPLICABLE(why)  no declared surface in this project

Then the invariants that make it real:
  - the aggregate reporter must NEVER collapse NOT_MEASURED or
    NOT_APPLICABLE into a zero, in human output OR --json;
  - the exit code must distinguish "all gates measured, none found
    anything" from "some gates never ran";
  - `frob check` must print an explicit unmeasured-gate roster whenever
    the set is non-empty, in the place the operator already looks
    (standing directive: automatic over commands -- a command that must
    be remembered is not a control);
  - NOT_APPLICABLE must be loud by default. A project that declares no
    surface for a gate should be told so, not silently passed.

This is a doctrine change across ~52 gates, so it needs a migration
path: a default-MEASURED shim keeps existing gates compiling while they
are converted one at a time, and a META-CHECK enforces that no gate
returns a bare empty list once converted. LEXCHECK001
(src/frob/gates/_lexical_selfcheck.py) is the working precedent for
exactly this kind of gate-on-the-gates and caught a live instance on its
first run; PORT001 (T-2384) is a second instance of the same shape.
Mirror them rather than inventing a third structure.

VERIFICATION. The must-fail fixture is the whole point here: force each
of the three non-pass states (run a gate under a budget that truncates
it; point a layout-dependent gate at a foreign project; make a matcher's
identity shape mismatch) and require the reporter to distinguish all
three from a genuine clean run. A conversion whose only evidence is
"frob check still exits 0" proves nothing -- that is precisely the
signal this ticket exists to make untrustworthy.