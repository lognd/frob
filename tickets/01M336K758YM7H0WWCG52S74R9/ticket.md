+++
id = "01M336K758YM7H0WWCG52S74R9"
title = "frob ticket land's Tier-A pre-land fix pass produces spurious mass ty invalid-type-form Never errors, refusing otherwise-clean lands"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5288"]
scope = ["src/frob/tickets/_land.py", "src/frob/tickets/_land_compose.py"]
+++

Observed repeatedly landing T-5132, T-5280, and T-5133 (all via nice-ed dry-run + bare land from the coordinator's own playbook): frob ticket land --drain refuses with hundreds of ty invalid-type-form 'Variable of type Never is not allowed' errors across ~30-40 PRE-EXISTING files this ticket's own diff never touches (e.g. tests/unit/test_ticket_store.py, tests/unit/test_land_queue.py) -- always the identical file/line list across repeated attempts on the same branch. Direct uv run ty check on any single flagged file, both at the root checkout and inside the worktree, reports zero errors. The land run also separately corrupts ~10-180 unrelated tracked files in the worktree on the SAME invocation (stripped alternating comment/docstring lines, breaking syntax in some cases) via its own Tier-A auto-fix pass, then reports 'worktree left clean' after restoring the absorbed paths -- but the ty check output was captured from the transiently-corrupted intermediate state before restore, producing the false Never-type cascade. Root cause hypothesis: the pre-land Tier-A fix pass and the post-fix ty check are not properly sequenced/isolated, so ty sometimes analyzes a partially-rewritten tree. Workaround used: repeatedly git checkout dev -- <corrupted files> to restore, then retry land; this can take 5+ attempts per ticket and is not something a ticket's own worktree can fix from inside its declared scope.

## Drop reason
- 2026-09-22: same root cause: the TEST010 Tier-A handler corrupting files in the pre-land pass (absorbed by T-5289)
