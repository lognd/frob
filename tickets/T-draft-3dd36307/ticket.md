---
id: T-draft-3dd36307
title: 'land CAS: apply-failed ledger-only rebase must fall back to full recompose,
  not refuse (T-5491 follow-up)'
state: queued
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
worktree: null
branch: null
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
Measured on T-5477's own land (dev advanced by ONE ledger-only commit, chore(tickets): mirror body T-5444 from worktree; /tmp/land-T-3010.log lines ~31200-31255): _attempt_ledger_only_rebase (T-5491/src/frob/tickets/_land_squash.py) retried the apply attempt 5 times against the SAME sibling tip, each logging 'did not apply cleanly (ComposeFailed: building the out-of-tree commit ...)' followed by 'falling back to full recompose', then after attempt 5 the land refused with the CAS-miss message -- the announced full recompose never actually ran. Retrying an IDENTICAL apply against an UNCHANGED tip is deterministic (it will fail the same way every time), so all 5 attempts were wasted and the promised fallback (a real re-merge/re-squash/re-check/publish cycle against the sibling's current tip, not a diff-and-apply rebase) never happened.

Fix: the apply_failed branch in _publish_with_ledger_only_retry/_attempt_ledger_only_rebase must perform the ACTUAL full recompose (re-merge current tip into the worktree, re-squash, re-run the composed-tree check, publish) instead of retrying the same diff-and-apply rebase against an unchanged tip -- bounded by the existing drift-proportional retry limit, refusing only if the recompose itself conflicts (a genuine, unresolvable content conflict), not merely because the cheaper diff-and-apply shortcut failed.