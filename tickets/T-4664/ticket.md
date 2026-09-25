---
id: T-4664
title: 'Story A: ratchet lock and the SYS111 mechanism -- one writer, a cache, a drift
  report, a derivable ceiling'
state: queued
kind: feature
origin: agent
created: '2026-09-19'
priority: high
parent: T-4662
tier: story
sprint: null
runs_last: false
milestone: 1.1.0
flavour: user_story
due: null
rank: null
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
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: story container under T-4662; the disjoint
  scopes live on its leaves'
triage_changes:
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
acceptance:
- text: Given the ratchet lock's measured baseline of 138 commits in 60 days (2.3/day)
    and capability_via_site_counts at 17.8s warm, when every child of this story is
    closed, then each carries a named positive-control pytest node that fails at HEAD
    c8f56ef10, and a second in-process call to capability_via_site_counts costs under
    1 second.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
Story A of T-4662. Covers SF-02, SF-03, SF-04, SF-05, SF-13, SF-14, SF-20.

THE MEASURED PROBLEM
docs/design/registry/capability-via-ratchet.lock.json is the highest-churn
artifact in the repo and it is maintained BY HAND on almost every land.

| id | measurement | evidence |
|---|---|---|
| SF-02 | 138 commits to the lock, ALL 138 within 60 days; 123 also touch design/frob.strata; CHANGELOG names capability-via-ratchet 53 times | git log -- docs/design/registry/capability-via-ratchet.lock.json |
| SF-03 | 3 shadow top-level keys diverge from `entries` and are ignored by the reader; 2 writers, 2 schemas, 1 file | capability-via-ratchet.lock.json; src/frob/strata/_effects.py:1441-1455, :1422; src/frob/gates/_fix_engine_sync.py:1362 |
| SF-04 | capability_via_site_counts 23.03s cold / 17.83s warm same process, no memoization; check --json median 717.1s max 1684.5s (n=145) | src/frob/strata/_effects.py:1154 |
| SF-05 | 7 keys under ceiling, total slack 45; 3 dead entries (cli::env, serve::eval, tickets_ledger::eval); 0 over ceiling, 0 unlocked | measured vs lock at HEAD |
| SF-13 | ratchet-race fix chain regressed 4x: T-4495 -> T-4563 -> T-4596 -> T-4607 -> T-4633 -> T-draft-a62505d4 | docstring src/frob/gates/_fix_engine_sync.py:1327-1337 narrates it |
| SF-14 | SYS111 fires on INTRODUCTION (ceiling 0): design + ceiling cannot be one commit | T-3833 (F-028), queued |
| SF-20 | load_design_ids has no cache; 7 call sites re-parse per run | src/frob/strata/_design_load.py; sys_runner.py:319,446,824; deploy_runner.py:84; _land_cmd.py:900; _policy_weakening_gate.py:172; _fix_engine_sync.py:1187 |

Verbatim CHANGELOG evidence that the churn lands on tickets with nothing to do
with strata: T-3411 (cycle-breaking refactor) "pushed the site count from 12 to
13 and required a reasoned bump"; T-3697 (a Claude hook) "testsuite::exec
ceiling 290 -> 291"; T-3777 (Windows test fixes) "ceiling bump 22->24";
T-3884 (release smoke test) "bumped exec/fs.read/fs.write ceilings".

SF-02 has no leaf of its own: it is the OUTCOME measure of this story. A4
(derive the ceiling instead of committing it) is the leaf that ends it.

SHAPE OF THE FIX (tooling and gate, never grammar)
one loader/writer/schema for the lock -> a digest-keyed cache so the scan is
paid once -> a drift report that can see slack and dead entries -> a derivable
ceiling so the race chain has nothing left to race on.

ACCEPTANCE
All children closed with a positive control, and the lock's commit rate after
the story is measurably lower than the 2.3 commits/day baseline recorded above.
