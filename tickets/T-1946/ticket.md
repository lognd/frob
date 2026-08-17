---
id: T-1946
title: 'Deleting or renaming a test silently orphans other tickets'' evidence: nothing
  refuses it, and it is the entire current error floor'
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
- tests/unit/test_land_orphaned_evidence.py
- src/frob/tickets/_land.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_orphaned_evidence.py
  reason: acceptance tests for the land-time orphaned-evidence-deletion guard live
    here
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/tickets.md
  reason: documenting the new land-time orphaned-evidence-deletion guard, same pattern
    as every other land-time check in this file
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/modules/tickets.md
  reason: doc section could not be committed (T-1967's live lease on this file) --
    deferred to follow-up T-1973
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'narrowed to the actual touched files after T-1967''s lease released: the
    new orphaned-evidence-deletion land-time check and its LandError variant

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'narrowed to the actual touched files after T-1967''s lease released: the
    new orphaned-evidence-deletion land-time check and its LandError variant

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/tickets/
  reason: narrowed to the actual touched files now that the lease is free
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly
- tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_rename_that_repoints_evidence_in_same_diff_is_accepted
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPEATED-MISTAKE AUDIT FINDING (2026-08-10). Deleting or renaming a test
silently orphans OTHER tickets' recorded evidence. Nothing refuses it at
the moment of the edit, and nothing catches it before land -- it only
surfaces later as COV003 on a ticket the author never touched.

MEASURED: this is 100% of the current unscoped error floor (4 of 4
errors, `frob check --only gates` at 2d8476ab4):

  COV003 T-0185 <- tests/unit/test_research_assets.py::
                   test_skill_frob_doc_anchor_resolves_in_guide
  COV003 T-1351 <- tests/unit/test_check.py::TestScopeDisclosure::
                   test_full_unfiltered_run_adds_no_disclosure
  COV003 T-1507 <- (same node)
  COV003 T-1512 <- (same node)

TWO INDEPENDENT ACTORS, ONE HOUR, DIFFERENT FILES -- this is a mechanism
failure, not carelessness:
  - commit 72902adc0 (coordinator) deleted the first test while removing
    the project-scope .claude/agents and .claude/skills copies.
  - T-1928's land e68f129b115f (agent) REPLACED the second test with
    `test_full_run_discloses_fmt_scope`, correctly asserting the opposite
    behavior -- a legitimate, well-reasoned change that silently broke
    three unrelated tickets.

Neither actor could have seen it: the orphaned tickets were outside both
scopes, and the deleting diff gives no signal. One deletion took out
THREE tickets at once, so blast radius is superlinear in how well-cited a
test is.

THE RULE ALREADY EXISTS AND DID NOT WORK. This exact hazard is recorded
(refactor invalidates out-of-scope edges; re-measure unscoped before
accepting a refactor land). It was written down and still happened twice
in an hour, to two different actors. Per the standing audit rule: when a
recorded rule is not followed, the rule is not the fix -- find what
enforces it.

FIX DIRECTION, preferred order:
(a) REFUSE AT THE MOMENT. A diff that deletes or renames a test node id
    bound as evidence on ANY ticket is statically detectable: the set of
    recorded evidence node ids is already in the ledger, and the set of
    removed node ids is derivable from the diff. Refuse the land, naming
    every orphaned ticket, and require either an evidence re-point or an
    explicit acknowledgement.
(b) Failing that, a pre-land gate that reports the orphan set.

DO NOT FIX IT THIS WAY: do not make COV003 lenient, and do not
auto-delete or auto-rewrite the orphaned evidence to make the gate go
quiet. The evidence binding is the only record that a ticket was ever
proven; silently repointing it fabricates proof. This is the WAIVE004
failure mode (a "safe" cleanup that deleted 55 live waivers) applied to
evidence. The correct outcome is a human/agent decision per orphan --
re-point to the replacement test, or re-scope the ticket and record fresh
evidence.

ACCEPTANCE: first test must FAIL before the fix -- construct a diff that
deletes a test node bound as evidence on an unrelated ticket, assert the
land is refused and the orphaned ticket id appears in the message. Then
assert a deletion of an UNBOUND test still lands cleanly (no false
refusal), and that a rename which re-points evidence in the same diff is
accepted.

## Done report

Root cause: a branch's own committed diff can delete or rename a pytest
test node ANOTHER ticket cites as evidence, with no signal at the point
of deletion -- two independent actors did this in one hour (a
coordinator's file cleanup, and a legitimate test replacement in an
unrelated ticket's land), each orphaning evidence outside their own
declared scope. One deletion took out three unrelated tickets' evidence
at once (100% of the then-current unscoped error floor, 4 COV003
findings).

Fix: `_check_orphaned_evidence_deletion` (src/frob/tickets/_land.py),
wired into `_land_precheck_remaining_checks` right after the existing
cross-ticket-leakage check. Computes the branch's own three-dot diff
(`_branch_changed_files`, the same primitive T-1922 fixed the two-dot/
three-dot confusion in) and, for every OTHER ticket's non-cmd evidence
id whose file lies in that diff, checks whether it still resolves
against the worktree's currently collected tests
(`_evidence_valid_for_ticket`). A node id that no longer resolves
refuses the land (`LandError.OrphanedEvidenceDeletion`), naming the
affected ticket(s) and evidence id(s). A rename that ALSO re-points the
affected ticket's evidence in the SAME diff is never refused, since the
check reads the ledger's POST-diff state.

Deliberately does not auto-repoint or auto-delete the stale evidence
itself (the WAIVE004 lesson applied to evidence: the binding is the
only record a ticket was ever proven, so repointing it automatically
would fabricate proof) -- only refuses and names what to fix.

Evidence:
tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test (acceptance 1, fail-then-pass proof)
tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly (acceptance 2, no false refusal)
tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_rename_that_repoints_evidence_in_same_diff_is_accepted (acceptance 3)

check-repro: BUG002 --check-repro on the new fresh test returned
NO_VERDICT (collection failure at parent commit -- the test exercises
code that did not exist there yet). Structural, not evasion; recorded
here per the playbook's documented gap for a brand-new test node.

Filed: T-1973 (add this ticket's and T-1944's doc sections to
docs/modules/tickets.md once no live lease blocks it -- could not commit
the doc prose in either ticket's own land window due to a live
cross-ticket lease on that file at the time).

Known limitation: post-mutation re-verification (mirroring T-1932's
second call site for the cross-ticket-leakage guard) is not yet added
for this check -- no Tier-A auto-fix handler in this repo deletes or
renames test files today, so the mutation window that pattern exists to
close is narrower here; documented in the (currently unlandable) doc
section rather than silently assumed safe.

Gates: SCOPE001/PRE001/file-scoped COV002 clean for this ticket's
touched files; 290/291 in the land/leakage regression sweep (the one
failure is a pre-existing environment flake reproducing identically on
an unmodified main checkout, unrelated to this change).

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
 tickets/T-1944/done-report.md                  |  93 +++++++++
 tickets/T-1944/ticket.md                       |  60 +++++-
 tickets/T-1946/ticket.md                       |  50 ++++-
 tickets/T-1973/ticket.md             |  40 ++++
 tickets/T-1975/ticket.md             |  33 ++++
 14 files changed, 1069 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_refuses_when_branch_deletes_evidence_bound_test` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_deletion_of_unbound_test_lands_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence.py::TestOrphanedEvidenceDeletion::test_rename_that_repoints_evidence_in_same_diff_is_accepted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 8 error(s), 1167 warning(s), 737 waived
- error-findings: ARCH001@src/frob/tickets/_land.py, ARCH001@src/frob/tickets/_scope.py, COV001@src/frob/tickets/_scope.py, DUP001@src/frob/tickets/_scope.py, F401@/home/logan/projects/frob/.claude/worktrees/detector-fp/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_scope.py, WIRE001@src/frob/tickets/_scope.py
