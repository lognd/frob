## Done report

Built the reflexive check-coverage registry as a tenth `docs/design/registry/
*.yaml` instance (`check-coverage.yaml`), added to `frob.gates
._registry_exhaustiveness.REGISTRY_FILES` -- T-0407's unification made adding
a new registry mean exactly this, a filename, not a second mechanism. The
same REG001-REG007 exhaustiveness gate now enforces it.

Seeded honestly from two real sources named in the ticket:
- `gate_rule_entries` -- one entry per id `frob.gates.known_gate_rule_ids()`
  reports LIVE (82 entries at time of writing), each self-referentially
  `handled_by:<that same rule id>`. Verified programmatically (see
  `TestCheckCoverageRegistryFile.test_gate_rule_entries_match_live_known_rules`)
  that every one of these targets is actually in the live rule set, not a
  frozen snapshot that could silently drift from reality.
- `concern_family_entries` -- the `docs/audits/` 7-auditor pessimistic pass
  (2026-07-20) concern families: 5 cross-cutting themes + 8 per-subsystem
  verdicts (docs/audits/README.md), 13 entries total, each `deferred:T-0397`
  (the real, open audit-remediation epic that already tracks these findings'
  per-HIGH-finding children).

`frob registry audit` confirms `check-coverage.yaml` reports
`total=95 handled=82 deferred=13 duplicate=0 out_of_scope=0 unaccounted=0
malformed=0 [EXHAUSTED]` against the live build.

Cut, disclosed honestly (acceptance item 2, "the pessimistic-auditor loop
runs on a schedule and its findings auto-file as dispositioned entries"):
NOT built in this pass. Wiring a recurring scheduled auditor loop that
auto-appends new `concern_family_entries` rows is a real scheduling/
automation feature (a cron-like driver plus an auditor-output-to-YAML
writer), a materially different and larger unit of work than the registry
model itself, and doing it properly needs its own ticket rather than a
rushed bolt-on here. Not Filed: T-draft-6060f333 (never refiled) (new ticket, scope
docs/design/registry/+src/frob/, "schedule the pessimistic-auditor loop
to auto-file new concern_family_entries rows in check-coverage.yaml").

At granularity: this seeds concern FAMILIES (the docs/audits/ verdict/theme
level), not every individual numbered finding (B1-B15 etc per audit file,
~100+ atomic items) -- the ticket's own text says "concern families", and
mapping every atomic finding to a specific already-existing or new child
ticket under T-0397 is real per-item triage work belonging to T-0397's own
children, not manufactured here. As those children close a concern down to
a real gate rule, its `concern_family_entries` disposition moves from
`deferred:T-0397` to `handled_by:<new rule id>`, and the registry's own
REG002 requires that rule id to actually exist and fire.

### Changed
```
 .frob-release.json                          |  13 +-
 CHANGELOG.md                                |  20 ++
 docs/design/registry/EXHAUSTIVENESS-GATE.md |  33 +++
 pyproject.toml                              |   2 +-
 src/frob/__main__.py                        |  17 ++
 src/frob/app/app.py                         |   2 +
 src/frob/app/config.py                      |  10 +
 src/frob/app/registry_runner.py             |  74 ++++++
 src/frob/gates/__init__.py                  |   4 +
 src/frob/gates/_registry_exhaustiveness.py  | 358 +++++++++++++++-------------
 src/frob/registry/__init__.py               |  38 +++
 src/frob/registry/_models.py                | 326 +++++++++++++++++++++++++
 tests/test_registry_exhaustiveness.py       | 160 ++++++++++++-
 tests/test_registry_models.py               | 193 +++++++++++++++
 tickets.md                                  | 118 ++++++++-
 uv.lock                                     |   2 +-
 16 files changed, 1198 insertions(+), 172 deletions(-)
```

### Evidence
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_is_in_registry_files` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_loads_without_error` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_concern_family_entries_are_deferred_or_handled` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_no_malformed_entries` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_audit_reports_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations` (pytest node id, verified passing when recorded)
