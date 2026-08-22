---
id: T-2886
title: 'Fleet worktrees run stale src/ post-land: audit staleness/leases/unlanded
  work, propose per-worktree disposition'
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/worktrees/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record the full per-worktree audit measured across all 39 .claude/worktrees/
    entries, with proposed dispositions, for coordinator approval before any removal
  actor: logan
  at: '2026-08-22'
  old_length: 1833
  new_length: 7453
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Measured tonight (coordinator + confirmed independently): each git
worktree under .claude/worktrees/ carries its OWN editable install
pointing at THAT worktree's src/, not main's. On the primary checkout,
9 worktrees have arm_parent_death_signal in their own
src/frob/process/_reap.py (T-2849's forkserver-leak fix); the rest do
not. Any agent running frob check from a stale worktree executes
pre-T-2849 pool-construction code and leaks forkservers exactly as
before the fix.

THE GENERAL FORM (the real finding, not just this one leak): a stale
worktree runs stale code for EVERY land, not just T-2849's. Any fix
whose correctness depends on all agents actually running it is silently
defeated by a worktree that never merged main. This is a fleet-
integrity problem.

## Plan

1. Enumerate every worktree under .claude/worktrees/, measure staleness
   (commits behind main, last-commit age via fleet_status).
2. For each, check for a live lease (in-progress ticket) -- active, not
   stale.
3. For each remaining candidate, verify by CONTENT not ancestry before
   proposing removal: `git -C <wt> log --oneline main..HEAD` plus
   `git diff --stat main <branch> -- src tests docs`. Empty content
   diff = genuinely superseded. Non-empty = someone's unlanded work;
   do not touch.
4. Propose a disposition per worktree: refresh (merge main), reap
   (coordinator-approved removal only), or leave (live lease / genuine
   unlanded work needing hand-off).
5. Do NOT bulk-remove anything. Report findings; removals need explicit
   coordinator approval.
6. Record a recommendation on whether `frob ticket work` should refuse
   or auto-refresh a worktree whose branch is more than N commits
   behind main -- this ticket documents the recommendation, a follow-up
   ticket would build it.

## Failure log

(none yet)

## Audit findings (2026-08-22, all 39 worktrees under .claude/worktrees/)

### Method
For each worktree: (1) checked fleet_status for a live lease, (2) found
its ticket's terminal state, (3) found the terminal ticket's actual land
commit on main via `git log --grep`, (4) diffed the worktree's HEAD
against that land commit restricted to `src tests docs`. Where the diff
was non-empty (main had moved on since the land point), I did NOT stop
at diffstat noise -- I isolated the worktree's OWN unique commits
touching `src tests docs` (`git log --oneline main..HEAD -- src tests
docs`), then for any real (non-ledger) code commit among them, grepped
main's CURRENT tree for the specific function/test/doc-anchor that
commit introduced, to confirm the content is present under whatever
name/shape it now has (a different commit can carry equivalent content
after a rebase/regression-fix/re-land).

### Staleness (code, not just lease)
9 worktrees have T-2849's `arm_parent_death_signal` in their own
src/frob/process/_reap.py (t-2869, t-2870, t-2871, t-2872, t-2875,
t-2877, t-2879, t-2880, t-2883 -- all created/refreshed after T-2849
landed). 30 do NOT and would run pre-T-2849 forkserver-pool code if a
check ran from them today. Ages range from single-digit minutes to the
oldest at ~17,880 minutes (~12.4 days) behind (gate-internals,
land-integrity-series, t1893-t1908).

### Live leases -- ACTIVE, do not touch
- t-2875 (T-2875, in-progress)
- t-2883 (T-2883, in-progress)

### Verified SAFE (ticket(s) done, content confirmed present on main)
Every one of the following was checked by the method above and its
worktree's own unique code content is either an exact-empty diff
against its land commit, or (where main moved since) confirmably
present in main's current tree under the same or an evolved
implementation:

t-1614 (T-1614, periodic RUNS LAST ticket), t-1778 (queued, zero real
commits -- never did work), t-1945, t-2071, t-2125, t-2355, t-2356,
t-2489, t-2490, t-2508, t-2523, t-2547, t-2612 (+ its follow-on T-2611),
t-2778, t-2796, t-2801, t-2806, t-2845, t-2850, t-2855 (+ T-2864/T-2863
follow-ons), t-2858, t-2869, t-2870, t-2871, t-2872, t-2877 (this
session's own, just landed), t-2879, t-2880 (state now shows "queued"
because a follow-up finding requeued it post-land -- its own land IS on
main, content matches exactly), t1661-series (T-1654), t1860-series
(T-1860 -- the apparent 280-file diff was pure main-divergence noise;
the worktree's only unique src/tests/docs commits are the ticket's own
already-landed pre-land snapshot and a `frob ticket show` artifact
commit that never touched code), t1893-t1908 (2 real commits --
`_READ_ONLY_VERBS` debt/deprecated/wave classification and a WAIVE004
docs addendum -- both individually confirmed present in main's current
tests/test_ticket_leases.py and docs/modules/gates.md), t2747-t2746
(T-2746/T-2747), t2766-t2764 (T-1820/T-1831/T-2451 explicitly requeued
mid-worktree, T-2764/T-2766/T-2772 landed and content-matched),
rule-bookkeeping (2 real commits, T-1968/T-1970, both `state: done`;
the worktree's `_directive_edge`/`_unhandled_markdown_directive` helpers
are present in main's current src/frob/graph/dsl.py, evolved further by
the T-1989 regression-fix that followed T-1968's land), dev-friction
(T-2392/T-2393 -- `frob ticket close --no-behavior-change` and `frob
ticket body`, both of which I personally exercised THIS SESSION on
T-2871/T-2877, confirming they exist on main), gate-internals (T-1830,
`is_stamp_stale` dedup, present in main's _coverage.py), reg-enforce
(T-1916/T-1917, both done), land-integrity-series (T-1903, the
pre-Tier-A-rewrite strata parse-guard fix -- its LAND-PROOF verified=True
output format is the same one every land in this session produced).

No worktree in this pass held genuine unlanded work. That does not
retire the general risk (the coordinator's own report of two agents
finding real cases tonight stands -- those were presumably resolved or
are outside this snapshot's 39), but every worktree present RIGHT NOW
resolves to one of: LIVE (leave), or SAFE (content on main, reap-eligible).

### Proposed disposition
- t-2875, t-2883: LEAVE (live lease).
- All 36 SAFE-verified worktrees: eligible for `git worktree remove`
  (branch deletion left to your judgment -- some branch names like
  `t1860-series`/`t2766-t2764`/`t2747-t2746` were multi-ticket cluster
  branches with real history worth keeping tagged even after the
  worktree directory itself is removed).
- No refresh-in-place candidates found: every stale worktree here is
  fully superseded, not "behind but still useful if merged forward."

I am NOT running any removal -- this is the audit only, awaiting your
approval per your instruction.

### Recommendation on `frob ticket work` auto-refuse/refresh
Right shape, with a caveat: a hard commits-behind-main threshold should
WARN and require `--steal`-style explicit confirmation to proceed on a
stale worktree, rather than silently auto-merging main into it. Auto-
merging on every `ticket work` invocation risks exactly the collision
class T-1868/T-1093 already documented (a merge silently resurrecting
or dropping a draft ticket filed into the worktree ledger before the
merge). A refuse-and-suggest-refresh (surfacing `git -C <wt> merge
main` as the fix, requiring the agent to run it explicitly and verify
`git diff main -- tickets.md` after) fits the repo's existing "no
silent merge near reporting" doctrine better than an automatic merge.
Suggest a follow-up ticket to build the threshold check itself (not
this one -- this ticket is audit-only per your instruction).
