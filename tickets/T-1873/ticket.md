---
id: T-1873
title: 'rapid-debt.jsonl has no merge driver: concurrent appends conflict and agents
  hand-edit an append-only ledger'
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .gitattributes
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
OWNER REPORT, 2026-08-08: "rapid-debt.jsonl is being manually edited by
agents because of diff; can we figure out a way to reconcile that?"

CAUSE, confirmed. `rapid-debt.jsonl` is a TRACKED file at the repo root,
and it is append-only: every land under the rapid profile appends one
record to its tail. With five agents landing concurrently, two worktrees
routinely append different records at the same line, which git's default
line-level merge reports as a textual conflict.

`.gitattributes` currently contains exactly ONE merge rule:

    /tickets.md merge=frob-ledger

`rapid-debt.jsonl` has no entry at all, so it falls through to the
default driver. Nothing in the repo tells an agent how to resolve it
either, so each one improvises -- by hand, under land pressure, on a file
whose whole value is that no record is ever lost. Hand-editing an
append-only ledger during conflict resolution is how a record silently
disappears, and a dropped debt record is indistinguishable afterwards
from debt that was never incurred.

This is not an agent-discipline problem. The correct resolution for two
concurrent appends is ALWAYS "keep both sides", which is mechanical, so
the machine should do it.

REQUIRED:

1. Add a merge rule for `rapid-debt.jsonl` to `.gitattributes`, anchored
   with a leading slash exactly as `/tickets.md` is. T-0480 documents why
   the anchor is load-bearing: an unanchored pattern also matches any
   same-named file elsewhere in the tree, and that mistake silently
   truncated a ~900-line doc once already.

2. Prefer git's BUILT-IN `merge=union` over a new frob driver. Union
   concatenates both sides' lines, which is exactly the append-only
   semantics wanted, and -- unlike `merge=frob-ledger` -- it requires NO
   local `git config` registration. That matters: the frob-ledger driver
   needs a one-time per-clone setup, so any worktree or fresh clone that
   skipped it silently falls back to the default driver. A rule that only
   works on a correctly-configured machine is a rule that will be missing
   exactly when a new agent hits the conflict. Do not build a mechanism
   where a built-in suffices.

3. Verify by REPRODUCTION, not by inspection. Construct two branches that
   each append a different record to `rapid-debt.jsonl`, merge them, and
   assert both records survive with no conflict markers and no manual
   step. That test is the deliverable; the `.gitattributes` line without
   it is an unverified claim.

4. Check whether union merge can duplicate a record when both sides
   already share a line. If it can, decide explicitly whether that is
   acceptable (records carry a ticket id and timestamp, so an exact
   duplicate should be rare and harmless) or whether a dedup-on-read pass
   in the reader is warranted. Report the finding either way -- do not
   add a dedup mechanism speculatively.

5. Document the resolution rule in `docs/modules/tickets.md` next to the
   existing merge-driver section, so the next agent that hits a conflict
   reads "this is handled, do not hand-edit" instead of improvising.

AUDIT WHILE YOU ARE HERE: `rapid-debt.jsonl` is unlikely to be the only
tracked append-only file without a merge rule. List every tracked
`.jsonl` (and any other append-only artifact) and report which ones lack
a `.gitattributes` entry. Fix them in this ticket if they are the same
shape; file follow-ups if they are not. One file fixed while its three
siblings keep conflicting is the shape of a half-fix.
