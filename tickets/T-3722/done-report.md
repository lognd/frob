## Done report

warn_if_xdist_plugin_missing hardcoded the assumption that a repo's own pyproject.toml addopts sets -n auto unconditionally (its docstring said so explicitly). Added _addopts_sets_xdist(root) (src/frob/tickets/_worktree_guard.py), mirroring frob.testing._coverage_refresh's own addopts-read-and-tokenize pattern, and gated the warning on it actually finding an xdist token in the TARGET repo's real pyproject.toml addopts -- a consumer repo with a plain -q addopts no longer sees the warning. Updated docs/modules/tickets-data-storage.md's affected paragraphs to match. Evidence: 4 tests bound in tests/test_worktree_guard.py (TestAddoptsSetsXdist x3, TestWarnIfXdistPluginMissing::test_must_stay_quiet_when_addopts_has_no_xdist_token) -- full file 40/40 passed. Filed: none. Gates: frob check --ticket T-3722 clean except the pre-existing out-of-scope DEPR006 on frob-deprecated-baseline.lock.json (known, not this ticket's).

### Changed
```
 docs/modules/tickets-data-storage.md | 47 ++++++++++++------
 src/frob/tickets/_worktree_guard.py  | 95 +++++++++++++++++++++++++++++-------
 tests/test_worktree_guard.py         | 83 +++++++++++++++++++++++++++++--
 tickets/T-3722/ticket.md             | 21 +++++++-
 4 files changed, 208 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestAddoptsSetsXdist::test_true_when_dash_n_present` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAddoptsSetsXdist::test_false_when_addopts_has_no_xdist_token` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAddoptsSetsXdist::test_false_when_pyproject_unreadable` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_stay_quiet_when_addopts_has_no_xdist_token` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 4342 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
