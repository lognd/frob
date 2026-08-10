---
id: T-1628
title: 'strata: capability via lists only ever grow -- add a one-way ratchet'
state: done
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1627
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- tests/unit/strata/test_selfconform.py
- src/frob/gates/_waive.py
- src/frob/strata/_effects.py
- docs/design/registry/capability-via-ratchet.lock.json
- tests/unit/strata/test_effects.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: tests/** and src/frob/gates/** are mega-globs and scope IS the lease; as
    written this ticket would lock the fleet out of the whole tests tree. Narrowed
    to the selfconform test and the rule registry the ratchet actually needs.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/gates/**
  reason: tests/** and src/frob/gates/** are mega-globs and scope IS the lease; as
    written this ticket would lock the fleet out of the whole tests tree. Narrowed
    to the selfconform test and the rule registry the ratchet actually needs.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: tests/** and src/frob/gates/** are mega-globs and scope IS the lease; as
    written this ticket would lock the fleet out of the whole tests tree. Narrowed
    to the selfconform test and the rule registry the ratchet actually needs.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive.py
  reason: tests/** and src/frob/gates/** are mega-globs and scope IS the lease; as
    written this ticket would lock the fleet out of the whole tests tree. Narrowed
    to the selfconform test and the rule registry the ratchet actually needs.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/strata/**
  reason: src/frob/strata/** matches 71 files (>25) -- narrow to the one module the
    ratchet lives in plus its committed lock artifact
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_effects.py
  reason: src/frob/strata/** matches 71 files (>25) -- narrow to the one module the
    ratchet lives in plus its committed lock artifact
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: src/frob/strata/** matches 71 files (>25) -- narrow to the one module the
    ratchet lives in plus its committed lock artifact
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: SYS111 capability ratchet tests belong beside check_stale_via_symbols/other
    _effects.py tests, matching the module's own existing test-file convention
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/surface.md
  reason: 'AFFECT001: the new capability-ratchet symbols cite docs/strata/surface.md#may-scope
    as their frob:doc anchor and the affects()-closure gate requires that section
    touched in the same diff'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_effects.py::TestCapabilityViaSiteCounts::test_counts_scoped_via_entries
- tests/unit/strata/test_effects.py::TestCapabilityViaSiteCounts::test_unscoped_grant_contributes_nothing
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_growth_without_lock_entry_fails
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_at_or_below_ceiling_is_silent
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_growth_beyond_justified_ceiling_fails
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_shrink_is_silent
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_shrink_then_regrow_within_ceiling_stays_silent
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_growth_beyond_justified_ceiling_fails_even_after_a_prior_shrink
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_deleting_lock_entry_does_not_bypass_the_ratchet
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_empty_reason_is_flagged
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_missing_lock_file_treats_every_scoped_grant_as_unaccepted
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_unscoped_grant_is_never_ratcheted
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Capability `via` lists in design/frob.strata only ever grow. When a new file starts writing to disk, the fix is to append it to the fs.write list, and nothing anywhere pushes back. The self-model therefore documents an ever-loosening posture while looking green the whole time.

Add a ratchet: a via list may SHRINK freely, but growing it requires an explicit, recorded justification -- the same posture the repo already applies to waivers (a reason plus a follow-up), and the same one-way discipline T-1575's profile auto-ratchet uses (tighten automatically, loosen only by deliberate act).

Mechanically: record each capability's declared site count in the baseline the gates already keep; fail when a count increases without an accompanying justification attribute on that declaration; pass silently when it decreases.

This is what converts the capability model from documentation into enforcement. Today a developer who adds an exec call in a new file gets a SYS finding, appends the file, and moves on -- the gate taught them the ritual for widening the boundary rather than making them argue for it.

Report, as part of this ticket, the current per-capability site counts so there is a baseline to ratchet from and a number to drive down later.

## Done report

Implemented the one-way capability via-list ratchet as
frob.strata._effects.capability_via_site_counts/capability_ratchet_violations,
comparing each (node, atom) pair's current scoped via-list SITE COUNT
against a committed lock file (docs/design/registry/capability-via-ratchet.lock.json,
CAPABILITY_RATCHET_LOCK_REL) that records the accepted ceiling plus a
non-empty reason -- the same reason-bearing discipline frob:waive already
requires, applied to a capability's blast radius instead of a gate rule.
Growing past the ceiling without a matching lock edit is a violation;
shrinking, holding steady, or regrowing back up to (never past) an
already-justified ceiling is always silent.

BASELINE (ticket's own acceptance ask -- report the current per-capability
site counts): docs/design/registry/capability-via-ratchet.lock.json now
carries 56 (node, atom) entries measured directly against design/
frob.strata at T-1628 time, largest being testsuite::fs.write (297),
testsuite::exec (158), testsuite::fs.read (121). Verified this baseline
produces ZERO violations against the same tree
(capability_ratchet_violations(model, root) == () measured directly).

BYPASS PATHS TESTED (asymmetric-failure-mode instruction: a security
ratchet's real risk is wrongly ALLOWING growth, not wrongly blocking it):
1. Deleting a lock entry does NOT reset its ceiling to "anything goes" --
   a missing entry reads as accepted_count=0 (the STRICTEST possible
   ceiling), so an attempt to launder an already-justified capability by
   erasing its lock history re-triggers the growth violation immediately
   at whatever the current count is.
   (test_deleting_lock_entry_does_not_bypass_the_ratchet)
2. Shrink-then-regrow bypass: growing back UP TO a previously justified
   ceiling after an intervening shrink stays silent (not a NEW widening --
   the ceiling was already earned once); growing PAST that same ceiling,
   even after the shrink, still fires -- the ceiling is a high-water mark,
   not a moving average a temporary dip can reset.
   (test_shrink_then_regrow_within_ceiling_stays_silent +
   test_growth_beyond_justified_ceiling_fails_even_after_a_prior_shrink)
3. A missing lock file entirely is deny-by-default (every scoped grant
   reads as unaccepted), not "nothing to check".
   (test_missing_lock_file_treats_every_scoped_grant_as_unaccepted)
4. A lock entry with an empty/missing reason is itself flagged, same
   WAIVE001 discipline. (test_empty_reason_is_flagged)

DISCLOSED SCOPE CUTS (not silently dropped, module docstring's own
section): (a) an UNSCOPED grant (via=()) is never counted -- a
different, strictly broader risk shape (whole-node access) this
via-list-specific ratchet does not attempt to bound
(test_unscoped_grant_is_never_ratcheted). (b) renaming a node/atom to
dodge tracking under a new key is not detected -- a genuinely new
(node, atom) pair reads as a fresh, unratcheted baseline like any first
sighting. Both are real residual gaps, named rather than assumed
covered.

NOT WIRED INTO frob sys audit / a live gate rule (WIRE001-waived,
follow_up=T-1977): the actual CLI/gate surface
(src/frob/gates/_sys_selfaudit.py, frob.strata._selfconform's
_collect_sys_violations) is out of this ticket's declared scope
(src/frob/strata/_effects.py only) -- the SAME disclosed-gap shape
SYS109's own T-1627 left (check_stale_via_symbols module docstring).
capability_ratchet_violations is a fully tested, standalone function
today; a real rule id (e.g. SYS111) is assigned only once it fires
through a production Violation-producing gate path, matching this
repo's convention that "SYS1xx" only names a LIVE, wired rule.

Changed:
- src/frob/strata/_effects.py: CAPABILITY_RATCHET_LOCK_REL,
  CapabilityRatchetViolation, capability_via_site_counts,
  capability_ratchet_violations (all new); module-level design-rationale
  comment block
- docs/design/registry/capability-via-ratchet.lock.json (new, 56-entry
  baseline)
- tests/unit/strata/test_effects.py: TestCapabilityViaSiteCounts (2
  tests), TestCapabilityRatchet (10 tests, explicitly covering both
  bypass shapes named above)

Filed: T-1977 (wire capability_ratchet_violations into frob
sys audit / a real gate rule).

Evidence: 12 node ids bound (see evidence list).

Gates: tests/unit/strata/test_effects.py + test_selfconform.py -- 119/119
passed. frob check --ticket T-1628 --only test --only sys --only wire --
0 errors (WIRE001 waived with follow-up, disclosed above).
frob check --only coverage -- 0 new findings for src/frob/strata/_effects.py.

### Changed
```
 .../registry/capability-via-ratchet.lock.json      | 286 +++++++++++++++++++++
 rapid-debt.jsonl                                   |   1 +
 src/frob/strata/_effects.py                        | 191 ++++++++++++++
 tests/unit/strata/test_effects.py                  | 182 ++++++++++++-
 tickets/T-1628/done-report.md                      | 120 +++++++++
 tickets/T-1628/ticket.md                           |  53 +++-
 tickets/T-1977/ticket.md                 |  23 ++
 7 files changed, 853 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestCapabilityViaSiteCounts::test_counts_scoped_via_entries` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityViaSiteCounts::test_unscoped_grant_contributes_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_growth_without_lock_entry_fails` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_at_or_below_ceiling_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_growth_beyond_justified_ceiling_fails` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_shrink_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_shrink_then_regrow_within_ceiling_stays_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_growth_beyond_justified_ceiling_fails_even_after_a_prior_shrink` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_deleting_lock_entry_does_not_bypass_the_ratchet` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_empty_reason_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_missing_lock_file_treats_every_scoped_grant_as_unaccepted` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_unscoped_grant_is_never_ratcheted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 2 error(s), 1181 warning(s), 709 waived
- error-findings: DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1628
