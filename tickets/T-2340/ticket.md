---
id: T-2340
title: design/frob.strata missing capability declarations for tests/unit/verify/test_watermark.py
  (5 undeclared effects, T-2323 residue)
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- tests/unit/verify/test_watermark.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2323's own body flagged these as "may belong here too, confirm current
count first". Confirmed via a fresh `frob check --only sys` in T-2323's
worktree: still present, unchanged count (5 undeclared effects, all on
the testsuite node):

  tests/unit/verify/test_watermark.py:34 exec (subprocess.)
  tests/unit/verify/test_watermark.py:38 exec (subprocess.)
  tests/unit/verify/test_watermark.py:39 exec (subprocess.)
  tests/unit/verify/test_watermark.py:42 env.read (os.environ)
  tests/unit/verify/test_watermark.py:44 exec (subprocess.)

Deliberately left OUT of T-2323's own scope (test_land_sibling_
regression.py and test_new_ticket_scope_overlap_warning.py only) --
adding a third, unrelated test file's capability review mid-ticket
would have expanded scope without a separate reviewed decision. Same
posture as T-2323 itself: read what test_watermark.py's subprocess/env
calls actually do before declaring vs. restructuring, per T-1870's
"deliberate review, not a blind edit" standard.

frob:waive BUG002 reason="this ticket's fix is a design/frob.strata capability declaration and docs/design/registry/capability-via-ratchet.lock.json ceiling correction, not a code-behavior change -- there is no pytest mutation-testable code path for a missing 'may' clause or a stale ratchet accepted_count. Same posture as T-2323 (its sibling ticket for the same file), which already established this precedent: the real fail-before/pass-after signal was directly demonstrated via the SELFAUDIT001/SYS111 gate itself -- 'frob check --only sys' reported 5 undeclared-capability-effect findings for tests/unit/verify/test_watermark.py (4 exec, 1 env.read) plus 2 SYS111 ratchet-ceiling findings BEFORE this change, and zero of either after -- measured directly in-worktree, not assumed, including a before/after comparison against unmodified main's design/frob.strata to isolate this ticket's own effect from pre-existing repo state. The bound pytest evidence (test_counts_raw_git_commits_not_queue_entries) exercises the touched test file's own real behavior as a sanity check that the capability grant did not break anything, per the must-still-pass positive-control requirement -- it was never meant to reproduce the SELFAUDIT001 defect itself, which is a declarative gate finding, not a runtime code path."