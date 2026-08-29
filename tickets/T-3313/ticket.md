---
id: T-3313
title: ticket scope --add is all-or-nothing on multiple globs; breadth-ack does not
  persist to start; mirror message misleading
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_scope.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-046, F-022). Three
distinct `scope --add`/scope-warning ergonomics defects bundled because they
share the same command surface.

F-046 IS CONFIRMED IN CODE: `mutate_scope`'s own docstring
(src/frob/tickets/_scope.py, around line 660) states "FAILS LOUDLY (`Err`, no
partial write)" -- `_validate_scope_mutation` checks EVERY `add`/`remove`
glob and returns a single `Err` on the FIRST conflict found
(`scope_lease_conflict`, called once over the whole `add_globs` tuple), with
no per-glob partial application. So `frob ticket scope T-X --add tests/a
--add tests/b --add docs/model.md --add src/model/__init__.py`, where ONLY
docs/model.md is lease-held elsewhere, fails the WHOLE command -- the two
uncontended test-file adds are silently rejected too, and the error names
only the FIRST conflicting glob it happens to check, not every conflicting
glob in the batch, forcing the reporter to bisect by re-running with fewer
--adds.

F-022 (two separate observations, not independently code-verified here --
confirm both before fixing):
  (a) `--scope-breadth-ack` passed at `frob ticket new` filing time does not
      silence the SAME breadth warning when `frob ticket start` runs later
      against the same glob -- the ack does not appear to persist/propagate.
  (b) `frob ticket scope --add` prints "scope mirrored onto the primary
      checkout", which reads as if it wrote into main's WORKING TREE
      (uncommitted files), when it presumably means a ledger-only mirror
      commit. Reword for clarity regardless of which it turns out to mean.

WHAT NOT TO DO (F-046): do not "fix" this by silently dropping the
conflicting glob and applying the rest without telling the caller which one
was dropped -- that hides a real conflict. The fix is either (i) apply every
non-conflicting glob and report exactly which ones were rejected and by
whom, in ONE error, or (ii) keep fail-loud-atomic but name EVERY conflicting
glob in the single error message, not just the first. Either removes the
bisection cost; pick and state which.

WHAT TO BUILD:
  1. F-046: per above -- name every conflicting glob (minimum fix), or apply
     what can be leased and report what cannot (stronger fix); state which
     you built and why.
  2. F-022(a): confirm whether `--scope-breadth-ack` is meant to be
     persistent across the ticket's lifetime; if so, find why `start` does
     not see it and fix the propagation.
  3. F-022(b): reword the "mirrored onto the primary checkout" message to
     say plainly what it means (a ledger commit onto main's tracked ledger
     file, not a working-tree write).

MUST-FIRE FIXTURE (F-046): `scope --add` with N globs, exactly one leased
elsewhere -- error names ALL conflicting globs (or the command succeeds for
every non-conflicting one and reports the rejected ones), never a single
opaque failure needing bisection.

MUST-STAY-QUIET FIXTURE: `scope --add` with zero conflicts -- succeeds
exactly as today.
