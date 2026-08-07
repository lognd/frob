## Done report

`make coverage`/`make coverage-fast` both depend on `$(STAMP)` (`uv sync`),
which reconciles the venv against only the declared dependency set and
silently removes the editable `strata_core`/`frob_core` natives `make
core` installed. Both targets now run `make core` (restore) then
`uv run frob doctor` (verify, exit 1 with one clear line if a native is
still missing, e.g. no Rust toolchain) before pytest ever collects.
`coverage-fast`'s incremental (non-fallback) branch got the same guard
since it shares the `$(STAMP)` dependency and does not always route
through `coverage:`'s own guard.

Verified via `make -n coverage` / `make -n coverage-fast` dry-runs (no
recipe line executed) confirming `make core` then `frob doctor` precede
the pytest invocation in both targets, plus a real `uv run frob doctor`
run against the now-built natives. Did NOT run the full `make coverage`
cycle per playbook 6b.

### Changed
```
 Makefile                | 29 ++++++++++++++++++++++
 docs/modules/testing.md | 11 +++++++++
 tests/test_coverage.py  | 65 ++++++++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 104 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_target_restores_and_verifies_natives_before_pytest` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives` (pytest node id, verified passing when recorded)
