---
id: T-1730
title: frob ticket land should auto-rebase the worktree onto main after a successful
  land
state: dropped
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
## Description

Every single land I performed across two ticket groups in this session
(T-1673/T-1630/T-1675/T-1670/T-1679, then T-1714/T-1706) hit the same
sequence: land a ticket successfully (`LAND-PROOF: ... verified=True`),
then the NEXT `frob check --ticket <next-id>` in the same worktree reports
spurious SCOPE001/COV002 findings on files the just-landed ticket touched
-- because the worktree's own commits for that already-landed work are
still present on its branch, and the branch has not moved to include
main's new (squashed) tip. `git diff main` for those files then shows
non-empty content even though the content is byte-identical, because the
branch and main reached the same state via two DIFFERENT commits (the
worktree's own step-by-step history vs. land's squash-apply), so `git
diff main --stat` inherently looks non-empty for anything the worktree
itself changed, whether or not it matches main.

Observed sequence, every time, this session:
1. `frob ticket land T-XXXX --worktree <path>` succeeds, `LAND-PROOF ...
   verified=True`.
2. Start the next ticket in the same worktree; `frob ticket sweep`/`frob
   check --ticket <next>` reports SCOPE001 (files outside declared scope)
   and/or COV002 (changed-with-no-frob:ticket-edge) findings that are
   NOT caused by the next ticket's own work -- they are the just-landed
   ticket's files, which the worktree's branch still carries as its own
   uncommitted-relative-to-main diff.
3. Resolved every time by `git rebase main` in the worktree (dropping the
   now-"patch already upstream" commits git detects automatically, and
   skipping any obsolete `wip: pre-land snapshot for T-XXXX` commits
   land's own machinery leaves behind) BEFORE doing any more gate
   verification for the next ticket.
4. Repeat from step 1 for the next ticket in the series.

This is pure repeated friction -- the exact same manual recipe, by hand,
after every single successful land in a multi-ticket worktree series.
Per the standing directive (systematize repeated friction rather than
re-doing it by hand every time), this should be mechanical.

## Proposal

`frob ticket land --worktree <path>` should, after a successful land
(`verified=True`), automatically `git rebase main` the worktree's own
branch onto the new main tip it just produced -- dropping the now-
redundant commits the same way a manual rebase does (git's own "patch
contents already upstream" detection), before returning control to the
caller. This closes the loop the same way a human currently does by hand,
every time, immediately after every land in this session.

Open questions for whoever picks this up:
- Should this be unconditional, or opt-in via a flag (e.g. `--rebase-
  after`) for a caller that does not want its worktree branch rewritten
  automously? A single-ticket worktree (not a series) may not care either
  way; a series worktree needs it every time.
- What happens if the auto-rebase hits a REAL conflict (not just
  redundant-patch drops) -- should land still report success (the land
  itself is done) and just warn that the auto-rebase needs manual
  attention, rather than let a rebase conflict retroactively fail an
  already-successful land?
- Should the two housekeeping commit classes land already knows about
  (`wip: pre-land snapshot for T-XXXX`, ledger auto-commits) be preemptively
  dropped/skipped rather than relying on git's generic empty-patch
  detection, since land KNOWS which of the worktree's own commits are its
  own now-obsolete staging artifacts?

## Evidence (the actual observed sequence this session)

Every occurrence below is `git rebase main` run in
`.claude/worktrees/agent-ac2dad95d0b2b8809` immediately after a
`LAND-PROOF ... verified=True` line, always resolving 1-3 conflicts (the
shared `rapid-debt.jsonl` append-only log, occasionally a `tickets.md`
splice-driver conflict) and dropping 1-6 "patch contents already
upstream" commits per rebase:

- After landing T-1673: rebased before starting T-1630 (SCOPE001 on
  `rapid-debt.jsonl` and other post-land-sweep-touched files).
- After landing T-1630: rebased before starting T-1675 (same shape).
- After landing T-1675: rebased before starting T-1670 (plus resolving a
  CHANGELOG.md/land-owned-file pre-commit-hook collision on the first
  attempt, which forced an abort-and-rebase-instead-of-merge decision).
- After landing T-1670: rebased before starting T-1679.
- After landing T-1679: rebased before starting T-1714 (2 real conflicts
  in `src/frob/tickets/_store.py`, both trivially resolved by keeping
  HEAD's already-landed content).
- After landing T-1714/merging T-1701 (already landed by another agent):
  rebased before starting T-1706.

Six for six. This ticket exists so the seventh time is automatic.

## Drop reason
- 2026-08-07: Exact duplicate of T-1720 (identical title). Keeping the lower id. Part of the same batch re-filing as T-1728/T-1729. (absorbed by T-1720)
