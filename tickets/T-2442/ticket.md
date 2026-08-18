---
id: T-2442
title: Add nested-worktree regression case to root-write-guard hook tests
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_hook_root_write_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_hook_root_write_guard.py::test_agent_write_inside_a_nested_worktree_is_allowed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2396 landed .claude/hooks/root-write-guard.py. The original fixture
(_make_repo_with_worktree in tests/test_hook_root_write_guard.py) placed
the linked worktree as a SIBLING directory of the primary checkout
(tmp_path/agent-wt next to tmp_path/primary). This repo's real topology
nests worktrees INSIDE the primary checkout instead
(.claude/worktrees/<name>), which the hook's fix commit (39039b5f3)
explicitly calls out in a comment: "T-2412: a linked worktree may live
INSIDE the primary checkout ... so the `..` relpath test below does NOT
catch them."

Because the fixture never reproduced the nested topology, its own
positive control (test_agent_write_inside_its_own_worktree_is_allowed)
passed for the WRONG reason against the pre-fix hook: the pre-fix logic
inferred "is this the primary checkout" purely from `..`-relative path
shape, which happens to also correctly classify a sibling-sited worktree
as "not primary" even with the bug present. The bug (every write inside
a NESTED worktree misclassified as a root write and denied, fleet-fatal)
only manifests when the worktree is actually nested, and nothing in the
suite ever built that shape -- 9/9 green while the real deployment
topology was fleet-fatal.

Add a nested-worktree fixture/case to
tests/test_hook_root_write_guard.py: create the linked worktree INSIDE
the primary checkout (e.g. primary/.claude/worktrees/agent-wt, mirroring
this repo's real layout) and assert an agent-context write there is
ALLOWED. Verify it fails against the pre-fix hook (`git show
39039b5f3^:.claude/hooks/root-write-guard.py`) and passes against
current. Keep the existing sibling-sited case too -- both topologies
must stay covered, per the T-2412 comment's own lesson.