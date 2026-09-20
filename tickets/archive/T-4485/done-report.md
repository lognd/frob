## Done report

The PyPI project name strata-core is owned by someone else, so both
release runs on tag v0.531.0 that reached upload-strata-core could never
have succeeded even with a publisher registered. Owner decision
2026-09-15: publish the kernel as frob-strata.

Only the distribution name moved. The strata-core/ crate directory, the
Cargo package and lib names, and the strata_core import name are
unchanged, so every path-shaped mention and every `import strata_core`
stays as it was. What changed is every place that names the DISTRIBUTION:
the crate's [project].name, frob's three pin sites and its uv source key,
the release workflow's upload job and environment (pypi-frob-strata,
created on GitHub the same day with the kernel posture of no required
reviewer), the smoke preflight's required-wheel glob and Requires-Dist
reader, VERSION001's dependency table, the graph-cache fingerprint
package, the tests pinning those names, and the release/install docs.
uv.lock is land-owned and is regenerated at land time (measured in the
worktree: `uv lock` adds frob-strata and removes strata-core, 9 lines).

Measured in the worktree: uv build of strata-core/ produces
frob_strata-0.531.0-cp311-abi3-linux_aarch64.whl with METADATA
Name: frob-strata and the strata_core package inside; 220 unit tests
across the four renamed test modules pass; tests/system/test_artifact_smoke.py
passes against the renamed wheel; frob check --only release reports 0
errors (REL001/REL002/VERSION001 with the new pin name).

Not done here: the old pypi-strata-core GitHub environment is deleted
after this lands, and the owner registers the PyPI pending publisher for
frob-strata with environment pypi-frob-strata.

### Changed
```
 .github/workflows/ci.yml                   |  8 +++----
 .github/workflows/release.yml              | 18 +++++++-------
 README.md                                  |  2 +-
 docs/guides/install.md                     | 24 +++++++++----------
 docs/guides/release.md                     | 30 +++++++++++------------
 docs/modules/gates.md                      |  6 ++---
 pyproject.toml                             | 16 ++++++-------
 scripts/artifact_smoke.py                  | 16 ++++++-------
 src/frob/gates/_version_coupling.py        | 12 +++++-----
 src/frob/graph/cache.py                    |  8 +++----
 strata-core/pyproject.toml                 |  2 +-
 tests/system/test_artifact_smoke.py        | 10 ++++----
 tests/system/test_public_api_from_wheel.py |  4 ++--
 tests/test_graph.py                        |  4 ++--
 tests/unit/gates/test_version_coupling.py  | 12 +++++-----
 tests/unit/test_artifact_smoke_script.py   | 38 +++++++++++++++---------------
 tests/unit/test_release_workflow_gate.py   | 12 +++++-----
 tickets/T-4485/ticket.md                   | 14 ++++++++++-
 18 files changed, 124 insertions(+), 112 deletions(-)
```

### Evidence
- `tests/unit/test_artifact_smoke_script.py::TestReadCorePins::test_reads_both_pins_from_metadata` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate::test_matched_versions_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestUploadSplitPerDistribution::test_application_upload_needs_both_kernel_uploads` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 5021 warning(s), 970 waived
- error-findings: PRE001@tickets/T-4485
