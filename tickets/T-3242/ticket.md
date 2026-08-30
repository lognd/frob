---
id: T-3242
title: Recovered from T-3031's phantom TICK006 citation of T-draft-36006d55
state: done
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: phantom-citation recovery ticket resolved as already-done
  on main; no file changes, only a failure-log/evidence record
body_changes:
- mode: append
  reason: 'BUG002 refused: designated repro test passes at parent because there is
    no code defect here, only a stale ticket-ledger citation to close'
  actor: logan
  at: '2026-08-29'
  old_length: 1530
  new_length: 1874
evidence:
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-3031's Done report claimed T-draft-36006d55 was filed, but T-draft-36006d55 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> fore this ticket's diff ever touched anything; two of the three
  (T-3028, T-3030) were already filed by T-3019's own land, the third
  filed here as T-draft-36006d55 (gets a real id at land/renumber).

Filed: T-draft-36006d55 ("TestGitlessTargetGateSeverity::
test_render_lint_gate_warns_not_errors_

## Failure log
- 2026-08-29 attempt 1: Already resolved on main. T-3031's Done report claimed a new ticket T-draft-36006d55 was filed for adding TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root -- that draft id never resolves (phantom filing trail, likely dropped/never promoted at renumber time), but the DESCRIBED WORK itself is present and passing on main: tests/system/test_cli_check.py::TestGitlessTargetGateSeverity (both test_gitless_target_gates_warn_not_error and test_render_lint_gate_warns_not_errors_on_gitless_root) exist, are wired to T-0705's git-less-target-contract docs/modules/gates.md#git-less-target-contract-t-0705, and pass: 'uv run pytest -p no:xdist tests/system/test_cli_check.py::TestGitlessTargetGateSeverity -v' -> 2 passed. Nothing left to implement; the phantom citation just never got cleaned up.

frob:waive BUG002 reason="phantom-citation recovery ticket: no code defect exists to reproduce -- the work T-draft-36006d55 was supposed to cover already exists and passes on main (T-3031 landed it directly or via an id that never resolved), this ticket only closes the ledger loop with evidence naming the pre-existing test, never a new fix"