---
id: T-1928
title: FMT gate passes in 0.00s while frob fmt --check would rewrite 267 files on
  main
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED on main, 2026-08-09, tree clean (git status --porcelain empty):

    uv run frob check --only fmt
      gate-summary  0 errors, 0 warnings, 1 waived  [fmt=0.00s]

    uv run frob fmt --check
      ... would rewrite: tests/unit/test_profile.py
      267 file(s) would change

    uv run frob check   (full, unscoped)
      FAIL  ruff-format   71 files would be reformatted

Three different answers to "is this repo formatted": 0, 267, and 71.
The gate that nominally enforces formatting reports clean, and its
0.00s runtime says it did no work at all.

WHY THIS MATTERS BEYOND TIDINESS. This is the catalogued-is-not-enforced
shape: a gate presented as coverage that measures nothing. Two concrete
harms, both live:

1. Accumulated drift is a landmine for every future ticket. Playbook 0.5
   says `frob ticket land` absorbs `frob fmt` on the worktree. If that
   absorption only touches the ticket s own files (the wording suggests
   it does), then the next ticket to touch any of those 267 files gets a
   large unrelated reformat swept into its land, blowing its scope and
   making its diff unreviewable. Several tickets today already fought
   OutOfScopeWaiveDeletion and scope-closure warnings; this is the same
   class of latent trap.
2. An agent running `frob check --only fmt` and seeing 0 errors
   reasonably concludes formatting is clean. It is not. That is a
   false-green, and this repo has already been bitten repeatedly by
   trusting a green number that was not measuring what it appeared to
   (T-1703 sweep false green, T-1907 vacuous evidence).

INVESTIGATE BEFORE FIXING -- I have NOT diagnosed this, only measured it.
Open questions, in order:
- Does the FMT gate deliberately only check the active ticket s touched
  set, and is therefore a no-op on main with no --ticket? If so the
  reported 0 is arguably correct-but-misleading, and the fix is
  disclosure (say what was and was not checked), not a behavior change.
  Note the gate:scope-note mechanism already does exactly this kind of
  disclosure for --only runs; reuse it rather than inventing a new one.
- Why do frob fmt (267) and ruff-format (71) disagree by ~4x? frob fmt
  presumably does more than ruff-format (directive wrapping and similar).
  Establish exactly what each covers before touching either.
- Is the 267 genuine drift, or is frob fmt applying a style the repo has
  not actually adopted? DO NOT reformat 267 files to make a number go
  green until this is answered. A 267-file reformat commit would be
  nearly impossible to review and would collide with every live worktree
  in the repo (there are ~16 right now, several holding unlanded work).

EXPLICIT NON-GOAL for whoever takes this: do not open with a mass
reformat. The deliverable is first an accurate ANSWER to "is this repo
formatted, by whose definition, and what does the gate actually check",
then a gate that cannot report clean for work it did not do. Bulk
reformatting, if it is warranted at all, is a separate ticket sequenced
when the live-worktree count is low.

ACCEPTANCE
1. Documented, evidence-backed explanation of the 0 / 267 / 71 spread.
2. `frob check --only fmt` can no longer report a bare clean result for
   a scope it did not examine -- either it examines the repo, or it
   discloses what it skipped in the same way gate:scope-note already
   does for partial --only runs.
3. A test proving 2: a repo with known unformatted files does not yield
   a bare 0-error FMT verdict. It must fail before the fix.
4. Any decision to accept the current formatting of those 267 files is
   recorded explicitly, not left implicit in a passing gate.