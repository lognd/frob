---
id: T-0594
title: Wire ratchet-pool severity resolution into a real gate (frob.gates.__init__)
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- frob.toml
- docs/modules/gates.md
- tests/test_gates.py
- frob-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'ticket body scope: the one resolve_ratchet_severity call site plus config/docs/tests
    wiring INV006 into ratchet, plus the committed baseline lock file the wiring produces'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: frob.toml
  reason: 'ticket body scope: the one resolve_ratchet_severity call site plus config/docs/tests
    wiring INV006 into ratchet, plus the committed baseline lock file the wiring produces'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/gates.md
  reason: 'ticket body scope: the one resolve_ratchet_severity call site plus config/docs/tests
    wiring INV006 into ratchet, plus the committed baseline lock file the wiring produces'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates.py
  reason: 'ticket body scope: the one resolve_ratchet_severity call site plus config/docs/tests
    wiring INV006 into ratchet, plus the committed baseline lock file the wiring produces'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: frob-ratchet.lock.json
  reason: 'ticket body scope: the one resolve_ratchet_severity call site plus config/docs/tests
    wiring INV006 into ratchet, plus the committed baseline lock file the wiring produces'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestInv006Gate::test_ratchet_fresh_finding_errors_when_rule_enabled
- tests/test_gates.py::TestInv006Gate::test_ratchet_baselined_finding_stays_warn
- tests/test_gates.py::TestInv006Gate::test_ratchet_rule_not_enabled_stays_static_warn
- tests/test_gates.py::TestInv006Gate::test_this_repos_frob_toml_and_ratchet_lock_calibrate
designated_repro_test: null
threat: null
component: null
---
T-0569 built frob.gates._ratchet (RatchetLock/snapshot_ratchet/clear_ratchet_entry/resolve_ratchet_severity/ratchet_enabled_rules) as a complete, additive, self-contained mechanism + CLI (frob pool snapshot/clear), deliberately NOT wired into any live gate's severity resolution because src/frob/gates/__init__.py's per-rule dispatch is large shared surface owned by a concurrent wave. This ticket is that follow-up: pick one real warn-first rule (e.g. INV006 or PII010), opt it into [gates.ratchet] rules, and call resolve_ratchet_severity at that gate's severity-decision call site so a baselined finding stays warn and a fresh one errors for real, not just in tests/test_gates_ratchet.py's synthetic fixture. Scope: src/frob/gates/__init__.py (the one call site), frob.toml, docs/modules/gates.md.