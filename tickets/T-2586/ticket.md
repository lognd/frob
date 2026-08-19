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
milestone: null
scope:
- scripts/fleet_status.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'scope closure: fleet_status frob:doc targets live here'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'root cause found: core.autocrlf=true on WSL, plus a measured genuine variant
    on the same path'
  actor: logan
  at: '2026-08-19'
  old_length: 2189
  new_length: 5845
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


## ROOT CAUSE FOUND -- supersedes the stat-dirty theory above

Measured on this clone:

    git config --get core.autocrlf   ->  true
    git config --get core.eol        ->  unset
    git check-attr text eol -- rapid-debt.jsonl
        rapid-debt.jsonl: text: unspecified
        rapid-debt.jsonl: eol:  unspecified

`core.autocrlf=true` is a WINDOWS setting and it is active on this
WSL/Linux checkout. Git therefore converts LF to CRLF in the WORKING TREE
while the index stores LF. A tool that rewrites the file (every rapid
sweep rewrites `rapid-debt.jsonl`) leaves working-tree content whose bytes
differ from the index blob, so `git status` reports `M`, while `git diff`
-- which applies the same normalization before comparing -- reports
nothing. That is exactly the divergence observed, and it is a better
explanation than the stat-cache theory originally filed above: the stat
cache would be cleared by any content-comparing read, but this reproduced
repeatedly across separate invocations.

Confirmed live during a land:

    warning: LF will be replaced by CRLF in rapid-debt.jsonl.
    The file will have its original line endings in your working directory

This is NOT specific to `rapid-debt.jsonl`. `autocrlf=true` with no
`.gitattributes` normalization applies to every text file git decides to
convert, so any file a tool rewrites can present the same phantom.

## Revised fix -- two independent layers, do BOTH

1. CONFIGURATION. `core.autocrlf=true` is wrong for a Linux/WSL checkout.
   The durable fix is a `.gitattributes` declaration that pins line endings
   for the repo's own generated/tracked artifacts (at minimum
   `rapid-debt.jsonl` and `force-overrides.jsonl`, which already carry
   `merge=union` there) rather than leaving them `text: unspecified` and at
   the mercy of a per-clone git setting. A per-clone `git config` change is
   NOT sufficient on its own -- it does not travel with the repo, and a
   clone that skips it silently falls back to the broken behavior. That is
   the same argument that chose a BUILT-IN merge driver for
   `rapid-debt.jsonl`; apply it here.

2. REPORTING. `scripts/fleet_status.py` must still confirm dirtiness by
   CONTENT before printing `ROOT DIRTY -- do not dispatch`, because a
   content-identical working file must never read as dirt regardless of why
   the bytes differ. Layer 1 removes this cause; layer 2 makes the report
   correct for any future cause.

## MEASURED: a genuine variant exists too -- do not suppress the path

Both variants occurred within one hour today:

- PHANTOM (3 occurrences): `git status` says `M rapid-debt.jsonl`,
  `git diff` empty, root actually clean.
- GENUINE (2 occurrences): the land's own post-land sweep FAILED to commit
  `rapid-debt.jsonl` and said so explicitly --
  "ERROR: rapid sweep: T-2561 could not commit rapid-debt.jsonl ... root is
  now DIRTY and the next land from any agent will refuse with DirtyMain".
  Verified real: `git diff --stat` showed `1 insertion(+)`, staged and
  unstaged (`MM`). Committed by hand as `a3584e131`.

So the same path produces both a false and a true dirty report. Any fix
that special-cases `rapid-debt.jsonl` will suppress the GENUINE case, which
is a real DirtyMain blocker for the whole fleet. Distinguish by content;
never by path.

## Positive controls -- updated

- content-identical rewrite (LF/CRLF differing bytes, same logical content):
  root reports CLEAN
- genuinely changed content: STILL reports ROOT DIRTY
- the specific genuine case above -- sweep leaves an uncommitted line in
  `rapid-debt.jsonl` -- STILL reports ROOT DIRTY
- untracked file in the root: STILL reports dirty