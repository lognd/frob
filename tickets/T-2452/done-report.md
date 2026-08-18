## Done report

Changed:
- src/frob/__main__.py::_dispatch (routing body only, now ~26 lines)
- src/frob/__main__.py::_dispatch_bind (new)
- src/frob/__main__.py::_dispatch_quality_bind (new)
- src/frob/__main__.py::_dispatch_agent (new)
- src/frob/__main__.py::_dispatch_worktree (new)
- src/frob/__main__.py::_dispatch_sync_skills (new)
- src/frob/__main__.py::_dispatch_release_publish (new)
- src/frob/__main__.py::_dispatch_refactor (new)
- src/frob/__main__.py::_dispatch_default (new)

`_dispatch` was 81+ lines on main, over ARCH001's 60-line threshold
(flagged by the T-2452 waive comment previously on the function).
Split each argv-routing special case (bind, quality bind, agent,
worktree, sync-skills, release publish, refactor, default) into its own
small `_dispatch_*` helper, mirroring the existing
`_is_quality_bind`/`_is_release_publish` extraction pattern already used
for two of these special cases. `_dispatch` itself is now a pure
if/elif routing table (~26 lines) that calls exactly one helper per
branch; removed the now-obsolete ARCH001 waive comment on `_dispatch`.

argv-slicing behavior preserved exactly: `_dispatch_bind` receives the
already-`bind`-stripped argv and forwards it unsliced to `bind_runner.
run`; `_dispatch_quality_bind` strips the leading `quality` token then
delegates to `_dispatch_bind` (net: same `argv[2:]` `bind_runner.run`
received before); `_dispatch_agent`/`_dispatch_worktree`/
`_dispatch_sync_skills` each receive pre-stripped argv and forward it
unsliced; `_dispatch_release_publish`/`_dispatch_refactor` receive the
FULL unsliced argv (their own dedicated parsers expect the leading verb
token), matching the original inline branches exactly.

Re-measured unscoped after the split (T-2452's own instruction: a
refactor invalidates doc/test/waiver edges outside declared scope):
`frob check --only archgate --only ruff --only ty` (repo-wide, no
--ticket) shows ZERO findings anywhere in src/frob/__main__.py -- no new
ARCH/ruff/ty finding was introduced by the split. `frob check --ticket
T-2452 --only ty` (scoped) also passes clean, 0 issues.

Evidence:
- tests/unit/test_main_entry.py (full file, 31 tests, all pass --
  covers `_dispatch`'s external behavior for every special-cased verb:
  bind, agent, refactor, sigint, sigterm-reaper install, quality bind
  via `_is_quality_bind`)
- tests/test_release.py -k "publish or Dispatch" (7 tests pass --
  covers `frob release publish` dispatch through the new
  `_dispatch_release_publish` helper)
- tests/unit/test_skills_sync.py (15 tests pass -- covers `frob
  sync-skills` dispatch through the new `_dispatch_sync_skills` helper)

Filed: none

Gates: frob check --ticket T-2452 --only scope --only prework --only
affect_drift --only fmt clean after re-running the pre-work sweep
(PRE001 was stale from the base-main merge, fixed via `frob ticket sweep
T-2452`). Remaining SCOPE002 warnings are pre-existing (unrelated
symbols in __main__.py whose docs already lived outside this file before
this ticket touched it) -- not introduced by this diff.

### Changed
```
 tickets/T-2452/ticket.md | 9 ++++++++-
 1 file changed, 8 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestRefactorDispatch::test_refactor_subcommand_dispatches_to_run_refactor_command` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV005@src/frob/__main__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md


frob:no-behavior-change reason="This is a structural refactor (ARCH001 line-count split of _dispatch) with no intended runtime behavior change -- argv routing, verb dispatch, and every special-case's argv slicing are preserved exactly (verified: all 31 tests in tests/unit/test_main_entry.py plus the release-publish and sync-skills dispatch test files pass unchanged after the split). The designated evidence genuinely passes at both the parent commit and the fix, which is the expected/correct shape for a pure refactor, not a confirmatory-only defect repro. "
