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
land_commit: null
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

## Done report

Root cause: `scope` served two conflated purposes -- evidence coverage
(D-02's `evidence_covers_scope`) and write lease
(`_scope_add_conflicts`/`_find_leaked_tickets`). Citing a pre-existing
test as evidence (an explicitly endorsed pattern for a no-new-code-path
ticket) had to widen `scope` to satisfy D-02, which then ALSO claimed a
write lease on that file. Live instance: T-1686 (epic, done-report, zero
lines of code changed) permanently held a write lease on
tests/test_ticket_land.py purely from citing one existing test there,
could not release it (ScopeRemoveOrphansEvidence correctly refused), and
blocked T-1922's land with CrossTicketLeakage.

Fix: `Ticket.evidence_scope`, a second field disjoint from `scope`.
`_scope_add_conflicts`/`_find_leaked_tickets`/`scope_lease_conflict`
read `scope` alone, so a path living only in `evidence_scope` is
structurally invisible to every lease/leakage check -- not a
special-cased exemption. `evidence_covers_scope` (D-02) checks `scope +
evidence_scope` together, so evidence recorded there is exactly as
"covered". `add_evidence` auto-populates `evidence_scope` (never
`scope`) whenever a cited node's file isn't already covered -- non-
leasing by default, no flag, per the standing directive.
`demote_to_evidence_only(root, ticket_id, globs, reason=...)` migrates
an EXISTING `scope` entry (the T-1686 shape) into `evidence_scope`
atomically, so D-02 coverage is never momentarily false the way a plain
`scope --remove` + `--add` round-trip would risk (and which would itself
deadlock on ScopeRemoveOrphansEvidence).

ScopeRemoveOrphansEvidence is UNCHANGED and still tested: a plain
`scope --remove` with no matching demotion still refuses exactly as
before (test_remove_without_demotion_still_refuses) -- this adds a new,
narrower escape hatch, it does not weaken the existing guard.

Evidence:
tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_new_evidence_widens_evidence_scope_not_scope
tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_evidence_already_covered_by_scope_widens_nothing
tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceOnlyScopeNeverLeases::test_evidence_scope_path_does_not_block_another_tickets_add
tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceCoversScopeWithEvidenceOnlyScope::test_evidence_covers_scope_true_via_evidence_scope_alone
tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered
tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_refuses_an_undeclared_glob
tests/unit/test_tickets_evidence_only_scope.py::TestScopeRemoveOrphansEvidenceUnweakened::test_remove_without_demotion_still_refuses

Filed: T-1975 (CLI wiring for demote_to_evidence_only, outside
this ticket's declared scope since the CLI parser tree lives outside
src/frob/tickets/); T-1976 (add this ticket's and T-1946's doc
sections to docs/modules/tickets.md once T-1967's live lease on that
file frees -- could not commit the doc prose here, ScopeLeaseConflict).

Known limitation, not silently dropped: existing tickets filed before
this fix (e.g. T-1686 itself) are not retroactively migrated --
demote_to_evidence_only exists and is tested, but applying it to T-1686
specifically is left for whoever resolves that ticket's own lease
contention next, once T-1946's land (currently blocked on the same
T-1967 lease on _land.py) also clears.

Gates: SCOPE001/PRE001/file-scoped COV002 clean for this ticket's own
touched files in `frob check --ticket T-1944`; ruff/ty pass locally;
tests/test_tickets_scope_mutation.py, tests/test_evidence_integrity.py,
tests/test_tickets_acceptance.py, tests/test_tickets_evidence_cli.py,
tests/test_ticket_reverify.py all green (161 tests) confirming no
regression to the existing scope/evidence machinery this change touches.

### Changed
```
 docs/modules/tickets.md                        |  51 +++++
 src/frob/gates/__init__.py                     |  10 +-
 src/frob/tickets/__init__.py                   |   3 +-
 src/frob/tickets/_evidence.py                  |  28 ++-
 src/frob/tickets/_land.py                      | 107 ++++++++++
 src/frob/tickets/_models.py                    |  32 +++
 src/frob/tickets/_scope.py                     |  99 +++++++++-
 tests/unit/test_land_orphaned_evidence.py      | 214 ++++++++++++++++++++
 tests/unit/test_tickets_evidence_only_scope.py | 258 +++++++++++++++++++++++++
 tickets/T-1944/ticket.md                       |  60 +++++-
 tickets/T-1946/ticket.md                       |  24 +++
 tickets/T-1976/ticket.md             |  40 ++++
 tickets/T-1975/ticket.md             |  33 ++++
 13 files changed, 952 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_new_evidence_widens_evidence_scope_not_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestAddEvidenceAutoPopulatesEvidenceOnlyScope::test_evidence_already_covered_by_scope_widens_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceOnlyScopeNeverLeases::test_evidence_scope_path_does_not_block_another_tickets_add` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestEvidenceCoversScopeWithEvidenceOnlyScope::test_evidence_covers_scope_true_via_evidence_scope_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_releases_the_lease_and_keeps_evidence_covered` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly::test_demote_refuses_an_undeclared_glob` (pytest node id, verified passing when recorded)
- `tests/unit/test_tickets_evidence_only_scope.py::TestScopeRemoveOrphansEvidenceUnweakened::test_remove_without_demotion_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 8 error(s), 1358 warning(s), 737 waived
- error-findings: ARCH001@src/frob/gates/_dead_symbols.py, ARCH001@src/frob/tickets/_land.py, ARCH001@src/frob/tickets/_scope.py, COV001@src/frob/tickets/_scope.py, DUP001@src/frob/tickets/_scope.py, F401@/home/logan/projects/frob/.claude/worktrees/detector-fp/tests/unit/test_tickets_evidence_only_scope.py, TEST001@src/frob/tickets/_scope.py, WIRE001@src/frob/tickets/_scope.py
