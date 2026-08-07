---
id: T-0816
title: 'tests: sys-audit clean-model fixture red on main (matrix/reliability leg exits
  1 after recent strata lands)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN TestSysAudit::test_clean_model_passes runs THEN it passes
    with every audit leg PROVED, with the fixture updated to current rules (or the
    responsible check fixed if it false-positives on a clean model, with the choice
    documented)
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes
threat: null
component: null
---
Found during T-0752 (2026-07-23, confirmed on current main): the sys-audit
clean-model fixture test fails -- self-conformance and resource-contention
legs PROVE, then the runner exits 1 from the final composite check
(reliability / health / matrix_proved legs; last frame shows `or not
matrix_proved`). Almost certainly fixture-vs-new-check drift: a recently
landed strata leg (T-0606 windows host wiring, T-0644 health leg, T-0717
mode vocabulary, or the T-0769 may-net narrowing) tightened what a clean
model must declare and the fixture was never updated. Root-cause which leg
reports the gap (run the test, capture the named-gap summary), then fix
the FIXTURE to be genuinely clean under current rules -- do NOT weaken any
check. If the leg's demand is wrong (false positive on a genuinely clean
model), fix the check instead and say so.