## Done report

T-1271's declared scope (src/frob/app/config.py, src/frob/_cli_parsers/
__init__.py, docs/modules/app.md, tests/test_app_config.py) reaches only
the AppConfig pydantic layer, not the argparse parser builders in
src/frob/_cli_parsers/_ticket/**, src/frob/_cli_parsers/_check.py, the
scope-closure warning emitter, or frob check's lease machinery -- several
of the ticket's five acceptance criteria structurally cannot be
implemented inside this scope. Implemented the minimal honest core that
DOES fit and disclosed the rest as a draft rather than silently widening
scope (per this drive's epic-closure instruction).

Shipped (acceptance criterion 0, the one genuinely reachable from this
scope): AppConfig now carries a field_validator for every ticket-model
StrEnum-backed field (ticket_state, ticket_kind, ticket_kind_value,
ticket_tier, ticket_tier_value, ticket_priority_level, ticket_origin,
ticket_review_verdict). An unrecognized value raises a pydantic
ValidationError naming every legal value inline -- e.g. `'open' is not a
valid ticket state; valid values are: queued, planned, in-progress,
blocked, done, dropped` -- instead of the bare, terser ValueError a raw
TicketState(v) call downstream used to raise with no indication of what
would have been valid (the exact `frob ticket list --status open`
symptom the ticket cites). frob.__main__.main's existing top-level
`except Exception` already prints this as a clean `frob: <message>` and
exits 1, so the fix needed no __main__.py change (out of scope anyway).
docs/modules/app.md documents the addition and honestly notes what this
ticket's own scope could not reach.

Deferred, disclosed, filed as T-1557 (parent T-1238): AC0's
remainder for non-ticket-model enum flags; AC1 (scope-closure warning
collapse + --verbose); AC2 (frob check --ticket read-only/no-lease for
review/show/brief); AC3 (a close-porcelain verb + ticket renumber --help
examples); AC4 (docs/design/ cli-hygiene doc + checklist gate). All four
require files outside T-1271's declared scope (_cli_parsers/**,
tickets/**, check/**, docs/design/**).

Changed:
  src/frob/app/config.py::_validate_enum_choice
  src/frob/app/config.py::AppConfig._check_ticket_state
  src/frob/app/config.py::AppConfig._check_ticket_kind
  src/frob/app/config.py::AppConfig._check_ticket_kind_value
  src/frob/app/config.py::AppConfig._check_ticket_tier
  src/frob/app/config.py::AppConfig._check_ticket_tier_value
  src/frob/app/config.py::AppConfig._check_ticket_priority_level
  src/frob/app/config.py::AppConfig._check_ticket_origin
  src/frob/app/config.py::AppConfig._check_ticket_review_verdict
  tests/test_app_config.py::TestEnumFieldValidation (new file)
  docs/modules/app.md#config (new paragraph)
  design/frob.strata (testsuite node: attr interface=TestEnumFieldValidation)

Evidence: 10 pytest node ids under tests/test_app_config.py::
TestEnumFieldValidation, all bound to acceptance index 0.

Gates: frob check --only archgate --only test --only coverage --only sys
--ticket T-1271: gate:ARCH/gate:LARGE/gate:TEST/gate:TODO/gate:scope-note
all pass; gate:COV shows 14 repo-wide pre-existing errors, none touching
any file this ticket changed (verified: no config.py/test_app_config.py/
frob.strata line among them) -- confirmed unrelated debt, not introduced
by this change. --ticket scoping note: COV002/TODO001 and SCOPE/PREWORK
are the only families actually filtered to this ticket's touched set;
the rest are repo-wide counts (section 6c) -- disclosed, not claimed
clean.

Filed: T-1557 (remainder of AC1-4 and AC0's non-ticket-enum
half; parent T-1238).

Waive-deletion declaration (land OutOfScopeWaiveDeletion audit): this
worktree also carries T-1238's explore-regroup slice, which un-deprecates
frob docs --search / map / outline / xref. That work deletes the four
DEPR003 waivers listed here (one file:rule pair per line):
- src/frob/app/docs_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
- src/frob/app/map_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
- src/frob/app/outline_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
- src/frob/app/xref_runner.py DEPR003 waiver deleted (T-1238 un-deprecation)
alongside their frob:deprecated
markers -- each waiver's own reason text mandated exactly this removal
("T-1238's own acceptance criterion is to remove this frob:deprecated
marker entirely once the frob explore regroup lands"). Attributed to
T-1238 (in-progress in this same worktree), intentional, not scope
creep by T-1271.

### Changed
```
 README.md                         |   3 +-
 design/frob.strata                | 765 +++++++++++++++++++-------------------
 docs/commands/map.md              |   3 +
 docs/commands/outline.md          |   3 +
 docs/commands/xref.md             |   3 +
 docs/design/cli-regrouping.md     | 143 +++++++
 docs/guides/agentic-workflow.md   |   4 +-
 docs/index.md                     |  15 +-
 docs/modules/app.md               |  27 ++
 docs/modules/cli.md               |  79 ++--
 docs/modules/render.md            |   5 +-
 docs/rework.md                    |   4 +-
 src/frob/__main__.py              |   2 +
 src/frob/_cli_parsers/__init__.py |   2 +
 src/frob/_cli_parsers/_core.py    |  15 +-
 src/frob/_cli_parsers/_explore.py |  71 ++++
 src/frob/app/_config_external.py  |   1 +
 src/frob/app/app.py               |   4 +
 src/frob/app/config.py            | 106 +++++-
 src/frob/app/docs_runner.py       |  15 +-
 src/frob/app/explore_runner.py    |  61 +++
 src/frob/app/map_runner.py        |  16 +-
 src/frob/app/outline_runner.py    |  16 +-
 src/frob/app/xref_runner.py       |  22 +-
 tests/test_app_config.py          |  87 +++++
 tests/unit/test_app_runners.py    |  48 +++
 tickets.md                        | 419 ++++++++++++++++++++-
 27 files changed, 1434 insertions(+), 505 deletions(-)
```

### Evidence
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_state_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_valid_ticket_state_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_none_ticket_state_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_value_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_value_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_priority_level_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_origin_lists_valid_values` (pytest node id, verified passing when recorded)
- `tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_review_verdict_lists_valid_values` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 364 warning(s), 781 waived
- error-findings: none (measured, zero errors)

### Acceptance amendments
- [4] remove: removed "GIVEN the audit lands THEN a short cli-hygiene principles doc exists in docs/design/ and a checklist test (or gate rule) verifies new parsers against it (every flag help string states its default; no flag silently changes another flag's meaning)" (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)
- [3] remove: removed "GIVEN a multi-step workflow (close needs start, done-report, evidence, accepts) THEN each refusal names the exact next command AND a single porcelain verb exists that sequences the happy path; hidden optional arguments that change behavior (e.g. renumber's positional-only contract) are documented in --help with examples" (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)
- [2] remove: removed 'GIVEN a read-only invocation (check --ticket for review, show, brief) THEN it never requires a lease or mutates state -- reviewers repeatedly could not re-verify gate claims because check --ticket demands a lease' (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)
- [1] remove: removed 'GIVEN a command emits repeated advisory warnings (scope-closure on ticket new can flood thousands of lines) THEN they collapse to a counted summary with a --verbose escape hatch -- signal is never drowned' (reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree draft T-1557 cannot survive the land preview, land-splice draft-loss class); logan, 2026-08-05)
