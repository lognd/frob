## Done report

Added a stale-worktree detector (T-1030's root cause) wired into the existing
`commit_start_transition` call every `frob ticket start` already makes:
`warn_if_worktree_stale(root, ticket_id, main_ref="main")` in
src/frob/tickets/_leases.py measures how many commits `main`'s tip is ahead of
`git merge-base HEAD main` and logs a loud warning (naming the ticket id, the
commit count, and the playbook's warm-up anchor) once that count reaches the
configurable `[tickets] stale_worktree_warn_commits` threshold (frob.toml,
default 20). Best-effort/non-fatal throughout -- any git failure degrades to a
silent no-op, matching this module's other optional-signal helpers.

Extracted a shared `load_positive_int_config(root, key, default)` helper in
_leases.py (DUP001: my new stale-commits reader was 95% similar to the
existing `_load_large_glob_max_files` in tickets/__init__.py) and refactored
both to delegate to it.

Verified via a real multi-commit git-worktree fixture
(tests/test_ticket_leases.py::TestWarnIfWorktreeStale, 4 tests: warns past
threshold, silent within threshold, silent on a non-git root, respects a
configured threshold) plus TestLoadPositiveIntConfig (4 tests) for the shared
reader. docs/modules/tickets.md gained a "Stale-worktree-cut warning (T-1059)"
section.

`frob check --ticket T-1059` is clean except two pre-existing, unrelated
findings verified via `git diff main -- <file>` to be empty (not touched by
this ticket): an INV006 finding in src/frob/gates/_todo_fmt.py, and two
TICK006 phantom-draft findings from T-1077/T-1084's historical Done reports.
Also confirmed one pre-existing ruff-format finding in src/frob/gates/
__init__.py is untouched by this diff.

### Changed
```
 docs/modules/tickets.md      |  36 +++++++++++
 src/frob/tickets/__init__.py |  24 +++-----
 src/frob/tickets/_leases.py  | 113 +++++++++++++++++++++++++++++++++-
 tests/test_ticket_leases.py  | 142 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                   |  16 ++++-
 5 files changed, 314 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_warns_when_behind_threshold` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_when_within_threshold` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_silent_on_non_git_root` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWarnIfWorktreeStale::test_respects_configured_threshold` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_returns_default_when_frob_toml_absent` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_reads_configured_value` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_non_positive_value_falls_back_to_default` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestLoadPositiveIntConfig::test_malformed_toml_falls_back_to_default` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 2 error(s), 941 warning(s), 425 waived
- error-findings: INV006@src/frob/gates/_todo_fmt.py, TICK006@tickets.md
