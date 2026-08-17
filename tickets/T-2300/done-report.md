## Done report

T-2300's directive-anchor false-positive gap (a commented-out or quoted
mention of a REAL ticket id matching identically to a live directive) is
closed: `_directive_anchor_signals_on_branch` now resolves each
candidate blob through the real comment-DSL parser
(`frob.lang.parse_file` + `frob.graph.dsl.parse_directives`, the same
machinery a normal `frob check` gate run uses) before falling back to
the old bare regex only when that language is unsupported or the blob
fails to parse -- so precision improves without losing coverage for a
language the parser cannot handle.

Repro: `test_real_ticket_id_inside_a_string_literal_is_not_flagged`
(a REAL, non-terminal ticket id quoted inside a string literal, not a
directive-position comment) fails at the test-only commit (8ce11ed71,
before the parser switch) and passes after the fix. Positive control:
`test_real_directive_anchor_still_flagged_via_real_parser` confirms a
genuine directive-position comment for a real ticket still reports --
the switch narrows precision, it does not also narrow coverage. All 21
pre-existing plus new tests in tests/unit/test_unlanded_branch_work.py
pass (`SUITE-RESULT: exitstatus=0 collected=21 failed=0`).

### Changed
```
 src/frob/tickets/_unlanded.py           | 72 ++++++++++++++++++++++++++++++++-
 tests/unit/test_unlanded_branch_work.py | 60 +++++++++++++++++++++++++++
 tickets/T-2300/ticket.md                | 14 ++++++-
 3 files changed, 142 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_directive_anchor_still_flagged_via_real_parser` (pytest node id, verified passing when recorded)
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_ticket_id_inside_a_string_literal_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md
