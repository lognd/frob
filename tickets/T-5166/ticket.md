---
id: T-5166
title: 'land: T-4658 in-worktree renumber refusal breaks finalize_draft_for_land for
  sibling and landing drafts'
state: done
kind: bug
origin: human
created: '2026-09-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_draft_finalize.py
- src/frob/tickets/_new_renumber.py
- tests/ticket_land_suite/test_draft.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/ticket_land_suite/test_draft.py::TestLandFromDotClaudeWorktreesPromotesOwnAndSiblingDrafts::test_own_and_sibling_draft_both_promoted_from_agent_worktree_path
- tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree
- tests/unit/test_ids_assigned_once.py::test_renumber_one_refused_inside_worktree
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5166
branch: t-5166
---
MEASURED 2026-09-21 00:11 (T-3962 land, coordinator queue): T-4657's land shipped T-4658's _refuse_renumber_inside_worktree (src/frob/tickets/_new_renumber.py), which refuses ANY renumber whose root resolves under .claude/worktrees/. But frob ticket land finalizes drafts by calling finalize_draft_for_land(worktree, draft_id, root) (src/frob/tickets/_land_finalize.py:318 for the landing ticket, :403 for sibling drafts) -- the renumber runs against the WORKTREE ledger by design, so it now always fails: 'sibling draft T-draft-152d99c7 finalize failed (WorktreeLeaseViolation ...) after T-3962 already finalized' -> LandError.GitFailed. The post-land sweep files a residue draft on dev after EVERY land, so every following land whose worktree merges dev carries a sibling draft and dies; landing a T-draft-* ticket itself is broken the same way. Coordinator mitigation: 'frob ticket promote' every draft on the root before each land (land-one.sh). Fix: the land's finalize path must either be exempt from the guard (land-internal caller, e.g. via the promotion primitive T-4658 says land itself owns) or promote against root then carry the mapping into the worktree ledger. Add a ticket_land_suite regression: land from a .claude/worktrees/ path with one sibling draft in the ledger must succeed. Also make the post-land sweep's residue ticket mint a final id (it files from the root checkout on dev, not main -- T-0162 draft minting rule) so lands do not accumulate drafts.