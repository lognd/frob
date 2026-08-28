## Done report

Changed:
.claude/hooks/frob-suggest.py::_import_modules
.claude/hooks/frob-suggest.py::_rename_state_path
.claude/hooks/frob-suggest.py::_edit_rename_hit
.claude/hooks/frob-suggest.py::_escalate
.claude/hooks/frob-suggest.py::_handle_edit
.claude/hooks/frob-suggest.py::_handle_bash
.claude/hooks/frob-suggest.py::_match
.claude/hooks/frob-suggest.py::main
.claude/settings.json (frob-suggest PreToolUse matcher: Bash -> Bash|Edit)

Evidence:
tests/test_hook_frob_suggest.py::test_hand_rename_sed_fires_on_scripted_import_rewrite
tests/test_hook_frob_suggest.py::test_hand_rename_perl_fires_on_scripted_import_rewrite
tests/test_hook_frob_suggest.py::test_hand_rename_sed_stays_quiet_without_import_mention
tests/test_hook_frob_suggest.py::test_hand_rename_sed_stays_quiet_inside_frob_refactor_invocation
tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_second_file_rewriting_same_module_import_fires
tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_brand_new_import_never_fires
tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_single_file_repeated_edits_never_fire
tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_refactor_residue_prose_fix_never_fires
tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it

The 4 must-fire/must-stay-quiet fixtures directly named in the brief
(scripted sed rewrite, multi-file Edit sequence, brand-new import,
single-file edit, refactor-residue prose fix, frob refactor invocation)
were all confirmed to FAIL against the pre-change hook (manual before/
after run of the hook file, restored after) before the fix landed.

Design decisions per the brief:
- Landed AFTER T-3066 (chosen over "acknowledge the limitation in the
  message") since T-3066 is now on main and `frob refactor
  rename`/`move`/`split`/`move-module` all share the fixed scan path.
- Verified the recommended verb works for a subagent caller: ran
  `frob refactor rename` end-to-end from this session (a dispatched
  subagent) against a scratch repo; it applied the rewrite ops
  correctly (`refactor.apply: applied 4 op(s) across 2 file(s)`) --
  the only failures were the scratch repo's own missing pytest/frob
  project scaffolding (`pytest_collect`/`check_delta`), not a
  subagent refusal like EnterWorktree's.
- Both new signals share the existing block-once-then-escalate
  machinery (T-2164/_escalate) rather than inventing a second policy.
- `hand-rename-sed` matches against the RAW command (not the
  quote-stripped one every other rule uses) because the `import`
  mention lives inside the sed/perl script's own quotes.
- `.claude/hooks/frob-suggest.py` re-synced to ~/.claude via
  `python3 .claude/hooks/sync-claude-config.py`; `frob claude sync
  --check` reports 9 file(s) in sync.

Filed: none

Gates: `frob check --only scope --ticket T-3069` clean (0 errors, 1
warning -- a pre-existing scope-closure doc-anchor notice on
`.claude/hooks/frob-suggest.py::main`, not something this ticket's
diff introduced). Repo-wide gate:DRIFT (21 errors) and gate:WAIVE (1
error, T-2993) are pre-existing and unrelated to this ticket's scope.

### Changed
```
 .claude/hooks/frob-suggest.py   | 255 +++++++++++++++++++++++++++++++++++-----
 .claude/settings.json           |   2 +-
 tests/test_hook_frob_suggest.py | 243 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3069/ticket.md        |  34 +++++-
 4 files changed, 500 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::test_hand_rename_sed_fires_on_scripted_import_rewrite` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_hand_rename_perl_fires_on_scripted_import_rewrite` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_hand_rename_sed_stays_quiet_without_import_mention` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_hand_rename_sed_stays_quiet_inside_frob_refactor_invocation` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_second_file_rewriting_same_module_import_fires` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_brand_new_import_never_fires` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_single_file_repeated_edits_never_fire` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_refactor_residue_prose_fix_never_fires` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 70 error(s), 648 warning(s), 862 waived
- error-findings: AFFECT001@.claude/hooks/frob-suggest.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV005@.claude/hooks/frob-suggest.py, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3069/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3069, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py
