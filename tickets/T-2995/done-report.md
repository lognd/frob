## Done report

Changed:
- src/frob/narrative/_migrate.py -- add `paragraph_at` (block_at's markdown-
  prose counterpart, blank-line-delimited); relax `_validate_block` to accept
  a non-comment lead line and search the whole block for a ticket id when the
  lead line itself names none; make `migrate_block`'s one-line reference
  format-aware (plain prose for `.md`, unchanged `#`-comment shape otherwise).
- src/frob/narrative/_cli.py -- `frob narrative move` picks `paragraph_at` vs
  `block_at` by file suffix.
- tests/test_narrative_migrate.py -- TestParagraphAt (2 cases),
  TestMigrateBlockSplit.test_markdown_paragraph_reference_line_is_plain_prose.
- docs/commands/narrative.md -- the representative sample: moved the
  DuplicateId-hazard history into T-2678 (archived) via the real CLI; fixed
  the doc's own stale "NOT YET wired" NARR001 status now that T-3014 landed.

No second detector, no second migration path: same `migrate_block`/`set_body`
engine T-2993 built, extended, not forked.

Sample proved: docs/commands/narrative.md, before 61 lines / after 54 lines
(`git diff --stat`: 4 insertions, 11 deletions). Ran the real
`frob narrative move docs/commands/narrative.md 33 --keep-file ... --reason ...`
against T-2678 (archived, done). Verified:
- `git -C tickets/archive/T-2678 grep narrative-moved` shows the idempotency
  marker written to the ARCHIVE path (no DuplicateId).
- `frob ticket list` exits 0 afterward (the T-2994 archived-write-hazard
  regression check).
- Re-running the identical move reports "already migrated -- no-op"
  (idempotency, T-2994 constraint 4).
- MOVE, NEVER DELETE: the DuplicateId-hazard sentence is gone from the doc
  file but present verbatim (via `frob.tickets.set_body`) in T-2678's ticket
  body -- nothing lost, only relocated.

Before/after counts (repo-wide, from T-2994's own epic measurement, restated
here for this ticket's own record): 30,959 of 69,736 doc lines (44%) sit in
paragraphs citing a ticket id, across 137 of 146 files (94%). This ticket's
own sample touched 1 of those 137 files. The remaining 140-file bulk (re-
measured via `git ls-files 'docs/**/*.md' | xargs grep -c 'T-[0-9]\{2,6\}'`,
non-zero rows) is filed as T-3023, an epic with no file scope of
its own (declared via `--declare-no-scope`) carrying the full per-file count
table and the split-by-file dispatch plan -- NOT scoped or attempted here.
Verify its real id on main before citing it further.

Filed: T-3023 ("Docs narrative bulk migration: 140 files still
cite tickets in prose, split by file").

Evidence:
tests/test_narrative_migrate.py::TestParagraphAt::test_finds_blank_line_delimited_paragraph,
tests/test_narrative_migrate.py::TestParagraphAt::test_blank_line_returns_none,
tests/test_narrative_migrate.py::TestMigrateBlockSplit::test_markdown_paragraph_reference_line_is_plain_prose
-- all 16 tests in tests/test_narrative_migrate.py collected and passed
(`pytest tests/test_narrative_migrate.py -q`, exitstatus=0 collected=16 failed=0).

Gates: `frob check --only docblocks` (unbudgeted, gate-summary present) shows
the doc's own pre-existing DOC006 finding (line 7, `frob narrative move` not
yet a registered subcommand in the docblocks command registry -- T-3020's
territory, not this ticket's) unchanged, and the NEGEXIST001 "NOT YET wired"
finding on this doc's old wiring-status paragraph is gone (that text no
longer exists).

### Changed
```
 docs/commands/narrative.md         | 15 ++----
 src/frob/narrative/_cli.py         | 12 ++++-
 src/frob/narrative/_migrate.py     | 59 +++++++++++++++++++----
 tests/test_narrative_migrate.py    | 42 +++++++++++++++++
 tickets/T-2995/ticket.md           | 68 +++++++++++++++++++++++++-
 tickets/T-3023/ticket.md | 97 ++++++++++++++++++++++++++++++++++++++
 6 files changed, 269 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_narrative_migrate.py::TestParagraphAt::test_finds_blank_line_delimited_paragraph` (pytest node id, verified passing when recorded)
- `tests/test_narrative_migrate.py::TestParagraphAt::test_blank_line_returns_none` (pytest node id, verified passing when recorded)
- `tests/test_narrative_migrate.py::TestMigrateBlockSplit::test_markdown_paragraph_reference_line_is_plain_prose` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 57 error(s), 630 warning(s), 854 waived
- error-findings: ARCH001@src/frob/narrative/_cli.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3015/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t3014-series/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2995, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
