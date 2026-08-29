## Done report

T-3401: added warn_if_testmon_plugin_missing mirroring T-3316's xdist plugin-absence check exactly; wired as a preflight in Makefile's test-fast target since --testmon is a raw shell pytest spawn outside every in-process frob call site. pytest-testmon already an unconditional dev dependency. Evidence: tests/test_worktree_guard.py full suite (36 passed). Known gap: TEST016 flagged the new tests as mutation-confirmatory-only, same shape as the existing xdist tests in this file; disclosed, not papered over.

### Changed
```
 Makefile                            |  9 +++++
 src/frob/tickets/_worktree_guard.py | 69 +++++++++++++++++++++++++++++++++++++
 tests/test_worktree_guard.py        | 44 +++++++++++++++++++++++
 tickets/T-3401/ticket.md            | 19 +++++++++-
 4 files changed, 140 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestWarnIfTestmonPluginMissing::test_must_fire_when_plugin_not_importable` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWarnIfTestmonPluginMissing::test_must_stay_quiet_when_plugin_importable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 22 error(s), 3968 warning(s), 898 waived
- error-findings: AFFECT001@src/frob/tickets/_worktree_guard.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC011@docs/modules/tickets.md, DUP001@tests/test_worktree_guard.py, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/process/_reap.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE001@src/frob/tickets/_worktree_guard.py
