---
id: T-3221
title: rapid-debt.jsonl reappeared at repo root after T-2997's own land (in-flight
  process used pre-fix code)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
blocked_by:
- T-3241
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- rapid-debt.jsonl
- .frob/rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2997 moved rapid-debt.jsonl's write target to .frob/rapid-debt.jsonl and untracked the root copy. During T-2997's OWN land, the long-running frob CLI process had already imported the pre-fix frob.tickets._evidence module before the merge published the fix to main -- so the same process's own post-merge steps (rapid sweep deferred-debt recording, evidence-scope-unbound skip) wrote 3 fresh lines back to root/rapid-debt.jsonl via the stale in-memory code, and the land's auto-commit-stray-append machinery committed it (chore(rapid): record T-2997's deferred post-land sweep, 3173d18fe). Verified: git show HEAD:rapid-debt.jsonl shows 3 lines dated to T-2997's own land commits. Fresh frob invocations from now on use the fixed code and will not reproduce this, but the 3 stray lines are back on the tracked root path right now and need removing (git rm rapid-debt.jsonl, migrating the 3 lines into .frob/rapid-debt.jsonl) to actually close out T-2997's acceptance bar ('root copy is gone from git tracking').