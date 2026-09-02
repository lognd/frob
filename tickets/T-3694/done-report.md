## Done report

Changed:
.claude/hooks/_root_write_guard_lib.py::_strip_prose
.claude/hooks/_root_write_guard_lib.py::_QUOTED_SPAN_RE
.claude/hooks/_root_write_guard_lib.py::_HEREDOC_BODY_RE
.claude/hooks/_root_write_guard_lib.py::_effective_cwd_from_tokens
.claude/hooks/_root_write_guard_lib.py::_effective_cwd
.claude/hooks/_root_write_guard_lib.py::_bash_ticket_verb_targets_root
.claude/hooks/_root_write_guard_lib.py::_is_legitimate_land

Evidence:
tests/test_hook_root_write_guard.py::test_bash_quoted_ticket_verb_argument_is_allowed
tests/test_hook_root_write_guard.py::test_bash_ticket_verb_in_single_quoted_commit_message_is_allowed
tests/test_hook_root_write_guard.py::test_bash_ticket_land_still_refused_alongside_quoted_prose
tests/test_hook_root_write_guard.py::test_bash_set_prefixed_cd_into_worktree_is_allowed
tests/test_hook_root_write_guard.py::test_bash_pushd_into_worktree_is_allowed
tests/test_hook_root_write_guard.py::test_bash_set_prefixed_cd_into_primary_still_refused
tests/test_hook_root_write_guard.py::test_bash_heredoc_body_containing_delimiter_substring_is_allowed
tests/test_hook_root_write_guard.py::test_bash_heredoc_appending_into_checkout_still_refused_with_delimiter_substring
plus all 39 pre-existing tests in tests/test_hook_root_write_guard.py, all still green (47/47 total)

Filed: none (this ticket's scope covers all three measured false-positive shapes; coordinator's mid-task heredoc report was folded into this same ticket rather than filed separately)

Gates: frob check --ticket T-3694 clean of scope-caused findings (remaining 5 errors are pre-existing/repo-wide and unrelated to this diff: DEPR006/WAIVE011 lock-producer-abandoned advisories, TICK011 on unrelated T-3689, claude-config-drift x2 expected pre-coordinator-sync). frob test --base main: PASS (exit=0).

### Changed
```
 .claude/hooks/_root_write_guard_lib.py | 125 +++++++++++++++++++++++++---
 tests/test_hook_root_write_guard.py    | 145 +++++++++++++++++++++++++++++++++
 tickets/T-3694/done-report.md          |  36 ++++++++
 tickets/T-3694/ticket.md               |   9 ++
 4 files changed, 305 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_hook_root_write_guard.py::test_bash_quoted_ticket_verb_argument_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_in_single_quoted_commit_message_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_land_still_refused_alongside_quoted_prose` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_set_prefixed_cd_into_worktree_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_pushd_into_worktree_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_set_prefixed_cd_into_primary_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_heredoc_body_containing_delimiter_substring_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_heredoc_appending_into_checkout_still_refused_with_delimiter_substring` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 4 error(s), 4271 warning(s), 912 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, DEPR006@frob-deprecated-baseline.lock.json, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json
