---
id: T-1481
title: wire frob check --fix CLI flag to the tiered fix engine
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/app/check_runner.py
- docs/design/check-fix-engine.md
- src/frob/gates/_fix_engine_tier_b.py
- src/frob/gates/_fix_engine_tier_c.py
- tests/test_check_runner.py
- tickets/T-1481/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_tier_b.py
  reason: 'T-1481: wiring apply_tier_b_fixes/apply_tier_c_fixits into --fix removes
    their now-obsolete WIRE001 CLI-uncalled waivers; tests/test_check_runner.py covers
    the CLI wiring itself'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_fix_engine_tier_c.py
  reason: 'T-1481: wiring apply_tier_b_fixes/apply_tier_c_fixits into --fix removes
    their now-obsolete WIRE001 CLI-uncalled waivers; tests/test_check_runner.py covers
    the CLI wiring itself'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_check_runner.py
  reason: 'T-1481: wiring apply_tier_b_fixes/apply_tier_c_fixits into --fix removes
    their now-obsolete WIRE001 CLI-uncalled waivers; tests/test_check_runner.py covers
    the CLI wiring itself'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1481/**
  reason: 'T-1481: own ticket dir needed for Done report'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_no_tier_a_findings_is_a_no_op
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_finding_with_no_tier_a_handler_is_never_mutated_or_claimed
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_tierbdemo_marker_is_committed_via_tier_b_and_reported_fixed
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_tier_c_fixit_from_a_todo001_violation_is_included
- tests/test_check_runner.py::TestResultAsJsonWithFix::test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present
- tests/test_check_runner.py::TestResultAsJsonWithFix::test_no_fix_report_is_byte_identical_to_plain_as_json
- tests/test_check_runner.py::TestFixReportText::test_summary_line_reports_three_counts
designated_repro_test: null
threat: null
component: null
---
docs/design/check-fix-engine.md's "Status quo" section states
apply_tier_a_fixes has no CLI entry point: src/frob/app/check_runner.py
and src/frob/_cli_parsers/_check.py have no --fix/Fix reference, so
`frob check --fix` does not exist as a runnable command. Wire a --fix
flag through _cli_parsers/_check.py and check_runner.py that invokes
apply_tier_a_fixes (and, once T-1262/T-1263 land, the Tier-B/Tier-C
paths). Found while draining NEGEXIST001 (T-1477): the doc's
absence-claim had no frob:until binding.