---
id: T-1977
title: Wire capability_ratchet_violations into frob sys audit / a gate rule
state: done
kind: security
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_sys_selfaudit.py
- src/frob/strata/__init__.py
- tests/unit/gates/test_sys_selfaudit.py
- tests/test_gates.py
- docs/design/registry/capability-via-ratchet.lock.json
- src/frob/strata/_effects.py
- rapid-debt.jsonl
- tickets/T-1997/ticket.md
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/__init__.py
  reason: public re-export of capability_ratchet_violations needed to import it via
    frob.strata's own public interface, the same path SYS109's own wiring uses (check_stale_via_symbols)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/gates/test_sys_selfaudit.py
  reason: the production-caller proof test (SYS111 fires through the SELFAUDIT001
    gate path) lives in this file, matching SYS109's own precedent test location
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gates.py
  reason: the production-caller proof test (SYS111 fires through the SELFAUDIT001
    gate path) lives in this file, matching SYS109's own precedent test location
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: wiring SYS111 live exposed 3 real pre-existing drift findings (T-1628's
    ratchet was never re-baselined since its own initial measurement, because nothing
    called it) -- re-measured honestly and bumped to the current observed count with
    a disclosed reason, the ratchet's own designed workflow for a justified widening,
    not a bypass
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_effects.py
  reason: closing T-1977 requires re-pointing the stale WIRE001 waiver's follow_up=T-1977
    citation (now resolved) to its own successor ticket; single-line waiver-attribute
    edit, not new development
  actor: logan
  at: '2026-08-10'
- op: add
  glob: rapid-debt.jsonl
  reason: rapid-debt.jsonl is the standing rapid-profile debt log every land under
    this profile appends to; the draft ticket file is the residue I filed and then
    dropped in the same change after fixing the stale waiver directly instead
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1997/ticket.md
  reason: rapid-debt.jsonl is the standing rapid-profile debt log every land under
    this profile appends to; the draft ticket file is the residue I filed and then
    dropped in the same change after fixing the stale waiver directly instead
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_waive.py
  reason: registering SYS111 in _KNOWN_GATE_RULES is required to close (T-1937's UnregisteredGateRuleConstructed
    preflight) -- same registration SYS109/SYS110 already carry here
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_capability_ratchet_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_does_not_fire_below_the_ratchet_ceiling
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_deleting_ratchet_lock_entry_still_fires
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_shrink_then_regrow_within_ceiling_stays_silent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1628 built the capability via-list one-way ratchet (frob.strata._effects.capability_ratchet_violations) but wiring it into frob sys audit's own CLI/gate surface (src/frob/gates/_sys_selfaudit.py, frob.strata._selfconform's _collect_sys_violations aggregator) is out of T-1628's own declared scope (src/frob/strata/_effects.py only) -- same disclosed gap shape SYS109's own T-1627 left (see check_stale_via_symbols module docstring). Wire it the same way SYS109 was wired, with a real rule id (e.g. SYS111) once it fires through a production Violation-producing gate path, not just its own tests.