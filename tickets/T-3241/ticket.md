---
id: T-3241
title: rapid-debt.jsonl root copy restored to full pre-T-2997 history by T-2971/T-3029
  lands, not just 3 stray lines
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
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
found while working T-3221.

T-3221 assumed only 3 stray lines leaked back into the tracked root
rapid-debt.jsonl during T-2997's own land (commit 3173d18fe, going from
2 to 3 lines). Measurement shows the problem is much larger: the very
next land after that, land T-2971 (commit
013c97097502a2e7d1a22e51378a1eacb60a24d1), re-inserted 3358 lines into
the tracked root rapid-debt.jsonl in one commit -- the diff shows the
ENTIRE pre-T-2997 historical content (starting from old T-1264 entries)
being re-added wholesale, not incremental stray appends. A further land
(T-3029, ea92587bc) added 2 more lines, bringing HEAD's tracked
rapid-debt.jsonl to 3363 lines -- essentially the full pre-fix file is
back under git tracking at the exact path T-2997 was supposed to have
removed permanently.

This means T-2997's fix (move write target to .frob/rapid-debt.jsonl,
untrack the root copy) is being silently undone by ordinary lands, not
just a one-time in-flight-process artifact from T-2997's own land.

Verified via:
  git show b48c57be7:rapid-debt.jsonl (2 lines)
  git show 3173d18fe:rapid-debt.jsonl (3 lines)
  git show 013c97097:rapid-debt.jsonl (3361 lines, +3358 in that commit diff)
  git show ea92587bc:rapid-debt.jsonl (3363 lines)
  wc -l rapid-debt.jsonl at current HEAD (3363 lines, still tracked)

Do-first: diff 013c97097 against its parent to find the exact insertion
mechanism, then trace which land-pipeline code path still resolves the
old root path.