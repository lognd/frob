---
id: T-1944
title: 'Scope conflates evidence coverage with write lease: citing an existing test
  permanently leases its whole file'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_scope.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/__init__.py
- src/frob/gates/__init__.py
- tests/unit/test_tickets_evidence_only_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/
  reason: 'narrowed to the actual touched files: the new evidence_scope field, D-02
    update, add_evidence auto-population, demote_to_evidence_only, and its tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'narrowed to the actual touched files: the new evidence_scope field, D-02
    update, add_evidence auto-population, demote_to_evidence_only, and its tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_scope.py
  reason: 'narrowed to the actual touched files: the new evidence_scope field, D-02
    update, add_evidence auto-population, demote_to_evidence_only, and its tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'narrowed to the actual touched files: the new evidence_scope field, D-02
    update, add_evidence auto-population, demote_to_evidence_only, and its tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'narrowed to the actual touched files: the new evidence_scope field, D-02
    update, add_evidence auto-population, demote_to_evidence_only, and its tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'narrowed to the actual touched files: the new evidence_scope field, D-02
    update, add_evidence auto-population, demote_to_evidence_only, and its tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_tickets_evidence_only_scope.py
  reason: 'narrowed to the actual touched files: the new evidence_scope field, D-02
    update, add_evidence auto-population, demote_to_evidence_only, and its tests'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_new_evidence_widens_evidence_scope_not_scope
- tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_evidence_already_covered_by_scope_widens_nothing
- tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceOnlyScopeNeverLeases::test_evidence_scope_path_does_not_block_another_tickets_add
- tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceCoversScopeWithEvidenceOnlyScope::test_evidence_covers_scope_true_via_evidence_scope_alone
- tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered
- tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_refuses_an_undeclared_glob
- tests/unit/test_tickets_evidence_only_scope.py::TestScopeRemoveOrphansEvidenceUnweakened::test_remove_without_demotion_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
STRUCTURAL FINDING, discovered blocking a real land (2026-08-10).

Scope serves two different purposes that are wrongly conflated:
  1. EVIDENCE COVERAGE -- "this ticket's recorded evidence lives here"
  2. WRITE LEASE -- "no other ticket may modify these paths"

Because they are one field, citing a PRE-EXISTING test as evidence
permanently claims a write lease on the entire file containing it.

LIVE INSTANCE: T-1686 (tier=epic, done-report on main, Changed set =
ticket.md files ONLY, zero lines of code modified) cites one existing
test in tests/test_ticket_land.py as evidence. It therefore holds a
write lease on the repo's highest-traffic land test file, from
worktree=/home/logan/projects/frob branch=main -- the ROOT, where no
agent ever works. Recorded 2026-08-08 and still held.

BLAST RADIUS: this refused T-1922's land with CrossTicketLeakage over
pure NEW test methods with no semantic overlap with T-1686's work. The
epic cannot release the lease either: `frob ticket scope --remove`
correctly refuses with ScopeRemoveOrphansEvidence, because dropping the
path would orphan the recorded evidence. So the ticket is trapped --
it must hold a lease it does not use, on a shared file, until it closes,
and it cannot close because two children are still queued.

WHY THIS RECURS: every epic that cites existing tests as evidence (the
playbook explicitly ENDORSES citing existing tests for a no-new-code-
path change) becomes a long-lived lease on whatever shared files those
tests live in. The more correct the epic's evidence discipline, the
broader the block. That is backwards.

FIX DIRECTION: separate the two meanings. Evidence coverage should be
satisfiable without asserting a write claim -- e.g. an explicit
read-only/evidence-only scope entry, or deriving the lease from the
ticket's actual changed set rather than its whole declared scope. A
ticket that has modified zero lines of a file has no basis for excluding
others from it.

DO NOT fix this by adding a flag the operator must remember to pass on
epics; per the standing directive, a command requires knowledge of the
command. Prefer making evidence-only citation non-leasing by default.

Constraint: do not weaken ScopeRemoveOrphansEvidence itself. It is
correctly preventing orphaned evidence; the defect is upstream, in
scope carrying two meanings.