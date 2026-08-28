---
id: T-3181
title: Tracked agent scratch file emits a permanent REF001 ERROR in the repo error
  floor
state: in-progress
kind: bug
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
- .claude-scratch/**
- .gitignore
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude-scratch/**
  reason: the orphaned scratch capture and the ignore file that should cover it
  actor: logan
  at: '2026-08-27'
- op: add
  glob: .gitignore
  reason: the orphaned scratch capture and the ignore file that should cover it
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. `.claude-scratch/T-3122-close-guard-repro-capture.md` is
the sole tracked file under `.claude-scratch/`. It has no inbound reference from
any tracked file, so it emits REF001 at ERROR severity on every `frob check`:

    REF001@.claude-scratch/T-3122-close-guard-repro-capture.md

That finding appears in 39 done-reports as part of the pre-existing error floor.
Agents have been stepping around it all drive.

THE GATE IS CORRECT HERE. T-2369 promoted REF001 WARN -> ERROR precisely so new
orphan files could not silently reaccumulate. A scratch capture is not a
deliverable and nothing references it because nothing should. Do NOT waive this
finding -- fix the cause.

VERIFIED NOTHING CITES IT AS EVIDENCE: all 39 mentions in tickets/ are the
`REF001@` finding string itself, not a citation. T-3122's own done-report does
not reference it. T-3122 is `done`. Removing the file orphans no evidence edge.

WHAT TO DO
  1. `git rm --cached` the file and add the scratch directory to the repo's
     ignore file. Scratch captures are working files; the repo already ignores
     `.frob/` and `FROBLEMS.md` for the same reason.
  2. PRESERVE THE OBSERVATION rather than deleting it outright. The file
     captures a close-guard false-fire seen ONCE during series BT, under a
     concurrent `frob ticket land T-3115` and six concurrent fleet `frob check`
     runs. Move that content into a ticket body so it is triageable. Captured
     evidence of an unconfirmed race belongs in the queue, not in a loose file
     the reference gate must keep complaining about.
  3. When filing that successor, note that T-3131 was an UNCONFIRMED-ONCE
     guard false-fire dropped today as non-reproducing. Apply the same standard:
     try to reproduce it first. If it does not reproduce, record it as a
     one-sighting observation with the load conditions, or drop it with the
     reason -- do not carry an unreproducible finding as open work.

CHECK FOR OTHER INSTANCES. Do not fix only the one file named here. Search for
any other tracked path that exists solely as agent scratch (the scratch
directory, stray `*-capture.md`, `scratch-*` paths under the worktrees dir) and
report the count. `t-2356-scratch-golden-check.py` and `t1768.patch` under the
worktrees directory are visible candidates worth checking.

ACCEPTANCE
- REF001 no longer fires for the scratch directory; measured before and after.
- The repo ignore file covers that directory.
- The captured observation survives as a ticket, not as an untracked file that
  will be lost.
- A stated count of any other tracked agent-scratch paths found, with each
  either cleaned or explicitly justified as belonging in git.
