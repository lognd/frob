## Done report

Changed:
- .claude/hooks/frob-suggest.py::_RULES (added handrolled-floor-count, handrolled-fleet-probe)
- design/frob.strata (capability registry entries for tests/test_hook_frob_suggest.py)
- tests/test_hook_frob_suggest.py (13 new tests)

Evidence: 13/13 pytest node ids pass (measured: `uv run pytest tests/test_hook_frob_suggest.py -p no:cacheprovider -q` -> SUITE-RESULT: exitstatus=0 collected=13 failed=0), all 13 already bound in the ticket's evidence list.

Filed: none (successor already carries T-2031's scope; no new out-of-scope work found)

Gates: `frob check --ticket T-2033 --only scope` clean (0 errors, 120 warnings, 0 unresolved). `frob check --ticket T-2033 --only drift` clean (0 errors, 3 waived, pre-existing). Repo-wide gate families not re-run per section 6c/coordinator scope; test file itself green.

### Changed
```
 .claude/hooks/frob-suggest.py   |  48 ++++++++
 design/frob.strata              |   6 +-
 tests/test_hook_frob_suggest.py | 248 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-2033/ticket.md        |  36 +++++-
 4 files changed, 334 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::test_check_count_pipeline_is_blocked_naming_check_summary` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_fleet_probe_combo_is_blocked_naming_fleet_status` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_fleet_probe_combo_with_worktree_list_is_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_fleet_probe_combo_with_pgrep_is_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_second_identical_fleet_probe_is_allowed_through` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_plain_check_only_gates_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_check_piped_to_tail_only_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_git_grep_piped_to_grep_is_not_blocked_by_new_rules` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_plain_git_status_porcelain_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_bare_ps_aux_grep_alone_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_check_summary_invocation_itself_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_fleet_status_invocation_itself_is_not_blocked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, PRE001@tickets/T-2033, SELFAUDIT001@design
