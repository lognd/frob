---
id: T-1922
title: OutOfScopeWaiveDeletion false-refuses a land whose merge-base is stale relative
  to an unrelated upstream waiver reword
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-1918 (retrying T-1911's and T-1904's blocked lands).

T-1918 reworded a `frob:waive AFFECT001` comment's text in
src/frob/tickets/_renumber_v2.py (function name in the waiver reason
string changed from `_refuse_if_other_worktree_holds_live_lease` to
`_refuse_if_other_worktree_holds_live_lease_for_id`, wrapped across
slightly different line breaks). After T-1918 landed, retrying
`frob ticket land T-1911 --worktree .claude/worktrees/t1911-clean` (and
separately T-1904's worktree) both refused immediately with:

  ERROR: land: T-1911 refused -- branch history (commits since
  merge-base <stale-sha>) contains frob:waive deletion(s) outside scope
  [...] and undeclared by the Done report:
  ['src/frob/tickets/_renumber_v2.py:AFFECT001'] (real commits touching
  each file since main: {'src/frob/tickets/_renumber_v2.py': ("<sha>
  Merge branch 'main' into t1911-land",)})
  ERROR: ticket land failed: OutOfScopeWaiveDeletion

Root cause: `_land.py`'s branch-history OutOfScopeWaiveDeletion check
(around line 2084) diffs from the worktree's OWN merge-base (captured at
whatever `git merge main` last ran in that worktree, which for both
t1911-clean/verify-cluster pre-dated T-1918's land) forward to the branch
tip. Because that merge-base was stale, the diff includes T-1918's
reword of the AFFECT001 waiver text as if IT were a commit on the
landing branch's own history, and reads the literal old waiver string
disappearing as a "deletion" -- even though the landing ticket
(T-1911/T-1904) never touched _renumber_v2.py itself; it only inherited
the change transitively via its own `Merge branch 'main' into ...`
commit.

Confirmed workaround (not a fix): running a FRESH `git merge main` in
each worktree immediately before the land retry moved the merge-base
forward past T-1918's commit, and both retries then landed cleanly
(T-1904 landed at 1e524de9bec69141309638979a81296bded78d89; T-1911 got
past this check on retry too, though it then hit its own unrelated
BUG002 confirmatory-evidence finding).

The underlying defect: the check's "commits since merge-base" diff does
not distinguish "this branch's own commits changed/deleted the waiver"
from "an ALREADY-LANDED commit on main, picked up via a normal merge,
changed the waiver upstream of this branch's own work" -- the merge
commit itself carries the diff, and the check does not appear to
special-case merge commits or diff against CURRENT main instead of a
stale captured merge-base. Any concurrent worktree whose last main-merge
predates an unrelated waiver-text edit elsewhere in the repo will hit
this false refusal at land time, exactly the same "correct guard, wrong
scope/timing" shape as T-1918 itself.

Fix direction (not investigated further, out of T-1918's scope -- lives
in src/frob/tickets/_land.py, not touched by T-1918): either re-diff
against a freshly recomputed merge-base with CURRENT main at land time
rather than trusting the worktree's last captured merge-base, or exclude
lines whose "deletion" is fully explained by a merge commit pulling in
an already-landed, unrelated main-side edit.
