---
id: T-1796
title: 'A malformed design/frob.strata lands undetected: land''s Tier-A step warns-and-skips
  on ParseFailed instead of refusing'
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Evidence: a malformed `design/frob.strata` (an unterminated string
literal from two duplicated `may ... via` list entries merging into one
token -- see below) landed on main and broke `strata` parsing for every
subsequent `frob ticket land`'s Tier-A sync-interface/sync-may step,
silently, for an unknown number of lands, until noticed by chance while
debugging something unrelated (T-1779/T-1790 session). The coordinator
confirmed and fixed it at `aaa469df` (two copies of the same corruption,
in both the `fs.write` and `fs.read` via-lists).

MECHANISM, traced through the actual code:

1. `frob.gates._sys._sys004` DOES fire a loud `Severity.ERROR` for
   exactly this shape (`design_ids.errors` non-empty, a `.strata` file
   failed to load) -- the gate machinery to catch this ALREADY EXISTS
   and is not the gap.

2. The gap is TIMING, not detection: `frob ticket land`'s own Tier-A
   pre-land step, on encountering `ParseFailed` while trying to run
   `sys sync-interface`/`sync-may`, does not refuse the land -- it logs
   a WARNING ("pre-land sys sync-interface skipped: ParseFailed...") and
   PROCEEDS. Observed directly in this session's own land output. A
   corrupted `design/frob.strata` is therefore never a land-blocking
   condition at the one moment it would be cheapest to catch it.

3. `SELFAUDIT001` (`frob.gates._sys_selfaudit`) makes the SAME choice
   explicitly and by design, per its own docstring: "Suppressed... 
   whenever any design file failed to load -- self-audit cannot be
   honestly evaluated against a partial model." This is a deliberate,
   documented degrade-to-silence, not an oversight -- but its EFFECT,
   combined with (2), is that the one loud gate (SYS004) only fires on
   an explicit `frob check` invocation that happens to include the `sys`
   stage, and NOTHING in the land path forces that invocation before
   accepting a commit.

4. Under the `rapid` profile (active this session, `T-1681`), `frob
   ticket land` also skips its own pre-commit sweep -- the one place a
   full unscoped check might have caught this BEFORE the commit landed.
   The deferred post-land sweep (`T-1684`) is documented to file a bug
   ticket on a new finding, never revert the published commit -- so even
   if it eventually ran SYS004 against the corrupted file, the damage
   (every SUBSEQUENT land's Tier-A step silently degrading) was already
   locked in, and no bug ticket for THIS specific SYS004 finding appears
   to have been filed or noticed.

REQUIRED, in order of what closes the actual gap:

- `frob ticket land`'s Tier-A step should REFUSE (or at minimum loudly
  ERROR, not WARN-and-skip) when `sys sync-interface`/`sync-may` hits
  `ParseFailed` on a design file already tracked in the repo -- a
  pre-existing corruption should never be silently tolerated by the one
  process that mutates the ledger/design files on every land.
- Consider whether SYS004 (or an equivalent parse-health check) should
  be UNCONDITIONALLY part of every land's pre-commit path regardless of
  profile -- this is closer to "can the repo's own design model be
  loaded at all" than to the kind of slow, whole-repo sweep `rapid`
  exists to defer.

SEPARATE, filed here per the same evidence per the coordinator's
instruction (NO-DUPLICATION applied to config, not code): the actual
corruption was TWO IDENTICAL malformed entries, in `fs.write`'s and
`fs.read`'s `may ... via` lists, both listing the same hundreds-long set
of test file paths. Two agents' concurrent edits (each appending their
own new test file name to the SAME repeated list, appearing twice in the
same node) merged into one bad token in EACH copy independently -- the
same edit, wrong in the same way, twice, because the list itself is
maintained twice. A structure that repeats the same content across two
maintained copies will desync exactly like duplicated CODE does; consider
whether these `may ... via` lists can be expressed once and referenced
(or generated) for both `fs.write`/`fs.read`/other effect kinds that
share the same file set, rather than two parallel hand-edited copies of
hundreds of paths each.
