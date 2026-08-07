## Done report

Bound invariants/INV-049.md (the closed-domain-import exclusivity claim
T-1337's docstrings assert but never anchored) to both
src/frob/app/app.py::_import_runner_module and
src/frob/app/__init__.py::_import_runner_run_module via a
frob:invariant INV-049 edge on each. This is the fix committed earlier
in this worktree under T-1276 (commit 4d2c5001) and split out here so it
can land independently of T-1276's unverifiable TEST005 acceptance.

Evidence: two existing, already-passing tests, neither new, both already
proving the exclusivity property directly:
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
  -- clears sys.modules of every frob.app.*_runner entry, resolves one
  subcommand via _resolve_runner/_import_runner_module, asserts only
  that subcommand's own runner module is present in sys.modules
  afterward.
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
  -- a clean-interpreter subprocess check that accessing one
  frob.app.<name>_run attribute (via __getattr__/_import_runner_run_module)
  never imports an unrelated runner module.

Verified UNSCOPED (no --only, no --ticket) per instruction: a foreground
check with a full timeout wrapper reports gate:INV at 0 errors -- both
INV006 findings on app.py and __init__.py are gone. The run's other
FAILs are pre-existing/unrelated to this ticket's scope
(src/frob/app/app.py, src/frob/app/__init__.py, invariants/INV-049.md):
gate:TICK TICK003 (76 unarchived closed tickets, pre-existing debt),
gate:PRE/gate:SCOPE PRE001/SCOPE001 (both say "no active ticket is
derivable" -- an artifact of running fully unscoped with no --ticket/
branch, exactly as instructed, not a regression), gate:COV COV002 and
the one unwaived gate:PII PII012 hit both point at
tests/unit/test_doctor_runner_t1276.py and design/frob.strata, which
belong to T-1276's own separate, still-open scope, not this ticket's.

### Changed
```
 design/frob.strata                     |   2 +
 invariants/INV-049.md                  |  31 +++++
 src/frob/app/__init__.py               |   2 +
 src/frob/app/app.py                    |   2 +
 src/frob/app/doctor_runner.py          |   6 +
 tests/unit/test_doctor_runner_t1276.py | 148 ++++++++++++++++++++
 tickets.md                             | 237 ++++++++++++++++++++++++++++++++-
 7 files changed, 422 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 1301 warning(s), 688 waived
- error-findings: PII012@tests/unit/test_doctor_runner_t1276.py, TICK003@tickets.md
