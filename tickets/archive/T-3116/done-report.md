## Done report

T-1907's touched-file ty gate refused a land on ANY error in a touched
file, even one the diff merely relocated -- measured incident: an agent
landing T-3106 silenced a pre-existing _config_external.py finding its
diff only shifted a few lines down the file, because that was the only
way through. Against a repo carrying hundreds of frob:waive / ty:ignore
suppressions, this is a suppression factory: every ticket touching a
file with a pre-existing finding must fix out-of-scope debt or silence
it, and silencing is always cheaper under pressure.

Fixed by attributing findings to the DIFF, not the FILE.
_ty_baseline_diagnostic_identities runs a second ty pass against the
SAME touched files at this ticket's merge-base with main (a detached
git worktree add --detach snapshot, the same race-free primitive
_capture_pre_land_baseline already uses -- never an in-place swap of
worktree's own live files), only when the current pass already found at
least one error (the zero-error fast path is unchanged). Identity is
(file, code, message), deliberately excluding line/col (T-3065's own
lesson: line number is not identity). Comparison is MULTISET count, not
set membership -- caught during implementation itself: two textually
identical mistakes in two different functions share one (file, code,
message) identity, so a plain set-difference would let a genuinely new
SECOND occurrence hide behind one pre-existing occurrence of the same
shape. A Counter-based excess comparison (current count minus baseline
count, per identity) keeps exactly one relocation invisible while still
refusing a second, brand-new occurrence.

An unmeasurable baseline (no merge-base, snapshot spawn failure, ty
could not run there) degrades to the pre-T-3116 file-scoped refusal
posture rather than being read as "everything is pre-existing".

AUDIT (per the ticket's "also worth checking" note): the sibling
pre-land lint gate (T-3061, _assert_touched_files_lint_clean_pre_land)
has the identical file-scoped-not-diff-scoped shape. Not fixed here
(out of T-3116's declared scope) -- filed as T-3132.

MEASURED EFFECT (estimate, stated method): grep for the ty-specific
suppression comment (ty:ignore, since ty findings are not waivable via
frob:waive -- that directive covers frob check's own gate families)
found 93 occurrences across 45 files repo-wide; excluding
generator-template strings (gates/_fix_engine_text.py) and docstring
mentions (gates/_suppress.py), roughly 20 are real code-level
suppressions. Manually inspected each: all are the ordinary justified
shapes (optional-dependency import fallback, decorator/override return
type, dynamic attribute access on a third-party object) rather than a
suppression whose surrounding edit is unrelated to the suppressed
line's own purpose -- the T-3116 pressure's signature. None in this
small sample show that signature, so this specific pressure is not the
dominant source of the existing ty-ignore population; it plausibly
contributed to the much larger frob:waive population (493 directives,
2134 lines) for OTHER gate families this same file-scoped-refusal shape
still has (see T-3132), but that is now a separate, filed question
rather than an open one.

SCOPE NOTE: the ticket's declared scope named
src/frob/check/_typecheck.py, a file with no commits in this repo's
history -- never existed. Corrected via frob ticket scope --remove
src/frob/check/_typecheck.py --add
src/frob/app/ticket_runner/_land_cmd.py (plus
docs/modules/tickets-landing.md for the doc edge), reason recorded in
the scope-change audit trail, before touching any code.

### Changed
```
 tickets/T-3116/ticket.md | 35 ++++++++++++++++++++++++++--
 tickets/T-3132/ticket.md | 60 ++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 93 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land_ty_diff_attribution.py::TestTyDiagnosticIdentity::test_ignores_line_and_col` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_pre_existing_finding_that_merely_shifted_lines_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_genuinely_new_finding_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_ty_diff_attribution.py::TestAssertTouchedFilesTypeCheckPreLand::test_baseline_unmeasurable_falls_back_to_file_scoped_refusal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 89 error(s), 888 warning(s), 865 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/app/ticket_runner/_land_cmd.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/test_ticket_land_ty_diff_attribution.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_process_reap.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/test_ticket_land_ty_diff_attribution.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_process_reap.py, DRIFT002@tests/unit/test_reopen_ticket.py, DUP001@tests/test_ticket_land_ty_diff_attribution.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bw/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3116, REF001@.claude-scratch/T-3122-close-guard-repro-capture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, SUPPRESS001@src/frob/app/_config_external.py, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@src/frob/gates/_wire.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, invalid-argument-type@tests/test_ticket_land_ty_diff_attribution.py, unknown-argument@tests/unit/test_app_runners_process.py, unknown-argument@tests/unit/test_pytest_spawn_env_wiring.py
