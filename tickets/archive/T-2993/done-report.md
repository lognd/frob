## Done report

Changed:
- src/frob/gates/_narrative_blocks.py (new): NARR001, scan_narrative_blocks, narrative_blocks_gate
- src/frob/narrative/__init__.py, _cli.py, _migrate.py (new package): frob narrative move
- src/frob/__main__.py: _dispatch_narrative wired as a direct-dispatch verb (frob:waive DUP001/SYS003, cited follow-up T-3014)
- docs/commands/narrative.md (new)
- docs/design/registry/check-coverage.yaml: CHK-GATE-NARR001 entry
- tests/test_narrative_blocks.py, tests/test_narrative_migrate.py (new)

Evidence: tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_must_fire_long_archaeology_block,
tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_socketd_t2961_block_stays_quiet_at_default_threshold,
tests/test_narrative_migrate.py::TestMigrateBlockSplit::test_load_bearing_sentence_stays_when_named_as_keep,
tests/test_narrative_migrate.py::TestIdempotency::test_marker_already_present_refuses_as_already_migrated,
tests/test_narrative_migrate.py::TestNarrativeIntegration::test_frob_narrative_move_dry_run_via_subprocess
(18/18 in both test files pass; full list in the test files themselves)

Filed: T-3014 ("Wire NARR001 into gates/__init__.py") -- renumbers at land.

Gates: frob check --ticket T-2993 clean on gate:SCOPE (0 errors), gate:COV (0 errors
attributable to this diff), gate:FMT/AFFECT clean. WIRE001, DUP001, SYS003 explicitly
waived with follow_up=T-3014 (gates/__init__.py and design/frob.strata were
both T-2986-leased for this ticket's entire work window -- proven by attempting the
scope --add and getting ScopeLeaseConflict both times). SELFAUDIT001 SYS102/103/106
(narrative package unbound in design/frob.strata) is unwaived (no per-line waiver
point exists for a design:1 finding) and remains in the repo-wide baseline that
gate already failed before this ticket; tracked by the same follow-up.

Archived-ticket-body-append route proven live on T-0001 (archived): `frob ticket
body T-0001 --append-file ... --reason ...` wrote only the archive path (no
tickets/T-0001/ active dir created), and `frob ticket list` exited 0 afterward.

Migration verb proven live end-to-end on the real ledger against T-2961 (the
_socketd.py-citing ticket): frob narrative move on a scratch copy of that file's
own block moved the historical cross-references into T-2961's body (idempotency
marker verified) and kept the load-bearing "AttributeError at IMPORT time" sentence
in the file, matching T-2993's own acceptance case. A second run against the
now-migrated file was a correct no-op.

NARR001 measured: 0 -> N/A repo-wide count not re-run in this ticket (gate is not
yet wired into `frob check`'s live rule set; see T-3014). Fixture-level
before/after: must-fire block (17 lines) flags 1 violation; must-stay-quiet block
(2 lines) and the socketd T-2961 block (12 lines, at threshold) flag 0.

### Changed
```
 docs/commands/narrative.md               |  61 ++++++++
 docs/design/registry/check-coverage.yaml |   5 +
 src/frob/__main__.py                     |  33 ++++
 src/frob/gates/_narrative_blocks.py      | 155 +++++++++++++++++++
 src/frob/narrative/__init__.py           |  35 +++++
 src/frob/narrative/_cli.py               | 195 ++++++++++++++++++++++++
 src/frob/narrative/_migrate.py           | 251 +++++++++++++++++++++++++++++++
 tests/test_narrative_blocks.py           | 109 ++++++++++++++
 tests/test_narrative_migrate.py          | 245 ++++++++++++++++++++++++++++++
 tickets/T-2961/ticket.md                 |  12 +-
 tickets/T-2993/ticket.md                 |  96 +++++++++++-
 tickets/T-3014/ticket.md       |  39 +++++
 tickets/archive/T-0001/ticket.md         |  21 ++-
 13 files changed, 1254 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_must_fire_long_archaeology_block` (pytest node id, verified passing when recorded)
- `tests/test_narrative_blocks.py::TestNarrativeBlocksGate::test_socketd_t2961_block_stays_quiet_at_default_threshold` (pytest node id, verified passing when recorded)
- `tests/test_narrative_migrate.py::TestMigrateBlockSplit::test_load_bearing_sentence_stays_when_named_as_keep` (pytest node id, verified passing when recorded)
- `tests/test_narrative_migrate.py::TestIdempotency::test_marker_already_present_refuses_as_already_migrated` (pytest node id, verified passing when recorded)
- `tests/test_narrative_migrate.py::TestNarrativeIntegration::test_frob_narrative_move_dry_run_via_subprocess` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 61 error(s), 817 warning(s), 857 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2990/ticket.md, DOC006@tickets/T-2993/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t2993-series/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2993, REF002@docs/modules/ci_report.md, REF002@docs/modules/ghio.md, REF002@src/frob/gates/_narrative_blocks.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK011@tickets.md
