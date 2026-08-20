## Done report

Changed: Makefile:476 install-tool recipe (`.[serve]` package spec replaces
the nonexistent `uv tool install --extra serve` flag); updated the stale
comment above it.

Evidence:
tests/unit/test_makefile_coverage.py::TestInstallToolUsesServeExtraPackageSpecNotUnsupportedFlag::test_install_tool_recipe_has_no_extra_flag
tests/unit/test_makefile_coverage.py::TestInstallToolUsesServeExtraPackageSpecNotUnsupportedFlag::test_install_tool_recipe_uses_serve_extra_package_spec

Also verified end to end (outside pytest, real install) in this worktree:
- `make install-tool` completes: "Installed 1 executable: frob"
- the installed tool env (`~/.local/share/uv/tools/frob/bin/python`)
  imports `mcp`, `strata_core`, and `frob_core` successfully -- proving
  the serve extra applied and both native packages installed.

Filed: none

Gates: manual fix, verified via the two checks above rather than
frob check/frob test (build tooling recipe, not gate-covered source).

### Changed
```
 Makefile                             |  6 +++---
 tests/unit/test_makefile_coverage.py | 20 ++++++++++++++++++++
 tickets/T-2708/done-report.md        | 32 ++++++++++++++++++++++++++++++++
 tickets/T-2708/ticket.md             | 26 ++++++++++++++++++++++++--
 4 files changed, 79 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestInstallToolUsesServeExtraPackageSpecNotUnsupportedFlag::test_install_tool_recipe_has_no_extra_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestInstallToolUsesServeExtraPackageSpecNotUnsupportedFlag::test_install_tool_recipe_uses_serve_extra_package_spec` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 39 error(s), 741 warning(s), 703 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DOC006@tickets/T-2703/ticket.md, DOC006@tickets/T-2704/ticket.md, DOC006@tickets/T-2705/ticket.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2708-series/src/frob/gates/_fix_engine.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2708, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
