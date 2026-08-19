---
id: T-2586
title: fleet_status reports ROOT DIRTY from a stat-dirty index, falsely blocking dispatch
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
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
## Measured

`scripts/fleet_status.py` reported:

    ROOT DIRTY -- do not dispatch
      M  rapid-debt.jsonl

But `git diff rapid-debt.jsonl` and `git diff --stat rapid-debt.jsonl` were
BOTH EMPTY. After `git update-index --refresh`, `git status --porcelain`
returned nothing at all. The root was clean the whole time.

## Root cause

A stat-dirty index entry. Git caches (mtime, size, inode) per path; when a
file is rewritten with identical CONTENT -- which is exactly what
`rapid-debt.jsonl` gets from every deferred post-land sweep -- the stat data
changes and `git status` reports `M` without comparing content. `git diff`
does compare content, which is why the two disagreed.

## Why this matters more than a cosmetic wrong line

`ROOT DIRTY -- do not dispatch` is a HARD STOP in the dispatch workflow, and
it is the correct stop: a genuinely dirty root DirtyMain-blocks every agent
land, which this repo has paid for repeatedly. A false positive on that
signal stalls dispatch for a condition that does not exist, and the
resolution path is corrosive -- an operator who learns that ROOT DIRTY is
sometimes phantom starts overriding it, which defeats the guard on the real
occurrences.

`rapid-debt.jsonl` is written by every sweep, so this fires often.

## Fix

Confirm dirtiness by CONTENT before reporting it. Refresh the index
(`git update-index --refresh -q`) or use a content-comparing check rather
than trusting `git status`'s stat shortcut, then re-read. Report ROOT DIRTY
only for paths that genuinely differ.

Do NOT fix this by suppressing `rapid-debt.jsonl` specifically. The defect
is the stat-vs-content confusion and it applies to any path a tool rewrites
idempotently; a per-path exemption leaves the next one to be rediscovered,
and an exemption matching a routine case is how a guard gets disabled.

## Positive controls, both directions

- a file rewritten with identical content: root reports CLEAN
- a file with genuinely changed content: STILL reports ROOT DIRTY. Without
  this case the fix is indistinguishable from deleting the guard
- an untracked file in the root: STILL reports dirty (this is the
  retry-loop residue case that has blocked lands before)
