---
id: T-1950
title: 'A ticket can land verified=True with an empty commit while a sibling carries
  its code: land proof checks ancestry, not content'
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
- src/frob/tickets/_land.py
- tests/unit/test_land_already_landed.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/
  reason: T-1950 fix direction (a) touches _land.py only (a new content-verification
    preflight before commit); T-1950 own acceptance tests will live in tests/unit
    or tests/test_ticket_land.py, added within scope narrowing as needed once identified.
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_land.py
  reason: T-1950 fix direction (a) touches _land.py only (a new content-verification
    preflight before commit); T-1950 own acceptance tests will live in tests/unit
    or tests/test_ticket_land.py, added within scope narrowing as needed once identified.
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_land_already_landed.py
  reason: T-1950 needs new regression tests in tests/unit/test_land_already_landed.py
    per the ticket acceptance criteria.
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/tickets.md
  reason: The fixed function frob:describes docs/modules/tickets.md#already-landed-on-main-first-class-outcome-t-1618,
    which needs a T-1950 addendum documenting the new second positive signal.
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_when_a_sibling_carried_this_tickets_content_before_it_ever_landed
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_no_frob_ticket_directive_for_this_id_exists_on_main
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_has_real_changes_in_its_own_scope
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_for_a_docs_only_ticket_whose_scope_diff_is_empty_but_not_yet_landed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
A ticket can land with LAND-PROOF verified=True, pass an independent
scripts/verify_lands.py check, and reach state=done -- while its own land
commit contains NONE of the code it claims to have implemented.

MEASURED, 2026-08-10, both commits on main:

  T-1922 land b508b0ad3eec carried, in ONE commit:
     src/frob/app/ticket_runner/_land_cmd.py     +90   <- T-1720's feature
     tests/unit/test_land_auto_rebase.py        +131   <- T-1720's tests
     tickets/T-1720/done-report.md              +117   <- T-1720's report
     src/frob/tickets/_land.py                   +92   <- T-1922's own fix
     tests/test_ticket_land.py                   +91   <- T-1922's own tests

  T-1720 land 48f49d78b8db then contained ONLY:
     rapid-debt.jsonl                             +2
     tickets/T-1720/ticket.md                      1 changed line

`git log -S_auto_rebase_worktree_onto_main` confirms the symbol entered
main under b508b0ad3 (T-1922), not under T-1720's own commit.

BOTH LANDS REPORTED verified=True AND BOTH PASS verify_lands.py (ON HEAD,
exit 0). Nothing in the pipeline noticed. No work was lost -- the code and
tests are on main and pass (tests/unit/test_land_auto_rebase.py: 2 passed)
-- so this is an ATTRIBUTION and VERIFICATION defect, not data loss.

WHY IT MATTERS: verify_lands.py answers "is this commit an ancestor of
main, and is the ticket done" -- it does NOT answer "does this commit
contain the change the ticket claims". Those are different questions, and
the whole land-verification discipline in this repo has been treating the
first as proof of the second. Consequences: git blame and bisect
misattribute the feature to an unrelated bugfix; a reviewer reading
T-1720's commit sees an empty change; and a genuinely empty land (work
silently dropped) is indistinguishable from this case.

HOW IT AROSE (both `--allow-cross-ticket`, coordinator-authorized): the
agent had committed BOTH fixes in one worktree before landing either. The
coordinator verified the flag was safe with respect to the ticket holding
the contested LEASE (T-1686 -- additive-only diff, no unlanded code) but
did NOT check what else in the worktree the flag would sweep along. The
safety analysis was scoped to the lease holder rather than to the whole
carried changeset. That is the reusable lesson.

FIX DIRECTION, preferred order:
(a) At land, verify the commit actually contains a change to at least one
    path in the ticket's declared scope (excluding ledger/rapid-debt
    bookkeeping), and REFUSE with a clear message if not.
(b) Have --allow-cross-ticket enumerate every foreign ticket whose files
    it is about to carry, and require they be named explicitly -- so
    "carries T-1720" is an affirmative statement, not a side effect.
(c) Extend verify_lands.py to report the ticket's scope-touching file
    count so an empty land is visible after the fact.

DO NOT FIX IT THIS WAY: do not make this a warning only. A warning at
land time is read by an agent that has already decided to land, and this
session has repeatedly shown warnings are not enough (four agents were
warned about the confirmatory-evidence trap and all four fell in). Also
do not weaken or remove --allow-cross-ticket -- it has legitimate uses,
including the one that produced this; the defect is that it is silent
about what it carries, not that it exists.

ACCEPTANCE: first test must FAIL before the fix -- construct a land whose
commit touches no path in the ticket's scope and assert it is refused,
naming the ticket. Then assert a normal land still passes, and that a
docs-only ticket whose scope IS docs/ is not falsely refused.