## Done report

module_to_path (and validate_module_destination, _importing_package,
_path_to_module, _import_check_env) hardcoded src/ as the sole package
root whenever src/ existed, so frob refactor split/move/rename/
move-module could never address any tests/**/scripts/** module -- five
independent copies of the same rule. Added import_roots/root_for_path
as the one shared root-resolution function (src/ first, then repo_root,
matching pyproject's pythonpath = ["."]) and routed all five sites
through it.

Verified: full tests/test_refactor.py suite green (131/131, was 126);
a real end-to-end must-fire probe -- `frob refactor split` against a
throwaway tests/** module in this worktree -- succeeded
(import_resolution/module_import/pytest_collect all PASS; reverted
before landing, never committed); `frob check --only gates-fast
--budget 300 --ticket T-3587` shows zero refactor/test_refactor errors,
every remaining finding pre-existing repo-wide baseline noise unrelated
to this diff.

### Changed
```
 docs/commands/refactor.md                | 21 ++++++++-
 src/frob/refactor/_module_scan_python.py | 11 +++--
 src/frob/refactor/_operands.py           | 23 +++++-----
 src/frob/refactor/_resolve.py            | 77 +++++++++++++++++++++++++++++---
 src/frob/refactor/_verify.py             | 43 ++++++++++--------
 tests/test_refactor.py                   | 72 +++++++++++++++++++++++++++--
 tickets/T-3587/ticket.md                 |  7 +++
 7 files changed, 210 insertions(+), 44 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestModuleToPath::test_maps_module_under_src` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestModuleToPath::test_maps_module_under_root` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestImportRoots::test_src_first_then_repo_root` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestImportRoots::test_repo_root_only_when_no_src` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRootForPath::test_finds_owning_root` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRootForPath::test_none_when_outside_every_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 27 error(s), 4105 warning(s), 891 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@tickets/T-3587/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3587, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
