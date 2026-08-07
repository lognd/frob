---
id: T-1260
title: 'gates --fix CLI wiring: wire apply_tier_a_fixes into frob check --fix + affected-gate
  re-run'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_check.py
- src/frob/app/check_runner.py
- tests/test_check_runner.py
- src/frob/app/config.py
- design/frob.strata
- docs/modules/app.md
- docs/design/check-fix-engine.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: CLI --fix flag requires a new AppConfig field + from_args wiring; check_runner.py
    cannot read the flag without it, T-1260's own scope omitted this necessary plumbing
    file
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/AFFECT001 gate remedies for this ticket's own new symbols require
    touching the .strata interface declarations and the affects()-closure docs in
    the same diff
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/app.md
  reason: SELFAUDIT001/AFFECT001 gate remedies for this ticket's own new symbols require
    touching the .strata interface declarations and the affects()-closure docs in
    the same diff
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/check-fix-engine.md
  reason: SELFAUDIT001/AFFECT001 gate remedies for this ticket's own new symbols require
    touching the .strata interface declarations and the affects()-closure docs in
    the same diff
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
- tests/test_check_runner.py::TestResultAsJsonWithFix::test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present
- tests/test_check_runner.py::TestResultAsJsonWithFix::test_no_fix_report_is_byte_identical_to_plain_as_json
designated_repro_test: null
acceptance:
- text: GIVEN a repo with a live DOC007 finding WHEN `frob check --fix` runs THEN
    the directive is rewritten and the summary line reports it fixed with DOC007 re-verified
    clean in the same invocation
  evidence:
  - tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
  - tests/test_check_runner.py::TestResultAsJsonWithFix::test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present
  - tests/test_check_runner.py::TestResultAsJsonWithFix::test_no_fix_report_is_byte_identical_to_plain_as_json
- text: 'GIVEN `frob check --fix --json` WHEN no Tier B/C handlers exist yet THEN
    the json output includes an empty `fixits` array and a `rolled_back: []` field,
    not a missing key'
  evidence:
  - tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
  - tests/test_check_runner.py::TestResultAsJsonWithFix::test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present
  - tests/test_check_runner.py::TestResultAsJsonWithFix::test_no_fix_report_is_byte_identical_to_plain_as_json
- text: GIVEN `frob check` (no --fix) WHEN run against the same repo THEN behavior
    and output are byte-identical to before this ticket -- --fix is strictly additive
  evidence:
  - tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
  - tests/test_check_runner.py::TestResultAsJsonWithFix::test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present
  - tests/test_check_runner.py::TestResultAsJsonWithFix::test_no_fix_report_is_byte_identical_to_plain_as_json
threat: null
component: null
---
Wire apply_tier_a_fixes (src/frob/gates/_fix_engine.py, T-1138) into an
actual `--fix` CLI flag. Add the flag to src/frob/_cli_parsers/_check.py
and orchestration to src/frob/app/check_runner.py: load the graph
snapshot + ticket queue exactly as a normal `frob check` run does, call
apply_tier_a_fixes, then re-run the UNION of every rule id actually fixed
once in the same invocation and report the residual violation count for
those rules. Report three counts in the summary line: fixed / rolled-back
(0 for this ticket, Tier B not built yet) / fix-its emitted (0 for this
ticket, Tier C not built yet) -- shape the summary so later tickets can
add to it without a reshape. `--fix --json` emits the existing violations
array plus an (empty for now) `fixits` key. See docs/design/check-fix-engine.md
"Gate re-run semantics" and "Fix-it emission format" sections.