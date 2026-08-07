## Done report

The natives package now has a real integration-kind edge: a minimal synthetic pyo3 crate fixture driven through the actual build_natives code path (real maturin develop subprocess), with the built extension imported and called in a fresh subprocess. Measured ~7-8s total (warm cache), shipped as a slow-marked system test with a 180s timeout and clean cargo/uvx skip guards -- no waiver needed.

### Changed
```
 tests/system/test_natives_build_integration.py | 136 +++++++++++++++++++++++++
 tickets.md                                     |  80 ++++++++++++++-
 2 files changed, 215 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives` (pytest node id, verified passing when recorded)
- `tests/system/test_natives_build_integration.py::test_build_natives_compiles_and_imports_real_crate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
