---
id: T-1675
title: already-landed detection is opt-in because it cannot tell 'no diff' from 'docs-only
  ticket'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_already_landed.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: positive on-main detection replaces the empty-diff inference; flag removed
    end to end per the ticket's own ask
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: positive on-main detection replaces the empty-diff inference; flag removed
    end to end per the ticket's own ask
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/config.py
  reason: positive on-main detection replaces the empty-diff inference; flag removed
    end to end per the ticket's own ask
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/_config_external.py
  reason: positive on-main detection replaces the empty-diff inference; flag removed
    end to end per the ticket's own ask
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: positive on-main detection replaces the empty-diff inference; flag removed
    end to end per the ticket's own ask
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_land_already_landed.py
  reason: positive on-main detection replaces the empty-diff inference; flag removed
    end to end per the ticket's own ask
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/tickets.md
  reason: positive on-main detection replaces the empty-diff inference; flag removed
    end to end per the ticket's own ask
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_has_real_changes_in_its_own_scope
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_when_the_ticket_declares_no_scope_at_all
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_no_op_for_a_docs_only_ticket_whose_scope_diff_is_empty_but_not_yet_landed
designated_repro_test: null
threat: null
component: null
---
T-1618 added _check_already_landed, which reads an empty ticket-scope diff as LandError.AlreadyLandedOnMain. It shipped behind an opt-in flag (--check-already-landed) because wiring it on by default regressed 20 tests in tests/test_ticket_land.py: an empty scope-diff is ALSO the ordinary shape of a docs-only or ledger-only ticket in this repo's own fixtures.

The opt-in is an honest response to a check that cannot currently distinguish two different states from the same signal, and it is the right call for landing T-1618. But it leaves the check off for every real land, which is where it would have value -- so the defect it detects still reaches main.

The signal is the problem, not the default. 'Scope diff is empty' is being asked to answer 'was this already landed?', and it cannot: absence of a diff is equally consistent with 'the work is already on main', 'this ticket's work is entirely outside its declared scope globs', and 'this ticket legitimately changed only docs or the ledger'. That is the R1 shape -- absence read as a negative -- and the T-1662 rule that a check must decide from semantics rather than a proxy signal.

Work: distinguish the states positively rather than inferring from emptiness. 'Already landed' should be established by finding the ticket's actual content ON main (its commit, its directive edges, its evidence resolving there), not by finding nothing on the branch. Once the check answers the question it claims to answer, turn it on by default and drop the flag.

Filed by the coordinator while reviewing T-1618 before landing it.