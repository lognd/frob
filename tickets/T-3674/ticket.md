---
id: T-3674
title: 'self-gate floor (a): DOC007/DRIFT001 fallout from T-3661/T-3628'
state: in-progress
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets_leases.py
- src/frob/process/_derived_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 remedy: this is a directive-comment-only fix'
  actor: logan
  at: '2026-09-01'
  old_length: 894
  new_length: 1017
evidence:
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_a_windows_style_worktree_path
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_drops_a_dash_prefixed_windows_style_worktree
- tests/test_tickets_leases.py::TestLeaseShapeValidation::test_worktree_operand_check_admits_windows_paths_directly
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Self-gate floor bucket (a): frob:tests separator defect + drift ack.

Fix:
- tests/test_tickets_leases.py:464,500,515 -- frob:tests directives use
  `Class::method` (pytest collect-only separator); the graph convention is
  `Class.method`. Change to the dotted form. This resolves DOC007 x3 and
  the paired DRIFT002 x3 for the same lines.
- src/frob/process/_derived_lock.py::_process_already_holds -- DRIFT001,
  digest moved since ack (T-3628 split). Re-ack via `frob ack` after
  confirming the change is intentional.

OUT OF SCOPE (leased by T-3673, win32 round 17): docs/modules/process.md
DRIFT002 x3 (process.md#public-api -> _lock.py symbols moved to
_derived_lock.py). Deferred to a follow-up ticket once the lease frees.

Evidence: gate measurement, `timeout 540 uv run frob check --only doc`
and `--only drift` go to zero for these findings (excluding the deferred
process.md ones).

frob:no-behavior-change reason="comment-only fix: dotted separator in frob:tests directives, no runtime behavior touched"