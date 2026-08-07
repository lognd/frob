## Done report

T-0570 computed per-run sha256 fingerprints and validated format
(SQLite magic header, json.loads) but never persisted them, so content
DRIFT between two frob doctor runs (an artifact silently rewritten by a
stale tool or a foreign process, still valid bytes, just different
content) was undetectable -- only malformed bytes were caught. This
ticket adds the missing persistence half: a manifest file under
.frob/derived-state-manifest.json storing {artifact name: fingerprint},
written after every run_diagnosis call, compared against on the NEXT
call.

Design decision: manifest location and format. .frob/derived-state-
manifest.json, plain JSON, keyed by artifact name (not path, matching
DERIVED_ARTIFACTS' own key). This lives under .frob/, the same
gitignored derived-cache directory every other entry in
DERIVED_ARTIFACTS lives under -- never a tracked file. It is
deliberately excluded from DERIVED_ARTIFACTS itself (a manifest
fingerprinting its own drift would be circular) and best-effort on both
read and write: a missing or malformed manifest degrades to "no prior
run to compare against" (empty dict) rather than raising, and a write
failure is logged and swallowed rather than raised -- the manifest is
disposable bookkeeping, not a source of truth worth failing the whole
diagnosis over.

Design decision: drift is informational, not a hard failure. Unlike
T-0603's corrupt-artifact block (which DOES fail closed), a fingerprint
mismatch between two doctor runs does NOT flip DoctorReport.healthy to
False. Reasoning: frob's own tools legitimately rewrite these same
caches during ordinary use between two frob doctor invocations --
running frob check updates .frob/cache.db, frob dup updates
.frob/dup.db, etc. Treating every such expected rewrite as a failure
would make a session's second frob doctor call cry wolf on completely
normal churn, which is a worse failure mode than the drift-blindness
this ticket is fixing. detect_derived_state_drift's docstring documents
this explicitly.

Round-1 review REJECT and the fix applied this round: the reviewer found
that DerivedArtifactDrift and detect_derived_state_drift's frob:doc
edges pointed at docs/guides/install.md#derived-state-integrity-manifest-t-0570,
but that section was never touched by the round-1 diff -- it still
described only T-0570's reporting-only behavior, said nothing about
DoctorReport.drift or either new symbol, and still called the
enforcement block "out of this ticket's scope, see the Done report for
the follow-up" even though that follow-up (T-0603) has since landed in
this same worktree. The anchor mechanically resolved (satisfying gate:DOC)
while the prose behind it was stale and, after T-0603 landed, actively
wrong. Fixed this round: scope widened to docs/guides/install.md (frob
ticket scope --add, same reason pattern T-0603 used for
docs/modules/gates.md); the T-0570 paragraph now says the block landed as
T-0603 and cross-references docs/modules/gates.md's DERIVED001 section;
a new "Cross-run content drift (T-0604)" subsection documents
DoctorReport.drift, DerivedArtifactDrift, detect_derived_state_drift, and
the informational-only rationale, with its own frob:describes anchor for
detect_derived_state_drift.

What changed (round 2, on top of round 1):
- docs/guides/install.md: corrected the stale "out of scope" sentence in
  the existing T-0570 section to point at T-0603/DERIVED001 as landed;
  added a "Cross-run content drift (T-0604)" subsection under the same
  H2 covering the new symbols and design rationale.
- tickets.md: scope extended to include docs/guides/install.md.

What changed (round 1, unchanged this round):
- src/frob/doctor.py: new DerivedArtifactDrift model; _load_drift_manifest
  / _write_drift_manifest private helpers (best-effort load/persist);
  new public detect_derived_state_drift(root, current) function; new
  DoctorReport.drift field; run_diagnosis now calls
  detect_derived_state_drift before writing the fresh manifest for the
  next run. Module docstring updated with the T-0604 paragraph.
- tests/system/test_cli_doctor.py: new TestDoctorDerivedStateDrift class
  covering first-run (no prior manifest -> no drift, manifest written),
  a rewritten artifact between two runs (drift reported with both
  fingerprints -- the acceptance case), drift not affecting healthy, an
  unchanged artifact reporting no drift, and a malformed manifest
  degrading to "no prior run" rather than crashing.

Mutant kill (hand-verified, T-0604, round 1, still valid -- no logic
changed this round): temporarily replaced detect_derived_state_drift's
mismatch condition (prev_fingerprint is not None and prev_fingerprint !=
d.fingerprint) with False and reran tests/system/test_cli_doctor.py -k
TestDoctorDerivedStateDrift -- test_rewritten_artifact_between_two_runs_reports_drift
and test_drift_is_informational_and_does_not_affect_healthy both failed
(asserting drift != [] against an actual [] drift list), confirming the
tests actually exercise the comparison logic. Restored the real
implementation afterward and reran green (18 passed).

Evidence executed and observed:
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_rewritten_artifact_between_two_runs_reports_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_drift_is_informational_and_does_not_affect_healthy
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_unchanged_artifact_reports_no_drift
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_malformed_manifest_is_treated_as_no_prior_run
- Full file re-run after the doc fix: uv run pytest tests/system/test_cli_doctor.py
  -q -o addopts="" -> 18 passed (doc-only change, no source touched this
  round, confirmed unaffected)

Gates (re-run after the doc fix): frob check --only lint/static/gates-fast
--ticket T-0604 clean, including gate:DOC (0 errors, 2 warnings) and
gate:DRIFT (0 errors, 0 warnings, 2 waived) specifically. One disclosed,
unresolved COV002 finding on tests/unit/test_check.py (outside T-0604's
scope, T-0603's own test file) persists because T-0603 closed earlier in
this same worktree/branch, so its frob:ticket T-0603 edge no longer
points to an "open" ticket relative to this check's base=main comparison
-- a serial-chain artifact of doing two tickets in one worktree before
landing, not caused by any T-0604 change, and it self-resolves once both
tickets land on real main. git diff main --diff-filter=D --stat is empty.

Deviations: none in outcome beyond the round-1-to-round-2 scope widening
described above, which was explicitly directed by the review finding.

Filed: none (no new out-of-scope discoveries this round; the coordinator
is separately filing the TOCTOU residual noted on T-0603, unrelated to
this ticket).

### Changed
```
 docs/guides/install.md          |  51 +++++-
 docs/modules/gates.md           |  45 ++++++
 src/frob/check/__init__.py      |  90 +++++++++++
 src/frob/check/_python.py       |  10 ++
 src/frob/doctor.py              | 165 ++++++++++++++++++-
 tests/system/test_cli_doctor.py | 106 +++++++++++++
 tests/unit/test_check.py        |  51 ++++++
 tickets.md                      | 341 +++++++++++++++++++++++++++++++++++++++-
 8 files changed, 841 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_first_run_reports_no_drift_and_writes_manifest` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_rewritten_artifact_between_two_runs_reports_drift` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_drift_is_informational_and_does_not_affect_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_unchanged_artifact_reports_no_drift` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateDrift::test_malformed_manifest_is_treated_as_no_prior_run` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 980 warning(s), 220 waived
- error-findings: none (measured, zero errors)
