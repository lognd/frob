## Done report

Investigated T-1340's land commit (b614d46b) directly: `git show --stat`
confirms pyproject.toml/CHANGELOG.md/uv.lock changed but .frob-release.json
did not, matching the reported desync exactly.

Traced the bump path: `_apply_release_bump_for_land` (src/frob/app/
ticket_runner/_land_cmd.py, out of this ticket's declared scope) writes
pyproject.toml/CHANGELOG.md via `_write_release_bump`, then calls
`frob.release.stamp(...)` to write `.frob-release.json` -- but its own
return value is never checked. Downstream, inside this ticket's scope,
`_apply_release_bump`'s existing T-1078 safety net
(`_resync_release_manifest`) is ONLY invoked inside the `bumped.danger_ok
is not None` branch. Root cause could not be pinned to one single
mechanism with certainty from the historical commit alone (no log capture
survives from that land run), but the structural gap is real and
independently exploitable: any `bump_version` callback that reports
`Ok(None)` -- because it believes no bump is needed, or because it wrote
pyproject.toml itself without reporting the fact back through its return
value -- skips the manifest-resync safety net entirely, even if
pyproject.toml's on-disk version has already diverged from the manifest's.

Fix (in scope, src/frob/tickets/_land_release.py only): added
`_ensure_release_quartet_coherent`, an unconditional final coherence check
inside `_apply_release_bump` -- run regardless of which branch executed,
comparing pyproject.toml's on-disk version against `.frob-release.json`'s
on-disk version and force-resyncing the manifest whenever they disagree.
This closes the exact gap above as a structural guarantee ("the quartet is
coherent whenever `_apply_release_bump` returns Ok"), not a one-off patch
tied to a specific bump path. Split `_apply_reported_bump` out of
`_apply_release_bump` to keep the parent under ARCH001's 60-line threshold
after the addition.

Disclosed cut: the actual silent-failure site inside
`_apply_release_bump_for_land`'s unchecked `stamp(...)` call (src/frob/app/
ticket_runner/_land_cmd.py) is OUTSIDE this ticket's declared scope
(src/frob/tickets/_land_release.py only) and was not touched -- filing a
follow-up ticket for that call site's own return-value check, since the
new coherence guard is a safety net, not a substitute for fixing the
original silent-drop.

### Changed
```
 tickets.md | 70 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 68 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_reads_pyproject_version_from_disk` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_missing_pyproject_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_reads_manifest_version_from_disk` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_missing_manifest_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_malformed_manifest_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_already_coherent_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_diverged_versions_force_resync` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_missing_manifest_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_none_but_pyproject_already_diverged` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_new_version_normally` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 706 warning(s), 694 waived
- error-findings: none (measured, zero errors)
