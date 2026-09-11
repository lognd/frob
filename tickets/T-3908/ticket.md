---
id: T-3908
title: accept --amend and --remove are still 0-based after T-3837 made the display
  and --accepts 1-based, so --remove drops the wrong criterion
state: done
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: 0.531.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_accept.py
- src/frob/tickets/_models.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- tests/test_tickets_acceptance.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_accept.py
  reason: 'T-3908: --amend/--remove index convention fix touches the accept mutation
    family (_accept.py), the error message enum (_models.py), CLI dispatch/help (_mutate.py,
    _metadata.py), its test file, and the one doc section (tickets-data-storage.md)
    documenting the 0-based CLI contract that must move to 1-based'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-3908: --amend/--remove index convention fix touches the accept mutation
    family (_accept.py), the error message enum (_models.py), CLI dispatch/help (_mutate.py,
    _metadata.py), its test file, and the one doc section (tickets-data-storage.md)
    documenting the 0-based CLI contract that must move to 1-based'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'T-3908: --amend/--remove index convention fix touches the accept mutation
    family (_accept.py), the error message enum (_models.py), CLI dispatch/help (_mutate.py,
    _metadata.py), its test file, and the one doc section (tickets-data-storage.md)
    documenting the 0-based CLI contract that must move to 1-based'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'T-3908: --amend/--remove index convention fix touches the accept mutation
    family (_accept.py), the error message enum (_models.py), CLI dispatch/help (_mutate.py,
    _metadata.py), its test file, and the one doc section (tickets-data-storage.md)
    documenting the 0-based CLI contract that must move to 1-based'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_tickets_acceptance.py
  reason: 'T-3908: --amend/--remove index convention fix touches the accept mutation
    family (_accept.py), the error message enum (_models.py), CLI dispatch/help (_mutate.py,
    _metadata.py), its test file, and the one doc section (tickets-data-storage.md)
    documenting the 0-based CLI contract that must move to 1-based'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'T-3908: --amend/--remove index convention fix touches the accept mutation
    family (_accept.py), the error message enum (_models.py), CLI dispatch/help (_mutate.py,
    _metadata.py), its test file, and the one doc section (tickets-data-storage.md)
    documenting the 0-based CLI contract that must move to 1-based'
  actor: logan
  at: '2026-09-07'
body_changes:
- mode: set
  reason: 'de-pointer flags and code paths that cannot resolve in this repo: proposed
    flags and a python attribute path were read as CLI invocations and a TOML section,
    blocking lands'
  actor: logan
  at: '2026-09-05'
  old_length: 4025
  new_length: 4027
evidence:
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_refuses_zero_index_not_the_first_criterion
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_refuses_zero_index_does_not_drop_the_first_criterion
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_zero_index_is_rejected_not_the_first_criterion
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_remove_zero_index_is_rejected_not_the_first_criterion
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_one_edits_the_criterion_show_prints_as_one
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_amend_missing_reason_refused_before_ticket_is_read
- tests/test_tickets_acceptance.py::TestAcceptCliAmendRemove::test_cli_remove_missing_reason_refused_before_ticket_is_read
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_amend_replaces_text_and_records_reason
- tests/test_tickets_acceptance.py::TestAmendAcceptance::test_remove_drops_criterion_and_records_reason
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as logand.app-v2 FROBLEMS F-075 and F-074. F-075 is a REGRESSION
CREATED TODAY by a partial fix, and it has a destructive path.

MEASURED ON MAIN, 2026-09-05, after T-3837 landed (72b412d78):

    frob ticket show          displays criteria as [1], [2], [3]   (1-based)
    frob ticket evidence --accepts N   1-based, loud refusal for 0 or out-of-range
    frob ticket accept --amend INDEX   0-BASED
    frob ticket accept --remove INDEX  0-BASED

    src/frob/app/ticket_runner/_mutate.py:739
        ticket.acceptancecfg dot ticket_accept_amend_index.text
    -- raw list indexing, and the --help text says "replace acceptance[INDEX]'s
    text", bracket notation that reads as a raw 0-based list index.

So on current main, `frob ticket show` prints [1] for the first criterion,
`--accepts 1` binds evidence to the FIRST criterion, and `--amend 1` edits the
SECOND. Three surfaces over one list, two conventions.

WHY THIS IS WORSE THAN THE BUG IT CAME FROM. T-3837 fixed a real defect:
`--accepts` was 0-based with an out-of-range check (`i<0 or i>=len`) that could
never catch an in-range-but-wrong index -- a silent mis-binding. The fix moved
`--accepts` and the display to 1-based. That was correct and it landed. But
`--amend`/`--remove` were out of that ticket's scope and did not move, so a
consistent-if-undocumented system became an INCONSISTENT one, which is harder to
reason about: a user who learns the display is 1-based now has a correct mental
model that silently fails on two verbs.

AND ONE OF THEM DELETES. `--remove INDEX` drops an acceptance criterion
outright. Off by one there removes the WRONG criterion, and the
acceptance_amendments audit trail records the removal with the reason the
operator gave -- so the audit trail confidently documents an edit that did not
happen to the thing named. That is the silent-mis-binding shape T-3837 existed
to close, relocated rather than removed.

FIX: make `--amend` and `--remove` 1-based, matching the display and
`--accepts`, with the same loud typed refusal for 0 and for out-of-range that
T-3837 added. Update the --help text: "acceptance[INDEX]" should not use raw
bracket notation if the index is 1-based -- say "the Nth acceptance criterion
(1-based; see `frob ticket show`)" as T-3837 did for its own flags.

SEARCH FOR SIBLINGS BEFORE FIXING. T-3837 moved two surfaces and missed two.
Enumerate EVERY place an acceptance index is accepted or displayed -- CLI flags,
remedy strings, the MCP serve adapter, done-report rendering, anything in
docs/ -- and report the base of each. Fixing two more by name repeats exactly
the mistake that produced this regression.

DO NOT resolve this by reverting T-3837 to 0-based. The display is 1-based and
matching the display is what makes an index checkable by a human. Move the
laggards forward.

SECOND, SEPARATE DEFECT IN THE SAME COMMAND (F-074): `accept --amend` demands
`--reason` only AFTER parsing the whole command. Same class as F-063
(`ticket scope --add` demanding --reason only after a full sweep) and the same
principle: CHEAP ARGUMENT VALIDATION MUST RUN BEFORE EXPENSIVE WORK. A missing
required flag is decidable from argv alone. Fix it here, and note it as the
second instance so the general audit asked for in F-063's ticket covers both.

MUST-FIRE FIXTURES:
  - `--amend 0` and `--remove 0` are loud typed refusals naming the valid range
  - an out-of-range index on either is a loud refusal, not a clamp or wraparound
  - a missing --reason is refused before any ticket is read
MUST-STAY-QUIET:
  - `--amend 1` edits the criterion `frob ticket show` prints as [1]
  - `--accepts 1` still binds to that same criterion (no regression on T-3837)

ACCEPTANCE
- --amend and --remove 1-based, matching display and --accepts.
- The full enumeration of acceptance-index surfaces reported, with each base.
- --help text corrected away from raw bracket notation.
- --reason validated before expensive work.
- All fixtures committed. The --remove one matters most: it is the destructive
  path.