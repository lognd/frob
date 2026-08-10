---
id: T-2026
title: An interrupted ledger verb leaves an untracked ticket dir that DirtyMain-blocks
  every agent land, with no agent-reachable recovery
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
DIRECT PRECEDENT: T-1936 (done) -- "frob ticket reconcile --apply leaves the
ledger dirty and silently DirtyMain-blocks" -- is this same failure one verb
over, and it was fixed by auto-committing. Read it before designing anything.

MEASURED 2026-08-10, twice, both costing other agents real time.

`frob ticket new` writes `tickets/T-####/` and its ledger entry, then commits
LAST (T-1130, deliberately: one commit captures the whole filed block
including `--evidence` ids, rather than a partial commit). That design is
correct for coherence and creates a window: any interruption between the
writes and the commit leaves an UNTRACKED `tickets/T-####/` directory in the
shared primary checkout.

That torn state then refuses every agent's land with `DirtyMain`
(`src/frob/tickets/_land.py:1948`), whose message correctly says "this is NOT
a crashed land... an agent cannot fix this by retrying... whoever owns the
root checkout must commit or stash it". So a half-finished FILE operation
blocks every LAND repo-wide, and no agent can clear it.

Incident: a coordinator retry loop around `frob ticket new` (needed because
the verb refuses under `LandInProgress` almost continuously at 5-6 agent
dispatch) was killed mid-run. It left `tickets/T-2017/` untracked. An agent
with finished, tested, gate-clean work for T-1940 sat blocked 7+ minutes,
correctly diagnosed the cause, and correctly refused to touch the shared
root. Cleared by `git add tickets/T-2017/ && git commit` (`279f2fe36`).

WHY IDEMPOTENCY IS NOT THE MAIN GAP (measured, so the fix is not misaimed):
`frob ticket new` already has duplicate protection -- an exact-title
duplicate guard (an agent hit it today and refiled with a varied title) plus
T-1995's `related_tickets` title-similarity gate requiring `--ack-related`.
A retry that re-runs after a SUCCESSFUL attempt is therefore already largely
refused. The unprotected failure is not double-creation, it is the torn
half-created state. Any fix that adds request-dedup keys and stops there
would solve the wrong problem.

## Do not fix it this way
- Do NOT move the commit earlier to shrink the window. T-1130 chose
  commit-last on purpose so the single commit captures the whole block; an
  earlier commit reintroduces partial-ticket commits, and the window still
  exists, just smaller.
- Do NOT tell callers to write safer retry loops. That is the weakest tier of
  fix (a rule, not an enforcement), and it has already failed once here: I
  wrote the loop, I knew the hazard, and it still happened.
- Do NOT make `DirtyMain` ignore untracked files generally. It is protecting
  a real invariant, and blanket-ignoring untracked paths would let genuine
  uncommitted work be silently swallowed by a land.
- Do NOT auto-`git clean` anything. Deleting an untracked ticket directory
  destroys a just-filed ticket -- this exact directory WAS a real ticket
  (T-2017) that is now landed work.

## Fix directions worth weighing (choose with evidence)
- Follow T-1936's precedent: make the condition self-healing. The next ledger
  verb (or `frob check` / `frob ticket doable`, where the operator already
  looks) detects an untracked, well-formed `tickets/T-####/` with no commit
  and commits it, reporting what it did.
- Or make the write atomic: stage into a temp location and move into place
  only when the commit is ready, so an interruption leaves nothing.
- Either way, `DirtyMain`'s refusal should distinguish "an interrupted frob
  verb left this, and here is the one command that fixes it" from "a human
  has uncommitted work here" -- the current message treats both identically.

## Acceptance criteria
1. A test that FAILS FIRST: simulate an interrupted `frob ticket new` (create
   the ticket directory, skip the commit), then assert `frob ticket land`
   currently refuses with `DirtyMain`. Then assert the new behavior.
2. A genuinely human-dirty root (an edited source file, unrelated untracked
   work) must STILL refuse -- assert no over-reach, since swallowing real
   uncommitted work is far worse than the blockage this fixes.
3. Report which other ledger-mutating verbs share the write-then-commit
   window (`ticket start`, `close`, `drop`, `scope`, `evidence`, ...), with
   the denominator examined. Any that share it are this ticket's residue.
