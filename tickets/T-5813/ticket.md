---
id: T-5813
title: 'land: run the ty pre-check after the post-merge natives rebuild (stale extension
  at ty time)'
state: done
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-42b1e188
branch: t-draft-42b1e188
scope:
- src/frob/tickets/_land_verify.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_land_dry_run.py::TestStaleNativesRebuildPrecedesTyCheck::test_rebuild_call_precedes_the_ty_check_call
- tests/test_ticket_land_dry_run.py::TestStaleNativesRebuildPrecedesTyCheck::test_rebuild_runs_even_when_natives_are_fresh
designated_repro_test: tests/test_ticket_land_dry_run.py::TestStaleNativesRebuildPrecedesTyCheck::test_rebuild_call_precedes_the_ty_check_call
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured twice: T-3010's land at 10:27 (ty check refused src/frob/gates/
_strata_milestone_closure.py:168 unresolved-attribute, Module strata_core
has no member milestone_closure_check -- log: /tmp/land-T-5464.log) and
T-5366's land at 19:50 (same "strata_core has no member
milestone_closure_check" refusal, a plain Python leaf whose worktree's
extension predated T-3010 -- log: /tmp/land-T-5366.log). Both times a
manual `uv run --no-sync frob natives build` in the worktree
immediately before the SAME ty check cleared it with no other change --
proof the extension, not the source, was stale.

Root cause: the land pipeline's ty pre-check runs BEFORE the post-merge
natives rebuild (T-5518's _rebuild_stale_worktree_natives / the T-1213
call), not after. A ticket whose merge brings in a new/changed Rust
export (or any ticket landing after such a change is already on dev)
gets ty-checked against whatever extension the worktree happened to
have built at `ticket work` time, which predates the merge.

Fix: in the land pipeline, move the stale-natives rebuild to run right
after the merge and before `ty check` (so ty checks the same fresh
extension `_reverify_evidence_post_merge` will later build/observe), or
have the ty step resolve strata_core against the freshly built extension
directly.

Positive control: a worktree with a stale extension and a Rust export
added on dev passes ty at land (no manual `frob natives build` needed
between merge and the ty check step).