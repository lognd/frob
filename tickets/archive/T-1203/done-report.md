## Done report

Built src/frob/strata/_mutation_audit.py (run_may_mutation_audit): for
every `may` atom on every node in every loaded `.strata` model, mutates
an in-memory copy two ways and proves detection:

- Deletion: proves SYS100 (core or extended) fires, computed at the
  kind level by reusing the SAME functions check_self_conformance calls
  (_declared_kinds/_stale_design_violations/_extended_kind_violations)
  against a single shared baseline scan, rather than a full repo-scan
  per atom (~100 atoms x repo scan would be prohibitive). Also checks
  the independent second detector: _export.py's node_allowed_syscalls
  (seccomp export), which joins the same Node.may tuple through a
  completely different table (_SECCOMP_KIND_MAP, keyed on the raw
  _may_kind spelling) -- a real second mechanism, not a second view of
  SYS100. Extended _SECCOMP_KIND_MAP with fs.read/fs.write (real
  syscall-backed kinds it was missing) and regenerated
  tests/golden/frob_export_seccomp.json.
- Substitution: proves the SYS100+SYS101 pair fires.
- Asserts baseline SYS101 count is zero (acceptance [2]) and reports
  every declared kind outside DETECTABLE_KINDS as an
  UndetectableCapabilityKind finding (acceptance [3]) rather than
  silently passing -- proc is confirmed reachable as the one currently-
  undeclared example.
- Deliberately pre-waiver: never calls _apply_sys_waivers, so an
  existing waive clause on the live design cannot mask a mutation
  finding here (acceptance [2]'s waiver-masking clause), structurally
  rather than via a special disabled-waivers mode.

REAL FINDING: today's export/seccomp mechanism only has genuine
OS-syscall coverage for exec/net/fs.read/fs.write. The 7 app-level
kinds actually declared in design/frob.strata (eval, env, ffi,
install-hook, sql, deserialize, fetch_url) have NO syscall analog --
faking syscalls for them would be dishonest. These are reported as
disclosed SecondDetectorGap findings, not silently claimed as
double-detected; MutationFinding.load_bearing only requires the export
diff where EXPORT_DETECTABLE_KINDS claims coverage. Filed T-1328
to build a real second detector for these kinds (e.g. a generated
capability-manifest artifact, mirroring the seccomp-export precedent
for app-level capabilities).

OUT-OF-SCOPE DISCOVERY: tests/unit/strata/test_selfconform.py's
TestRealGateGreen/TestCoverageTotality real-repo assertions fail on
main (pre-existing, unrelated to this diff) because src/frob/refactor/**
(landed by T-1197) has no code= binding in design/frob.strata (SYS102 +
4x SYS103). Filed T-1329 rather than fixing silently or
expanding this ticket's scope.

Also added interface= declarations for the new public symbols on the
stratamod/testsuite nodes (SYS104), a new docs/strata/selfconform.md
section documenting the mutation audit (COV001/AFFECT001), and
exported the new symbols from frob.strata's __init__.py.

### Changed
```
 design/frob.strata                       |   9 +
 docs/strata/selfconform.md               |  37 +++
 src/frob/strata/__init__.py              |  16 ++
 src/frob/strata/_export.py               |  33 +++
 src/frob/strata/_mutation_audit.py       | 439 +++++++++++++++++++++++++++++++
 tests/golden/frob_export_seccomp.json    | 185 +++++++++++++
 tests/unit/strata/test_mutation_audit.py | 103 ++++++++
 tickets.md                               | 153 ++++++++++-
 8 files changed, 970 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestDetectableKindsVocabulary::test_proc_family_is_currently_undetectable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
