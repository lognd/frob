---
id: T-5481
title: 'Windows-only: land CAS ledger retry/compose fails (2 node ids)'
state: in-progress
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5481
branch: t-5481
scope:
- src/frob/tickets/_land_compose.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_compose.py
  reason: patch_file.write_text(diff_text) uses Python's default newline translation,
    which writes CRLF on Windows -- corrupting the unified diff's LF line endings
    before git apply --cached parses it, so the diff no longer applies cleanly and
    rebase_composed_commit_onto/compose_tree_out_of_tree both fail with ComposeFailed
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
    the defect is Windows-only newline translation; verified on the real Windows mirror
    instead'
  actor: logan
  at: '2026-09-24'
  old_length: 829
  new_length: 1423
evidence:
- tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebased_commit_carries_the_same_content_change
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_dev_advances_by_ledger_only_commit_between_compose_and_publish_lands
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only. 2 failing node ids:
- tests/unit/test_land_cas_ledger_retry.py::TestRebaseComposedCommitOnto::test_rebased_commit_carries_the_same_content_change
- tests/unit/test_land_cas_ledger_retry.py::TestFoldPublishAndResync::test_ledger_only_cas_miss_rebases_and_retries_without_regates

Both fail with Err(LandComposeError.ComposeFailed) where Ok is expected --
the land-compose/rebase-onto machinery itself is failing under test on
Windows, not a downstream assertion. Plausible causes: git rebase
behaving differently on Windows (line-ending/autocrlf interaction), or a
path-separator assumption in the compose step itself. Needs the actual
captured error detail (not visible in the short summary this drain pass
extracted) before root-causing further.

frob:waive BUG002 reason="the defect is windows-only (Path.write_text's default newline translation to CRLF, measured directly on the real Windows mirror) -- BUG002's own re-verification runs on this Linux checkout, where write_text never translates newlines and the bound evidence tests pass at dev regardless of the fix; the defect and the fix were both measured directly on the real Windows mirror instead (winrun, recorded in the done-report): all 3 tests failed with the exact CI symptom (patch does not apply) at dev, and passed after the fix, confirmed on two consecutive Windows runs"