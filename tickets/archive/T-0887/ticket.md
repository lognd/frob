---
id: T-0887
title: done-report --base-ref hangs when the named base ref does not exist in the
  clone
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_ticket_runner_done_report.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: T-0887 fix requires updating tickets.md's public-api doc block for base_ref_resolvable/set_done_report
    per AFFECT001
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_ticket_runner_done_report.py::TestBaseRefResolvable::test_unresolvable_ref_in_a_real_repo_is_false
- tests/test_ticket_runner_done_report.py::TestBaseRefResolvable::test_resolvable_ref_is_true
- tests/test_ticket_runner_done_report.py::TestBaseRefResolvable::test_non_git_root_is_none
- tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_unresolvable_base_ref_returns_err_immediately
- tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_resolvable_base_ref_behavior_unchanged
- tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_non_git_root_still_succeeds_best_effort
designated_repro_test: null
acceptance:
- text: GIVEN a clone with no local or remote-tracking main WHEN done-report --base-ref
    main runs THEN it exits nonzero within seconds naming the unresolvable ref
  evidence:
  - tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_unresolvable_base_ref_returns_err_immediately
- text: GIVEN a repo where main exists WHEN done-report --base-ref main runs THEN
    behavior is unchanged
  evidence:
  - tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_resolvable_base_ref_behavior_unchanged
threat: null
component: tickets
---
Found during T-0590 attempt 2 (see its failure log): `frob ticket done-report <id> --base-ref main` HANGS indefinitely when run in a clone that has no local `main` branch (e.g. a scratch clone created from a worktree branch). Expected: fail fast with a clear error naming the missing ref (or resolve origin/main), never hang. Likely a subprocess waiting on git prompting or an unbounded retry around the base-ref diff. Repro: clone any repo checked out at a non-main branch without fetching main, run done-report --base-ref main.