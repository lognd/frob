---
id: T-3095
title: Isolate land's three post-squash file-mutating stages so the whole transaction
  is invisible in the shared tree
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Re-record on main the T-3089 residue that existed only as an unlanded worktree
    draft, with the three enumerated file-mutating sub-stages
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3936
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOUND 2026-08-27 while attempting T-3089 (wire the out-of-tree compose
primitive into the squash stage). T-3089 was FAILED and requeued rather than
forced, because the analysis showed its own acceptance criterion cannot be met
by wiring the squash step alone. This ticket carries the prerequisite.

(Filed fresh on main deliberately: the original residue was recorded as
`T-draft-19b78598`, which existed only on the `t-3088` worktree branch and
never reached main -- an unlanded draft id is invisible to the fleet, so it is
re-recorded here rather than cited.)

THE FINDING. T-3089's acceptance requires that a concurrent
`git status --porcelain` poll sees NOTHING dirty at any point during a land
until the final atomic publish. Composing the squash-merge out of tree closes
that window for the DIFF ITSELF -- but `_land_squash_apply_finish`, the stage
immediately after the squash, runs three more sub-stages that mutate root's
REAL CHECKED-OUT FILES, not merely git objects:

  - `_apply_release_bump` (`_land_release.py`) writes real bytes to
    `pyproject.toml`, `CHANGELOG.md` and `.frob-release.json` through the
    `bump_version` callback, then reads them back off disk.
  - `_maybe_rebuild_natives` runs a real `cargo`/`maturin` build against files
    on disk.
  - `_apply_pre_commit_sweep_or_unwind` runs `frob check`/ruff/Tier-A auto-fix
    against root's real staged files.

So root is genuinely dirty for the entire span those three run, no matter how
the squash is composed. This is why T-3088's primitive, though landed and
correct, does not by itself remove DirtyMain: it fixes the step everyone
noticed and leaves three that nobody had enumerated.

WHY THIS IS THE IMPORTANT HALF. The whole session's contention evidence --
sibling lands colliding on DirtyMain, `frob ticket new` refusing with
LandInProgress, an agent unable to even START unrelated work -- is explained by
root being observably dirty during a land. Closing only the squash window would
have produced a change that looks like the fix, measures as an improvement in
isolation, and leaves the actual fleet-serialization behaviour intact. That is
the failure mode to avoid here.

WHAT IS WANTED. Move these three sub-stages onto an isolated or throwaway
checkout so the entire land transaction is invisible in the shared tree until
the final `publish_ref_cas`. Sequencing note: each has a different character
and they may not all want the same treatment --
  - the release bump is pure file rewriting and should be straightforward to
    perform against a scratch checkout;
  - the native rebuild is expensive and may not belong inside the transaction
    at all -- consider whether it can move after the publish, and say why;
  - the pre-commit sweep MUTATES content (Tier-A auto-fix), so its output must
    end up in the composed tree, which makes it the genuinely hard one.
Argue the ordering rather than assuming it.

CONSTRAINTS
- Every existing guard stays intact: BUG002 repro ordering, LAND-PROOF, T-3050's
  non-QUEUED orphan refusal, T-3061's pre-land lint gate.
- Land small. This machinery produced, in a single day, a state=done with zero
  code on main, tip-drift refusals, a DirtyMain deadlock, a quarantine deadlock
  needing five land attempts, and multiple timeouts.
- Reuse `frob.tickets._land_compose` (landed at `c49a623ea`); do not write a
  second composition path.

ACCEPTANCE
- A concurrent `git status --porcelain` poll against root, sampled throughout a
  real land, reports clean at every sample until the final publish. Demonstrate
  with an actual poll during an actual land -- not by asserting it.
- Land wall-clock before and after, under comparable load. Current baseline:
  refusing land ~16-32s, clean land ~143-148s.
- The three sub-stages are handled explicitly, with the chosen treatment and
  reasoning stated for each.
- T-3089 becomes performable; state whether it should now be worked as-is or
  re-scoped.
