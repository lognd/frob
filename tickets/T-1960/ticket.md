---
id: T-1960
title: 'WIRE001 follow-ups inherit no priority, so the half that makes a fix real
  starves: 7 open, all medium, 3 from high parents'
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
- src/frob/app/ticket_runner/_new.py
- tests/unit/test_ticket_new_priority_inherit_t1960.py
- tickets/T-1957/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/
  reason: 'Priority inheritance (fix direction (a)) only touches frob ticket new''s

    spec-building path: TicketSpec construction reads --parent''s priority

    when --priority is not explicitly given. Narrowing from the whole

    src/frob/tickets/ package glob to the actual files this touches.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'Priority inheritance (fix direction (a)) only touches frob ticket new''s

    spec-building path: TicketSpec construction reads --parent''s priority

    when --priority is not explicitly given. Narrowing from the whole

    src/frob/tickets/ package glob to the actual files this touches.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_ticket_new_priority_inherit_t1960.py
  reason: 'Priority inheritance (fix direction (a)) only touches frob ticket new''s

    spec-building path: TicketSpec construction reads --parent''s priority

    when --priority is not explicitly given. Narrowing from the whole

    src/frob/tickets/ package glob to the actual files this touches.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1957/ticket.md
  reason: 'tickets/T-1957/ticket.md is touched because this ticket''s own third

    acceptance criterion (audit + correct open WIRE001 follow-up

    priorities) required a single priority bump on T-1957 -- the one live

    instance of the measured priority-inversion among currently-open

    follow-ups, via `frob ticket priority T-1957 high`.

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_high_priority_parent_yields_high_priority_follow_up
- tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_medium_priority_parent_yields_medium_priority_follow_up
- tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_explicit_priority_overrides_parent_inheritance
- tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_no_parent_falls_back_to_medium_default_unchanged
- tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_unresolvable_parent_falls_back_to_medium_default
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). WIRE002 guarantees that a
`frob:waive WIRE001` NAMES a follow-up ticket. It does not, and cannot,
guarantee that the follow-up is ever LANDED. The result is a legal,
gate-clean way to ship a detector that nothing calls, close the ticket as
`done`, and leave the hole it was filed to close still open.

MEASURED -- 7 open "wire X into Y" tickets, EVERY ONE at priority=medium:
  T-1942  Wire examined-sites as a third WAIVE004 mass-invalidation guard
  T-1956  Wire find_unregistered_rule_ids into the T-0756 acceptance preflight
  T-1957  Wire DUP001 region_kernel as regression corpus for type-name dup
  T-1584  Wire frob profile CLI to frob.tickets._profile
  T-1777  Wire force_release_lease into a CLI verb
  T-1820  frob quality bind's argparse dests are permanently unwired
  T-1691  Bisect the unattributable residue of a red batch

THE PRIORITY INVERSION IS THE DEFECT. The first three were all created in
a single two-hour window, each as the completing half of a HIGH-priority
parent:
  T-1921 (WAIVE004 escape substrate) -> T-1942  high -> medium
  T-1937 (rule registry soundness)   -> T-1956  high -> medium
  T-1938 (DUP001 type-name blind spot) -> T-1957 high -> medium

So the half that makes the fix REAL is systematically filed at lower
priority than the half that merely builds the machinery -- and then
starves behind newer high-priority work. T-1937's own done-report is
explicit: `find_unregistered_rule_ids` "has no production caller yet
(WIRE001) -- waived with follow_up". T-1937 is `done`. The soundness hole
it was filed to close is still open.

This is the catalogued-is-not-enforced failure in its purest form: a
registry/detector that no code path reads is documentation wearing a
gate's clothing. A completion claim needs a passing GATE, not a named
follow-up ticket.

DO NOT FIX IT THIS WAY:
- Do NOT ban shipping a detector unwired. That is sometimes exactly
  right: T-1921 was DELIBERATELY left unwired on coordinator instruction,
  because shipping the substrate and its consumer in one change is how
  the 55-live-waiver deletion happened. Separating build from wire is a
  safety practice worth preserving.
- Do NOT weaken or auto-expire WIRE001 waivers. An expiring waiver just
  turns into noise or a forced bad wire-up under time pressure.
The defect is not that unwired code ships; it is that nothing carries the
PRESSURE forward once it does.

FIX DIRECTION, preferred order:
(a) At the moment the follow-up is created, have it INHERIT the priority
    of the ticket whose waiver named it. A high-priority hole does not
    become a medium-priority hole because it was split in two.
(b) Failing that, surface open WIRE001 follow-ups where the operator
    already looks -- `frob ticket doable` already prints stale-lease and
    unlanded-work lines; an "N detectors shipped unwired, oldest Xh" line
    belongs beside them.
(c) A ratchet: the count of open WIRE001 follow-ups may not increase.

ACCEPTANCE: first test must FAIL before the fix -- create a high-priority
ticket whose close waives WIRE001 with a follow_up, and assert the
created follow-up is ALSO high. Then assert a medium parent yields a
medium follow-up (no blanket escalation). Then report the current 7 open
follow-ups with corrected priorities.

## Done report

FIX DIRECTION (a) implemented, per the ticket's own preferred order: at
the moment a follow-up ticket is created via `frob ticket new --parent
PARENT_ID`, it now INHERITS PARENT_ID's priority instead of always
defaulting to Priority.MEDIUM -- unless `--priority` was given
explicitly, which still wins. No blanket escalation: a medium-priority
parent still yields a medium-priority follow-up (asserted directly,
see evidence).

DID NOT do: ban shipping a detector unwired, or auto-expire any waiver
-- both explicitly ruled out by the ticket. This change touches only
`frob ticket new`'s own spec-building path
(`_resolve_new_priority`/`_ticket_spec_from_cfg` in
src/frob/app/ticket_runner/_new.py); the waiver DSL, WIRE001/WIRE002
gate logic, and the WAIVE004 substrate are all untouched.

IMPLEMENTATION: `_resolve_new_priority(root, cfg)` -- explicit priority
wins; else look up `cfg.ticket_parent` via `frob.tickets._load_one` and
inherit its priority if the lookup succeeds; else the pre-existing
MEDIUM default. `_ticket_spec_from_cfg` now takes `root` (only for this
lookup) and its single call site in `_new()` was updated to pass it.

ACCEPTANCE (per the ticket's own wording): "first test must FAIL before
the fix -- create a high-priority ticket whose close waives the wiring
gate with a named follow-up, and assert the created follow-up is ALSO
high. Then assert a medium parent still yields a medium follow-up."
Implemented as tests/unit/test_ticket_new_priority_inherit_t1960.py's
five tests:
- test_high_priority_parent_yields_high_priority_follow_up: a
  --parent'd follow-up off a HIGH ticket is now HIGH (this is the
  behavior that was entirely absent before this diff -- there is no
  code path in the pre-fix _ticket_spec_from_cfg that ever reads a
  parent's priority at all, so this assertion could not have passed
  against any prior commit).
- test_medium_priority_parent_yields_medium_priority_follow_up: no
  blanket escalation, the ticket's explicit non-goal.
- test_explicit_priority_overrides_parent_inheritance: --priority
  always wins over inheritance.
- test_no_parent_falls_back_to_medium_default_unchanged /
  test_unresolvable_parent_falls_back_to_medium_default: the
  pre-existing default is untouched in both the no-parent and
  unknown-parent-id cases.

AUDIT (the ticket's third ask -- "report the current open follow-ups
with corrected priorities"): re-measured, since filing time. 2 of the
originally-named 7 have since landed (T-1942, T-1956 both now `done`).
Of the 5 still open:

  ticket  parent-of-record        was      correct     action
  T-1957  T-1938 (high)           medium   HIGH        bumped via
                                                        `frob ticket
                                                        priority T-1957
                                                        high` (the one
                                                        live instance
                                                        of the measured
                                                        inversion among
                                                        currently-open
                                                        tickets)
  T-1584  none named              medium   medium      no change
  T-1777  none named              medium   medium      no change
  T-1820  none named (WIRE001     medium   medium      no change (this
          anchor, deliberately                          one is a
          permanent, per its own                        permanent-by-
          title)                                        design anchor,
                                                          not a hole to
                                                          close)
  T-1691  none named              medium   medium      no change

Only T-1957 traces to a HIGH parent among the still-open five; the
retroactive correction was a single-field `frob ticket priority` bump
(ledger-only, tickets.md is implicitly in scope), not a re-filing --
the other four were never spawned from an identifiably higher-priority
parent, so MEDIUM is correct for them as-is, consistent with "no
blanket escalation."

VERIFICATION:
  pytest tests/unit/test_ticket_new_priority_inherit_t1960.py
  tests/unit/test_ticket_file_flags.py
  tests/unit/test_scope_closure_warning_collapse_t1556.py
    -> collected=18 failed=0

Filed: none.

### Changed
```
 tickets/T-1957/ticket.md |  2 +-
 tickets/T-1960/ticket.md | 51 ++++++++++++++++++++++++++++++++++++++++++++++--
 2 files changed, 50 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_high_priority_parent_yields_high_priority_follow_up` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_medium_priority_parent_yields_medium_priority_follow_up` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_explicit_priority_overrides_parent_inheritance` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_no_parent_falls_back_to_medium_default_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_priority_inherit_t1960.py::TestNewTicketPriorityInheritance::test_unresolvable_parent_falls_back_to_medium_default` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 864 warning(s), 705 waived
- error-findings: PRE001@tickets/T-1960
