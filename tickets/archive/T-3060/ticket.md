---
id: T-3060
title: 'override_ratchet disables the pre-commit sweep, so lands publish lint errors:
  two classes reached main this way today'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
evidence_scope:
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: investigate whether T-3061 (7862fb4013cd6aaa2af121c6e9754fadfe9000ce)
  already resolves the incident this ticket was filed for
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_lint_error_in_a_touched_file_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_clean_touched_file_does_not_refuse
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1685dce679133085b6110a5d4d87ca083f866f2e
---

Resolved by T-3061 (7862fb4013cd6aaa2af121c6e9754fadfe9000ce): the pre-land
ruff-check gate it added runs unconditionally in every profile, including
rapid, and covers both lint classes (E501, import-sort/I001) that reached
main under override_ratchet on 2026-08-26. No code change belongs to this
ticket itself. Follow-up gap (ruff format, a distinct check from ruff
check) filed separately as T-3083.

<!-- frob:waive BUG002 reason="this ticket's own evidence is confirmatory-only by construction: the fix (T-3061's unconditional ruff-check pre-land gate) already landed under a different ticket before T-3060 was investigated, so there is no code change of T-3060's own to bind a fail-then-pass mutation pair to -- T-3061's own done report already carries the fail-at-parent/pass-at-fix demonstration for the real fix" -->