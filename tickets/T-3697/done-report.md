## Done report

Changed:
.claude/hooks/frob-directive-guard.py (new)
.claude/hooks/frob-directive-guard.py::main
.claude/hooks/frob-directive-guard.py::_corrected_target
.claude/hooks/frob-directive-guard.py::_violating_targets
.claude/settings.json (wired new PreToolUse hook, Write|Edit|NotebookEdit|Bash)
docs/guides/claude-hooks.md (new hook section, T-3695 --help note)
design/frob.strata (testsuite exec via-list: new test file)
docs/design/registry/capability-via-ratchet.lock.json (testsuite::exec ceiling 290 -> 291)

Evidence:
tests/test_hook_frob_directive_guard.py::test_write_double_colon_in_symbol_is_blocked
tests/test_hook_frob_directive_guard.py::test_write_correct_dotted_form_is_allowed
tests/test_hook_frob_directive_guard.py::test_write_with_no_directive_is_allowed
tests/test_hook_frob_directive_guard.py::test_edit_new_string_double_colon_is_blocked
tests/test_hook_frob_directive_guard.py::test_edit_old_string_double_colon_is_not_blocked
tests/test_hook_frob_directive_guard.py::test_bash_heredoc_writing_double_colon_directive_is_blocked
tests/test_hook_frob_directive_guard.py::test_bash_unrelated_command_is_allowed
tests/test_hook_frob_directive_guard.py::test_file_boundary_double_colon_alone_is_not_the_violation
tests/test_hook_frob_directive_guard.py::test_multiple_violations_all_named_in_denial
tests/test_hook_frob_directive_guard.py::test_unrecognized_tool_name_is_allowed
(all 10/10 green)

Filed: T-3702 (frob-timeout-guard.py misplaced frob:doc on private _HELP_OR_DRY_RUN_RE, found via gate:COV COV007 while checking this ticket -- out of this ticket's scope)

Gates: frob check --ticket T-3697 clean of scope-caused findings (COV001/COV007/DOC006/LANDPARITY001/SELFAUDIT001 all addressed in-scope; remaining errors are pre-existing/repo-wide: DEPR006/WAIVE011 lock-producer-abandoned advisories, TICK011 on unrelated T-3689, claude-config-drift pre-coordinator-sync). Manual stdin-JSON hook checks confirm: a Class::method payload blocks with the corrected form named, a correct path::Class.method payload passes, a no-directive edit passes.

### Changed
```
 .claude/hooks/frob-directive-guard.py              | 159 ++++++++++++++++
 .claude/settings.json                              |  11 ++
 design/frob.strata                                 |   2 +-
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 docs/guides/claude-hooks.md                        |  34 ++++
 tests/test_hook_frob_directive_guard.py            | 212 +++++++++++++++++++++
 tickets/T-3697/ticket.md                           |  33 +++-
 7 files changed, 452 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_hook_frob_directive_guard.py::test_write_double_colon_in_symbol_is_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_write_correct_dotted_form_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_write_with_no_directive_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_edit_new_string_double_colon_is_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_edit_old_string_double_colon_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_bash_heredoc_writing_double_colon_directive_is_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_bash_unrelated_command_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_file_boundary_double_colon_alone_is_not_the_violation` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_multiple_violations_all_named_in_denial` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_directive_guard.py::test_unrecognized_tool_name_is_allowed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 5 error(s), 4309 warning(s), 919 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV007@.claude/hooks/frob-timeout-guard.py, DEPR006@frob-deprecated-baseline.lock.json, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json
