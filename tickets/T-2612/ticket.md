---
id: T-2612
title: 'every waiver citing a LIVE lease has an expired premise: 0 of 12 named tickets
  still hold one'
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/scaffold/project.py
- src/frob/tickets/_reconcile.py
- src/frob/lang/_nodes.py
- src/frob/app/check_runner.py
- src/frob/gates/_mutation_evidence.py
- src/frob/tickets/_models.py
- src/frob/tickets/_evidence.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/lang/_nodes.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/check_runner.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_models.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/__main__.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/lang/_nodes.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/check_runner.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_models.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/__main__.py
  reason: T-2612 audit spans every waiver citing a now-terminal lease-holding ticket;
    these are the files with matching frob:waive reasons found by the audit grep
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

A `frob:waive` reason of the form "path P is under T-XXXX's LIVE
cross-worktree lease" is a legitimate and common pattern here: the waiver
author genuinely could not edit P without a ScopeLeaseConflict, so the
finding was suppressed with the lease named as the justification.

The problem is that the justification EXPIRES and nothing notices.

Every ticket currently cited as holding a live lease in such a reason, and
its state today:

    T-0764  archived        T-1720  done
    T-0854  archived        T-1739  archived
    T-1382  queued (epic)   T-1937  done
    T-1592  archived        T-2207  done
    T-1665  done            T-2365  done
    T-1703  archived        T-2485  done

**0 of 12 hold a live lease.** Eleven are terminal (done or archived).
T-1382 is QUEUED, and leases bind only at `in-progress` (T-0453), so a
queued epic holds no lease either.

(Measured by `git grep` for the "T-XXXX's LIVE/live lease" construction
across `src/**/*.py`, then reading each ticket's state. 68 lines mention a
lease in some form; not all are waiver reasons, so the LINE count is an
upper bound while the TICKET list above is exact.)

## Why this matters

Two concrete instances surfaced this session before the pattern was
measured:

- T-2598: an AFFECT001 waiver citing T-2582's live lease. T-2582 had
  landed; the doc it deferred was genuinely wrong (it described `frob
  cycle` as always exiting 0, when the exit code had become load-bearing),
  and the follow-up ticket its own reason PROMISED was never filed.
- `src/frob/scaffold/project.py`: an AFFECT001 waiver citing T-1382's
  "LIVE cross-worktree lease" on `docs/commands/scaffold.md`. T-1382 is a
  queued epic holding no lease.

A waiver whose premise has expired is worse than no waiver: it reads as a
considered engineering decision while silently suppressing a live finding
that nobody owns. That is the cop-out class T-1614's waiver audit exists to
catch, and this is a mechanically checkable subset of it.

## Two deliverables

1. **Audit and resolve the existing set.** For each waiver whose reason
   names a lease-holding ticket that is now terminal: re-check whether the
   underlying finding still fires. If the deferred work was done in the
   meantime, REMOVE the waiver. If it was not, do the work or file a ticket
   for it -- do not simply re-word the reason to keep it suppressed.

   An expired premise does NOT automatically mean the finding is live; the
   doc may have been updated since. Each needs its own check. Report the
   split: how many waivers were removable, how many hid real work.

2. **Make it enforceable.** A waiver reason naming a ticket should be
   checkable: when the named ticket reaches a terminal state, the waiver
   should surface for review rather than persisting silently. Coordinate
   with T-2606, which covers the adjacent case of a waiver reason promising
   a follow-up ticket that is never filed -- these two should share one
   mechanism, not become two parallel checks. If they cannot share, say why.

## What must NOT happen

Do not bulk-remove these waivers. Some suppress findings whose underlying
work is genuinely still owed, and removing the waiver without doing the
work just turns a hidden finding into a red gate with no owner. Each is an
individual judgment; the audit's value is making the judgment happen at
all.

Do not weaken AFFECT001 or any other rule to make this easier. The
detectors are correct; the waivers are the stale part.

## Positive controls, both directions

- a waiver whose named ticket is terminal AND whose underlying work is done
  is REMOVED, and the corresponding gate stays clean afterward
- a waiver whose named ticket is terminal but whose work is NOT done keeps
  a suppression (with a corrected, non-expiring reason) AND gains a ticket
  -- verify the finding would fire without it
- a waiver whose named ticket is genuinely still in-progress is left
  untouched. Without this case the audit is indistinguishable from deleting
  every lease-premised waiver
