+++
id = "01M2VFD1HJG323F8ZXX1M53CD1"
title = "Ids are assigned once at new: renumbering inside a worktree is refused"
type = "task"
category = "done"
outcome = "done"
priority = "critical"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-4658"]
labels = ["milestone:0.535.0"]
scope = ["src/frob/tickets/_new_renumber.py", "src/frob/tickets/_renumber_v2.py", "tests/unit/test_ids_assigned_once.py"]

[[acceptance]]
text = "Given a checkout under .claude/worktrees/, when a renumber is attempted, then it is refused with a named, logged error and the ledger is unchanged."
bound = false

[[acceptance]]
text = "POSITIVE CONTROL: tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree constructs a worktree-shaped checkout and asserts the refusal. It FAILS on dev today (the renumber succeeds and rewrites ids) and passes after this leaf."
bound = false

[[acceptance]]
text = "Given two concurrent `frob ticket new` calls in the root, when both allocate, then they receive distinct ids and neither rewrites the other's; tests/unit/test_ids_assigned_once.py::test_concurrent_new_allocates_distinct_ids proves it."
bound = false

[[acceptance]]
text = "draft promotion happens only at publish time on dev; the land never renumbers inside the worktree"
bound = false
+++

Kernel decoupling leaf (LEDGER story). ~2 points.

Measured this week: draft ids were renumbered INSIDE worktrees, and concurrent agents raced each other's renumbers. src/frob/tickets/_new_renumber.py (1807 lines) and _renumber_v2.py (441) can both rewrite an id from any cwd.

Make the rule structural: an id is allocated exactly once, at `frob ticket new`, in the root checkout. Renumbering from inside a worktree is REFUSED with a named error that says so. Draft promotion stays a root/ledger operation (see the sibling promotion leaf).

Log the allocation (id, cwd, root) at INFO and every refusal at WARNING with the detected worktree path.
