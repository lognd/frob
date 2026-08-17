---
id: T-2255
title: T-1946's orphaned-evidence land guard fails OPEN when test collection fails
  -- the normal case in agent worktrees -- and let T-2240 orphan 11 tickets' evidence
  (28 COV003, floor 35 to 59)
state: in-progress
kind: bug
origin: human
created: '2026-08-16'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: When collect_python_tests fails, the land does not silently proceed as if
    the check passed; the skip is surfaced as explicit UNMEASURED state, never a silent
    Ok(None)
  evidence: []
- text: A land removing a test function bound as evidence on another ticket is refused
    even when the containing FILE survives (the T-2240 shape)
  evidence: []
- text: 'MUST-STILL-PASS: deleting an unbound test still lands cleanly; deleting and
    re-adding the ticket''s OWN evidence in one diff is still not refused'
  evidence: []
- text: A worktree that genuinely cannot collect does not become unlandable; state
    what it does instead and why that is safe
  evidence: []
- text: The land's own record distinguishes 'check ran and passed' from 'check skipped'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# T-1946's orphaned-evidence land guard fails OPEN on test-collection failure -- the common case in agent worktrees -- and let a land orphan 11 tickets' evidence

## Measured evidence (2026-08-16)

Unscoped floor went **35 -> 59 errors** in one hour. Coverage verified complete
before trusting it (43 results, `gate-summary` present, all 24 `gate:*`
families). The entire regression is one class:

    28  gate:COV:COV003
     7  gate:TICK:TICK004
     6  gate:ARCH:ARCH001
     4  frob-cycle
     ...

All 28 COV003 findings name the same file:

    28  tests/unit/test_makefile_coverage.py

Orphaning evidence bound on **11 other tickets**: T-1205, T-1235, T-1335,
T-1353, T-1362, T-1373, T-1397, T-1426, T-1433, T-1526, T-1363.

Cause: T-2240 (`dcb07727d8ce`) legitimately retired the Makefile-text-slicing
tests, rewriting that file 924 -> 195 lines. The file SURVIVED; ~28 test
functions inside it did not.

## The guard for this exists, and it did not run

T-1946 (done) shipped `_check_orphaned_evidence_deletion`
(`src/frob/tickets/_land.py:4439`), which refuses a land with
`LandError.OrphanedEvidenceDeletion` when the branch's own diff deletes a
pytest node bound as evidence on a different ticket. It is node-level by
design, so a rewrite-in-place is exactly what it should catch.

It has two unconditional fail-open returns:

    if changed.is_err:
        _log.warning("land: %s orphaned-evidence check skipped -- diff unreadable (%s)", ...)
        return Ok(None)
    ...
    collected = collect_python_tests(worktree)
    if collected.is_err:
        _log.warning("land: %s orphaned-evidence check skipped -- test collection failed (%s)", ...)
        <skips the check>

**The skip condition is the normal condition in an agent worktree.** This
repo's own operating notes record that fresh worktrees lack `strata_core` /
`frob_core` builds and that collection/evidence failures there are environment
artifacts rather than regressions. So the guard is disabled precisely where
lands happen.

This is the same shape already recorded for a different land-time check: a gate
spawn refused under `FROB_AGENT`, its empty result read as "unmeasured", then
skipped permissively. Two independent land-time guards, same failure mode.

## Why a playbook line is not the fix

`docs/guides/agent-playbook.md:924` already carries "## 9. The deletion-filter
land rule (verify before every finish)". The rule is written down, the guard is
implemented, and 11 tickets' evidence was still orphaned -- because the guard
silently opted itself out and nothing surfaced that it had. An agent doing
everything right cannot tell the difference between "check passed" and "check
skipped".

## Do NOT fix it this way

- **Do NOT make the check hard-fail whenever collection fails.** Collection
  legitimately fails in a fresh worktree that has not built natives; refusing
  every such land would block the fleet on an environment artifact. That is a
  worse outcome than the bug.
- **Do NOT drop to a filename-level comparison** ("did the diff delete a file
  containing bound evidence"). T-2240 did not delete the file. A path-level
  check misses the exact incident that motivated this ticket, and the guard is
  deliberately node-level.
- **Do NOT rely on COV003 catching it afterwards.** It does -- that is how this
  was found -- but only on the next unscoped `frob check`, after the land is
  published and the orphan is already in the floor. The land is the last point
  where the deleting branch still knows what it deleted.
- **Do NOT parse the diff text for `def test_` lines.** Standing user
  directive: token/grammar, never lexical. Node identity must come from
  collection or a parsed tree, not from matching source text.

## Acceptance criteria

1. (MUST FAIL FIRST) When `collect_python_tests` fails, the land does NOT
   silently proceed as if the check passed. It must either resolve node
   identity another way, or surface the skip as an explicit,
   operator-visible UNMEASURED state that the land records -- never a silent
   `Ok(None)`. Fails today: two unconditional fail-open returns.
2. A land whose diff removes a test function bound as evidence on another
   ticket is refused, even when the containing FILE survives (the T-2240
   shape). Build the fixture from the real case: 28 nodes removed from a
   surviving `tests/unit/test_makefile_coverage.py`.
3. MUST-STILL-PASS CONTROLS: a land deleting an UNBOUND test still lands
   cleanly, and a land that deletes and re-adds its OWN ticket's evidence in
   the same diff is still not refused. Both behaviours have tests from T-1946
   (`test_deletion_of_unbound_test_lands_cleanly`) and must keep passing.
4. A worktree that genuinely cannot collect (no natives built) does not become
   unlandable. State what it does instead and why that is safe.
5. Whatever the outcome, the land's own record shows whether this check RAN.
   "Passed" and "skipped" must be distinguishable after the fact.

## Residue, not this ticket's job

The 28 already-orphaned COV003 findings need repointing or the citing tickets
need updating. That is separate cleanup; this ticket is about no twelfth ticket
being orphaned.

## Scope note

`src/frob/tickets/_land.py` is currently held by a live T-2220 lease. This
ticket must wait for that to land -- do not dispatch them concurrently.
