## Done report

frob:waive BUG002 reason="this ticket's own defect is a malformed frob:tests directive kind= value (a metadata/lint correction, not a code-behavior bug); there is no runtime behavior for a test to fail-then-pass around, matching the ledger/doc-correction-filed-as-kind=bug case docs/modules/gates.md#bug002-t-1421 names as BUG002's own intended escape hatch"

## Done report

Changed:
- tests/test_lang.py -- 4 `frob:tests` directives (lines 921, 927, 942,
  963) that used `kind="control"`, an invalid kind value, now use
  `kind="unit"` (these are ordinary pytest unit tests exercising real
  consumers, per T-2195's own land warning that filed this ticket).

Evidence:
- tests/test_lang.py::TestResolveLocalImportConsumers::{test_cycle_detected_in_top_level_layout,test_cycle_detected_in_src_layout_too,test_layering_resolves_a_nonempty_target_set,test_layering_detects_a_real_violation}
  -- the 4 tests whose directives were fixed; `pytest tests/test_lang.py
  -o addopts="" -q` -> "SUITE-RESULT: exitstatus=0 collected=56 failed=0"
  (all 56 tests in the file pass, no regression).

Measured: `frob check --only gates-fast --ticket T-2203 --json`'s
gate:TEST TEST010 count dropped from 5 to 1 (the remaining one, at
tests/test_ticket_work_and_land_finish.py:740, is pre-existing, unrelated,
outside this ticket's scope, and predates this ticket -- confirmed via
`git show 26ff8cdec:tests/test_ticket_work_and_land_finish.py`). No
SCOPE001/COV002 introduced.

Filed: none.

Gates: `frob check --only gates-fast --ticket T-2203` -- clean of
anything this ticket's own diff introduces; every remaining error (COV001
on scripts/fleet_status.py, COV004 attachment-sha mismatches on
T-2195/T-2197, DOC011 stale draft citations, DRIFT001 on two unrelated
symbols, the one pre-existing TEST010, TICK004 rot warnings) is repo-wide
pre-existing floor debt.

### Changed
```
 tests/test_lang.py            |  8 ++++----
 tickets/T-2203/done-report.md | 47 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2203/ticket.md      |  7 ++++++-
 3 files changed, 57 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_top_level_layout` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_src_layout_too` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_resolves_a_nonempty_target_set` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_detects_a_real_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2201-series/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2203, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
