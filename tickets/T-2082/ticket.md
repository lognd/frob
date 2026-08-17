---
id: T-2082
title: PassengerTickets false-refuses every refactor that relocates a pre-existing
  frob:ticket directive, training agents to reflex --allow-cross-ticket
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
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
  reason: T-2082 regression tests for the discriminator fix
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/tickets.md
  reason: T-2082 fix changes the passenger-ticket-disclosure section's own documented
    behavior; T-2078's lease freed after its land
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported
designated_repro_test: tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse
acceptance:
- text: given a branch that only RELOCATES an existing frob:ticket directive to a
    new line in the same file (net occurrence delta zero), when frob ticket land runs,
    then it does NOT refuse with PassengerTickets and no --allow-cross-ticket is needed
    -- this test MUST fail against current main
  evidence:
  - tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse
- text: given a branch that genuinely ADDS a new frob:ticket directive naming another
    ticket (the T-1618 incident shape, passenger code physically present), when frob
    ticket land runs, then it still refuses with PassengerTickets and names that id
    -- proving the guard is not weakened
  evidence:
  - tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse
  - tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id
- text: given the passenger ticket record reads DONE or DROPPED, when its code is
    genuinely added by the landing branch, then the refusal still fires -- the ledger-state-blind
    property of the check is preserved
  evidence:
  - tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id
  - tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
## Measured evidence: two independent agents, same false refusal, same hour

Both were pure ARCH001 refactor splits that extracted helper functions and
carried the ORIGINAL function's pre-existing `frob:ticket` attribution
comments to the new call sites. Neither added a single line of the named
tickets' code.

1. **T-2073** (`_query.py`, splitting `_doable`): refused with
   `PassengerTickets` naming FOUR ids -- T-0715, T-0752, T-0972, T-2006 --
   all pre-existing directive comments relocated onto the new split-out
   helpers. The agent verified with `git diff main...HEAD --stat` that the
   whole changeset was only `_query.py` plus T-2073's own ticket files, then
   landed with `--allow-cross-ticket`.

2. **T-2077** (`_rapid_sweep.py`, splitting `_file_regression_ticket` and
   `run_deferred_post_land_sweep`): refused with `PassengerTickets` because
   the extracted `_resolve_regression_attribution` carries a pre-existing
   `# frob:ticket T-2009` comment. Agent's words: "documentation only, not
   new T-2009 code -- confirmed via `git diff main...HEAD --stat` showing
   only my own files". Landed with `--allow-cross-ticket`.

## Root cause, read from the source (not inferred)

`_directive_ticket_ids_in_diff` (`src/frob/tickets/_land.py`) collects ids
from ADDED lines only:

    for line in diffed.danger_ok.stdout.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        found.update(_DIRECTIVE_TICKET_ID_RE.findall(line))

Its docstring is explicit that this is deliberate: "`frob:ticket <id>`
directive ADDED (`+`-prefixed source line, never a context/removed line)".

Nothing in the scan asks whether the SAME directive was removed elsewhere in
the same diff. A refactor that relocates a function emits
`+ # frob:ticket T-2009` at the new site and `- # frob:ticket T-2009` at the
old -- a net change of ZERO occurrences -- and the guard counts the addition
and refuses.

## Why this costs more than the two retries

It trains agents to reach for `--allow-cross-ticket` as routine. That flag is
a genuine safety override, and this repo has already paid for it twice: the
2026-08-05 incident where landing T-1581 out of a shared worktree carried
T-1579's WAIVE004 change onto main and deleted 55 live `frob:waive`
directives across five gate families; and the passenger-land-order trap,
where carrying a sibling's FIX to main first strands that sibling in BUG002
permanently because its repro can no longer fail at its parent. A guard that
cries wolf on ordinary refactors is a guard whose override becomes reflex.
The repo is currently doing many ARCH001 splits, so the false-positive rate
is rising, not incidental.

## THE DISCRIMINATOR

Compare each id's OCCURRENCE COUNT at `base_ref` versus `HEAD`. Only ids
whose count INCREASED are genuine passengers. A pure move nets zero.

This does NOT weaken the T-1618 guard, and that must be verified rather than
asserted: in the 55-waiver incident the passenger's code was physically ADDED
to the landing branch, so its directive count strictly increased and a
count-based check still refuses. Add a regression test that reproduces that
incident's shape and confirm it still refuses after the change.

## DO NOT FIX IT THIS WAY

- **Do not exempt ids that merely already exist somewhere at `base_ref`.**
  That is the tempting one-line version and it is unsound: a genuine
  passenger usually names a ticket that already has directives elsewhere in
  the tree. Existence at base is not the question; the DELTA is.
- **Do not consult the passenger ticket's ledger state.** The docstring is
  emphatic that ignoring ledger state is the point, not an oversight -- the
  T-1618 incident is exactly a sibling whose ledger said DONE/DROPPED while
  its code rode along. Do not re-introduce that exemption.
- **Do not widen `--allow-cross-ticket` or add a second override flag.** The
  two existing checks deliberately share ONE flag so a caller has only one
  concept to learn. Another override makes the reflex worse.
- **Do not switch to `--name-only`.** The check needs hunk CONTENT; a
  `frob:ticket` directive is a source line, not a path.
- **Do not silence the refusal into a warning.** Its loudness is what made
  both agents stop and verify. Keep it loud; make it CORRECT.

## A case to decide explicitly, not by accident

A passenger that MOVES existing code and also MODIFIES it nets zero
occurrences while genuinely changing behaviour. Decide whether a
count-unchanged id must also require that the removed and added directive
lines correspond to a pure relocation, and say which you chose and why. Err
toward refusing when ambiguous: a false refusal costs one flag, a false pass
costs an incident.

## Done report

Changed:
- src/frob/tickets/_land.py::_directive_ticket_ids_in_diff -- discriminator now compares each frob:ticket id's added vs removed line occurrence count (T-2082)
- src/frob/tickets/_land.py::_passenger_ids_from_line_buckets (new) -- the count/verbatim-line discriminator, split out to keep the caller under ARCH001's 60-line threshold
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_pure_relocation_of_a_preexisting_directive_does_not_refuse (new, designated repro)
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_relocation_that_also_edits_the_directive_line_still_refuses (new)
- docs/modules/tickets.md#passenger-ticket-disclosure-t-1618 -- updated to describe the count-delta discriminator

Evidence:
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse (acceptance 0, designated repro -- FAILED_AT_PARENT confirmed at 8056fcf92 via `frob ticket evidence --check-repro --base-ref 8056fcf92`)
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id (acceptance 1 -- proves the guard is not weakened for genuinely added passenger code, the WAIVE004-incident shape)
- tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported (acceptance 2 -- proves ledger-state blindness is preserved)
- Full TestPassengerTickets class (6/6) passing: `uv run pytest tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets -q`
- `uv run frob check --only test --only archgate --only sys --ticket T-2082` clean (0 errors)
- `uv run frob check --only doclink --only docanchor --only fmt --only affect_drift --only prework --only scope --ticket T-2082` clean (0 errors)
- `uv run frob check --land-parity`: 1 remaining unscoped error, PII012 on src/frob/testing/_coverage_refresh.py -- pre-existing, file never touched by this ticket's diff (confirmed via `git log -- src/frob/testing/_coverage_refresh.py`), out of scope

Decision recorded (per ticket's explicit ask): a count-unchanged id is exempted ONLY when the exact multiset of added directive lines equals the exact multiset of removed directive lines (verbatim text). A relocation that also edits the directive line in the same motion keeps the same count but fails this stricter check and still refuses -- erring toward refusing when ambiguous, per the ticket's own instruction.

Filed: none (the one out-of-scope PII012 finding is pre-existing repo-wide debt, not new residue from this change)

Cut disclosed: docs/modules/tickets.md could not be added to scope until mid-ticket because T-2078 held a live lease on it; work was blocked on it exactly as the playbook instructs (did not work around it) until T-2078's land completed, then scope was widened and the doc updated in the same change as planned.

Gates: frob check clean across test/archgate/sys/doclink/docanchor/fmt/affect_drift/prework/scope for T-2082's scope. frob check --land-parity shows only the pre-existing, out-of-scope PII012 finding.

### Changed
```
 docs/modules/tickets.md                      | 64 +++++++++++-------
 src/frob/tickets/_land.py                    | 97 +++++++++++++++++++++-------
 tests/unit/test_land_cross_ticket_leakage.py | 84 ++++++++++++++++++++++++
 tickets/T-2082/ticket.md                     | 33 ++++++++--
 4 files changed, 224 insertions(+), 54 deletions(-)
```

### Evidence
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_pure_relocation_of_a_preexisting_directive_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_refuses_and_lists_every_passenger_by_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets::test_a_dropped_siblings_still_present_code_is_still_reported` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2082
