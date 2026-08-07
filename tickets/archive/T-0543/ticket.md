---
id: T-0543
title: 'gates: INV001 evidence is test EXISTENCE, not proof the invariant holds (B12)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
- docs/modules/gates.md
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- frob.lock
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: documented the new INV005 gate per the same doc-as-you-go convention every
    other INV rule in this table follows
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: T-0108 cross-ticket exemption needs a T-#### ref in the covering commit
    subject, which T-0541/T-0542's commits omitted; scoping directly here instead
    of amending pushed-adjacent history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: T-0108 cross-ticket exemption needs a T-#### ref in the covering commit
    subject, which T-0541/T-0542's commits omitted; scoping directly here instead
    of amending pushed-adjacent history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: T-0108 cross-ticket exemption needs a T-#### ref in the covering commit
    subject, which T-0541/T-0542's commits omitted; scoping directly here instead
    of amending pushed-adjacent history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: frob.lock
  reason: T-0108 cross-ticket exemption needs a T-#### ref in the covering commit
    subject, which T-0541/T-0542's commits omitted; scoping directly here instead
    of amending pushed-adjacent history
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: T-0108 cross-ticket exemption needs a T-#### ref in the covering commit
    subject, which T-0541/T-0542's commits omitted; scoping directly here instead
    of amending pushed-adjacent history
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestInvariantGate::test_inv001_collected_but_unbound_evidence_warns_inv005
- tests/test_gates.py::TestInvariantGate::test_inv001_passes_via_explicit_tests_edge_to_anchor
- tests/test_gates.py::TestInvariantGate::test_inv001_passes_with_collected_evidence
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B12. invariant_gate accepts any evidence-list item that resolves to a collected test node id or a loaded policy rule id -- nothing checks the named test actually asserts the invariant. Same existence-not-proof pattern as TEST001/COV003. Fix direction: same remedy family as B1 -- require the evidence test to reach/assert against the invariant's anchored symbol (reuse whatever covers_scope-style binding T-0398/T-0415 built for ticket evidence), not just collect.