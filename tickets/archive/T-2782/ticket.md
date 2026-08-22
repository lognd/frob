---
id: T-2782
title: landing is serialized on a ~300s critical section, capping fleet throughput
  at ~1 ticket/5-6min regardless of agent count
state: done
kind: docs
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/investigations/
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/index.md
  reason: 'DOC001: link the new investigation doc from docs/index.md so it is not
    linked from nowhere'
  actor: logan
  at: '2026-08-21'
triage_changes:
- field: kind
  old_value: feature
  new_value: docs
  reason: measurement/investigation deliverable, docs/investigations/ scope only,
    no code change
  actor: logan
  at: '2026-08-21'
evidence:
- cmd:wc -l docs/investigations/T-2782-land-serialization.md exit=0 sha256=1f01d1b4b0cc
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ad4a95b31a52599f914fb82e443c4b9e97a08fe3
---
## Measured ceiling

Landing is fully serialized on a ~300s critical section, which caps fleet
throughput at roughly one ticket per 5-6 minutes NO MATTER how many agents
run. Observed repeatedly on 2026-08-20/21 with 5-6 implementers active:
best sustained rate 6 lands/30min, with 12-21 minute gaps whenever agents
bunched into verification.

`land()` (src/frob/tickets/_land.py:1410) acquires `_land_lock` and calls
`_land_locked` INSIDE it. `_land_locked` performs the merge and then a live
`frob check --ticket` spawn (`check_gates()`), plus
`_reverify_evidence_post_merge`. `_derive_post_land_sweep_budget_s` reports
estimated_work_s = 300 for that body. So the expensive verification is
inside the critical section, and N agents cannot overlap it.

Adding agents does NOT help past that point -- it only increases the number
waiting on the lock. T-2774 stopped the waiters from being SIGKILLed, and
T-2775 gave them a clean way to queue, but neither raises the ceiling.
This ticket is about the ceiling itself.

## Why the obvious fix is NOT obviously correct

Do not just hoist the check outside the lock. The verification is
deliberately POST-MERGE: `_reverify_evidence_post_merge` and the T-0754
claim re-verification both run against the merged tree, so that what is
verified is what will actually land, and so that `--dry-run` is "a real
guarantee, not a guess" (T-0176). The merge in turn needs main's tip
stable, which is what the lock provides.

The comments at src/frob/tickets/_land.py:2133-2180 record real ordering
constraints already paid for once -- `_refresh_prework_sweep` must run
BEFORE `check_gates()` or the check observes a stale-sweep PRE001 and
refuses on a false divergence (T-0754/T-0236); and a prior T-2064 probe
that claimed to prove which tree the spawn observes was found to be a
TAUTOLOGY and corrected by T-2076. Read all of that before designing.
Anyone proposing a reordering must show it does not reintroduce either.

## The candidate design, to be validated NOT assumed

Optimistic concurrency: merge and verify OUTSIDE the lock against a
recorded main tip, then take the lock and check whether main moved. If it
did not, commit. If it did, re-merge and re-verify.

The obvious objection, which must be answered with a measurement before any
implementation: every successful land ADVANCES main, so under sustained
load the next land's optimistic verification is invalidated by the previous
one, and the scheme could degenerate to serial-plus-wasted-work -- strictly
worse than today. The scheme only pays off if the post-move revalidation
can be made CHEAP (proportional to the delta) rather than a full re-run.

So the first deliverable is a MEASUREMENT, not a patch:
1. What fraction of `_land_locked`'s ~300s is the `check_gates()` spawn
   versus merge/finalize/squash? Profile it; do not estimate.
2. Of that, how much is genuinely post-merge-dependent versus computable
   from the worktree before the merge?
3. How often does main actually move between two consecutive lands in
   practice (measure against the real ledger history), and how expensive
   is a correct revalidation of just that delta?

If the answer is that most of the 300s is post-merge-dependent and
revalidation cannot be made cheap, the correct outcome is to CLOSE this
with that finding recorded, and pursue the cost of `frob check` itself
instead. That is a legitimate result, not a failure -- record it rather
than forcing a redesign.

## Constraints on any implementation

- `--dry-run` must remain a real guarantee (T-0176), not a guess.
- The post-merge re-verification must still verify the tree that actually
  lands. A scheme that verifies a tree which is then modified before
  commit is a silent correctness regression, and worse than slow.
- Positive controls in BOTH directions: two concurrent lands must both
  produce correct results (neither silently skipping verification), AND a
  land whose main moved mid-flight must be caught and re-verified rather
  than committing an unverified tree. Plant the race deliberately; a design
  this subtle cannot be argued correct in prose.
- No silent caps: if the scheme bounds retries, log what was dropped.

## Related

T-2774 (early refusal so a waiter is not killed) and T-2775 (shared
wait primitive) both landed tonight and address the SYMPTOMS of this
ceiling. Neither raises it. Do not treat this as a duplicate of either.