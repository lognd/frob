## Done report

core-wheels now resolves maturin via uvx (same single mechanism frob natives build already uses), not uv run maturin which only sees project-declared deps; real BUG002 repro against 45e1ead3b; unit test suite green; declared fs.read capability + ratchet bump for the new test file (SELFAUDIT001/SYS111); DRIFT/REF/ruff-format errors remaining are pre-existing on main, unrelated to this diff

### Changed
```
 Makefile                                           | 19 ++++-
 design/frob.strata                                 |  2 +-
 .../registry/capability-via-ratchet.lock.json      |  6 +-
 tests/test_ci_workflow_core_wheels.py              | 91 ++++++++++++++++++++++
 tickets/T-4479/ticket.md                           | 28 +++++++
 5 files changed, 141 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_invokes_uvx_maturin` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_does_not_invoke_uv_run_maturin` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_does_not_invoke_bare_maturin` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_core_wheels.py::TestCoreWheelsResolvesMaturinViaUvx::test_recipe_still_rebuilds_target_wheels_per_crate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 4877 warning(s), 970 waived
- error-findings: DRIFT001@src/frob/doctor.py, PERF004@src/frob/tickets/_land.py, REF002@docs/design/macos-portability.md
