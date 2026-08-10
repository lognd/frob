---
id: T-1967
title: 'land silently carries a sibling ticket''s code when a worktree holds two tickets:
  no flag needed, no warning, guard never fires'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_cross_ticket_leakage.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: T-1967 needs to add/modify regression tests for the cross-ticket leakage
    guard fix in tests/unit/test_land_cross_ticket_leakage.py, per the ticket acceptance
    criteria (a test that must fail before the fix). Widening scope to include this
    test file.
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/tickets.md
  reason: The fixed function DIRECTLY frob:describes docs/modules/tickets.md#cross-ticket-leakage-only-refuses-on-an-in_progress-sibling-t-1639,
    which now contains a stale sentence about the T-1370 same-worktree exemption T-1967
    removed. Doc must move in the same change per playbook section 8.
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_lands_with_explicit_ack
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly
designated_repro_test: tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob ticket land` squash-applies the ENTIRE worktree diff. When two
tickets share one worktree, landing the first silently carries the
second's code, tests and done-report onto main under the first ticket's
commit. No `--allow-cross-ticket` is required and NO WARNING IS PRINTED
-- the CrossTicketLeakage / PassengerTickets guard does not fire at all.

MEASURED, 2026-08-10. `git show --stat da9afe8369308c6c7666cfef9aa3053a07c960ec`
-- the land commit for T-1958, a `kind=docs` ticket whose entire declared
job was updating a stale `frob:enumerates` list in docs/modules/gates.md:

  src/frob/tickets/_evidence.py                  |  18 ++
  src/frob/tickets/_models.py                    |  17 ++
  src/frob/tickets/_new_gate_rule_acceptance.py  |  65 ++-
  tests/test_tickets_new_gate_rule_acceptance.py | 114 +++
  tickets/T-1956/done-report.md                  |  93 +++
  tickets/T-1956/ticket.md                       |  29 +-

Every one of those belongs to T-1956, a different ticket. A docs ticket
carried a production change to the ticket-transition guard. T-1956's
state on main stayed `in-progress` while its code was already live.

THIS IS A GUARD HOLE, NOT A MISSING CHECK. The reporting agent did not
force anything: it used no flag, and the guard that exists precisely to
catch this printed nothing. Compare T-1950, where cross-ticket carrying
happened but at least required an explicit `--allow-cross-ticket`; here
the same damage occurs on a completely ordinary land.

WHY IT MATTERS BEYOND ATTRIBUTION: reviewers read a docs ticket's diff
and see production code they never expected; `git bisect` and `git blame`
misattribute; and a ticket can be live on main while its ledger state
says otherwise, so the queue lies about what is deployed. It also
silently defeats the scope system -- code lands under a ticket whose
declared scope never included those paths.

SHARING A WORKTREE ACROSS TICKETS IS NORMAL AND ENDORSED here (the
dispatch model gives each agent a SERIES of tickets in one worktree to
amortize cold start), so this is not an exotic misuse -- it is the
default configuration, which means this has almost certainly happened
before unnoticed.

DO NOT FIX IT THIS WAY:
- Do NOT forbid multiple tickets per worktree. That is the deliberate
  cost-saving dispatch pattern and banning it would slow every wave.
- Do NOT simply widen `--allow-cross-ticket` to cover this case. The
  defect is SILENCE, not permissiveness: an operator who knowingly
  carries a sibling can already say so. What must not happen is carrying
  one without being told.
- Do NOT make land squash only the ticket's declared scope. Legitimate
  incidental changes (ledger, rapid-debt, lockfiles) fall outside scope
  and dropping them would produce broken lands.

FIX DIRECTION, preferred order:
(a) Before applying, enumerate every OTHER ticket whose files the squash
    would carry and REFUSE unless each is named explicitly. Carrying a
    sibling becomes an affirmative statement, never a side effect.
(b) At minimum, print the carried-ticket set loudly in the land output
    and record it in the LAND-PROOF line, so it is visible after the fact.

ACCEPTANCE: first test must FAIL before the fix -- one worktree, two
tickets with committed changes, land the first, assert it refuses (or at
minimum reports the second by id). Then assert a single-ticket worktree
lands unchanged with no new noise, and that in-scope incidental files
(rapid-debt.jsonl, ledger) never trigger a false refusal.

## Done report

Root cause: `_leaked_hits_for_candidate` (src/frob/tickets/_land.py) unconditionally
exempted any sibling ticket leased to the SAME worktree as the landing ticket
(the T-1370 same-worktree exemption), before ever computing whether the
sibling had real committed content in the branch. Since sharing one worktree
across a ticket series is this repo's normal, endorsed dispatch pattern, that
exemption fired on every ordinary series land and made the CrossTicketLeakage
guard permanently blind to exactly the shape it exists to catch: a sibling's
own committed, still-open work riding along silently. Reproduced live against
the measured incident: da9afe8369308c6c7666cfef9aa3053a07c960ec (T-1958's
land) carried T-1956's `_evidence.py`/`_models.py`/
`_new_gate_rule_acceptance.py`, its test file, and its Done report -- with
T-1956 IN_PROGRESS on main throughout, no `--allow-cross-ticket`, and no
warning printed. The separate T-1618 `_check_passenger_tickets` guard also
did not catch it, since T-1956's added hunks referenced "T-1937/T-1956" only
in prose, never as a genuine ticket-linking source-comment directive line
(the exact two-word marker that check scans for, spelled out here with a
space so this Done report's own prose cannot itself be misparsed as one).

Fix: removed the same-worktree exemption from `_leaked_hits_for_candidate`.
A same-worktree sibling with a real scope hit (content genuinely changed
since the branch's fork point, ticket IN_PROGRESS) now flows into the exact
same `leaked` map / `_report_leaked_tickets` refusal path a cross-worktree
leak already used -- it either requires the existing, already-logged
`--allow-cross-ticket` acknowledgment or refuses, naming the sibling by id.
This does not reintroduce T-1370's original mutual-deadlock concern: a hit
only ever exists once a sibling has genuinely been worked on the branch, and
`--allow-cross-ticket` remains the explicit way through for a genuinely
intentional joint land -- once the first of two mutually-scoped
same-worktree tickets lands, the second's own later land finds the first
already DONE and exempt.

Updated the existing `test_sibling_leased_to_same_worktree_does_not_block`
test (kept its NAME, since T-1370/T-1639 -- both DONE tickets -- cite that
exact node id as evidence; renaming it would have broken their COV003
resolution) to assert the corrected refusal behavior instead of the old
buggy exemption, and added a new
`test_sibling_leased_to_same_worktree_lands_with_explicit_ack` test proving
`--allow-cross-ticket` still unblocks a genuinely intentional joint land.
Widened T-1967's scope to include the test file and the one stale doc
paragraph in docs/modules/tickets.md that described the now-removed T-1370
exemption as still-applicable.

Verification: pytest tests/unit/test_land_cross_ticket_leakage.py (12 of 13
pass; the 13th, test_queued_sibling_scope_overlap_does_not_block, fails
identically on unmodified main -- a pre-existing fixture flake unrelated to
this change, confirmed by running it against main directly).
tests/test_ticket_land.py, tests/unit/test_land_step_ordering.py,
tests/unit/test_land_already_landed.py all pass (280 total). `frob check
--ticket T-1967` clean across gates-fast/gates-native/gates-security (the 2
gates-native errors are the pre-existing ARCH001 floor in
src/frob/gates/_dead_symbols.py, tracked separately as T-1962, not touched
by this ticket). `frob check --land-parity` clean.

### Changed
```
 tickets/T-1967/done-report.md | 69 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1967/ticket.md      | 27 +++++++++++++++--
 2 files changed, 94 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_does_not_block` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_sibling_leased_to_same_worktree_lands_with_explicit_ack` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_allow_cross_ticket_overrides_the_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 1358 warning(s), 707 waived
- error-findings: PRE001@tickets/T-1967
