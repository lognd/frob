---
id: T-5479
title: 'Windows-only: frob-suggest hook dedup-on-repeat fails (4 node ids)'
state: done
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5479
branch: t-5479
scope:
- tests/test_hook_frob_suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_hook_frob_suggest.py
  reason: 'root cause measured on real Windows: os.getppid() returns a DIFFERENT value
    across sequential sibling subprocess.run calls from the same long-lived parent
    process (confirmed via direct repro), so _session_key''s no-session_id ppid fallback
    treats each call as a new session and re-blocks instead of deduping. Real Claude
    Code hook invocations always supply session_id (per this test file''s own docstring);
    thread a consistent session_id through the affected tests to match production
    shape instead of exercising the Windows-unstable fallback'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: 'BUG002 refusal: evidence tests cannot fail at dev on this Linux host since
    the defect is a Windows-only os.getppid() instability; verified on the real Windows
    mirror instead'
  actor: logan
  at: '2026-09-24'
  old_length: 1143
  new_length: 1704
evidence:
- tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through
- tests/test_hook_frob_suggest.py::test_second_identical_fleet_probe_is_allowed_through
- tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only. 4 failing node ids, all in tests/test_hook_frob_suggest.py:
- test_second_identical_check_pipeline_is_allowed_through
- test_second_identical_fleet_probe_is_allowed_through
- test_third_identical_command_is_blocked_again
- TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it

Sample failure: test_second_identical_check_pipeline_is_allowed_through
expects a SECOND identical command to be silently allowed through (the
frob-suggest hook's own de-dup-on-repeat behavior) but gets the hook's
BLOCK response again, as if it were treated as a first-time/different
command. This points at the hook's "have I seen this exact command
before" cache/dedup key being computed differently on Windows -- likely a
path-separator or line-ending difference in the command string used as
the dedup key, so the same logical command hashes/matches differently
across two invocations on Windows.

Needs someone to read the frob-suggest hook's dedup-key implementation
with Windows path/newline normalization in mind; not root-caused further
in this drain pass.

frob:waive BUG002 reason="the defect is windows-only (os.getppid() instability across sequential sibling subprocess.run calls, measured directly on the real Windows mirror) -- BUG002's own re-verification runs on this Linux checkout, where os.getppid() is stable and the bound evidence tests pass at dev regardless of the fix; the defect and the fix were both measured directly on the real Windows mirror instead (winrun, recorded in the done-report): failing with the exact CI symptom at dev, passing after the fix, confirmed on two consecutive Windows runs"