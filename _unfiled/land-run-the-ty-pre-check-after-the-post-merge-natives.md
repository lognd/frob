+++
id = "01M38BCNNNQPBQYTYC6XY1KN97"
title = "land: run the ty pre-check after the post-merge natives rebuild (stale extension at ty time)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5813"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/tickets/_land_verify.py", "src/frob/app/ticket_runner/_land_cmd.py"]
+++

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
