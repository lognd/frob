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