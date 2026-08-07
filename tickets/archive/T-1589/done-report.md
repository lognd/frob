## Done report

Four real self-model tests fixed, all "code observed, declaration structurally
redundant/stale":

1. test_mutation_audit::test_every_may_is_load_bearing -- cli node
   declared BOTH a bare "env" may (covering several files) AND a narrower
   "env.read via _land_cmd.py" atom; testsuite node declared BOTH a bare
   "net" may AND a narrower "net.connect via test_sync_may.py" atom.
   canonical_declared_kind/expand_declared_kind confirmed the bare kind's
   expansion is a strict superset of the narrow one ("env" -> {env.read,
   env.write}, "net" -> {net.connect, net.listen}) -- deleting the narrow
   atom leaves the node's overall declared-kind set unchanged (the bare
   atom already covers it), so the mutation audit's node-level SYS100
   join never fires on its deletion; it was never load-bearing. Folded
   both narrow atoms into their sibling bare declaration's `via` list
   (design/frob.strata) instead of keeping a structurally-redundant
   second atom -- the code is still correctly attributed (land_parity_
   findings' os.environ read, test_sync_may.py's fixture-embedded
   requests.get( needle), just via the declaration that is actually
   load-bearing.

2. test_mutation_audit::test_second_detector_gaps_are_exactly_the_
   disclosed_app_level_kinds -- 'process-control' (testsuite node,
   T-1439's signal.signal(/sys.exit reclassification out of bare 'env')
   has no _SECCOMP_KIND_MAP entry (no dedicated syscall of its own,
   same shape as env/env.read already disclosed) and was missing from
   the test's disclosed set. Added it with the same reasoning pattern
   the existing env.read docstring uses. (The prior extra 'net.connect'
   gap in this same assertion was resolved as a side effect of fix #1
   above -- once the narrow net.connect atom no longer exists as a
   standalone declaration, it no longer appears as its own second-
   detector-gap entry.)

3. test_threat::test_every_shipped_entry_has_a_substantive_caught_by --
   a stale exhaustiveness-lock count (15) hadn't been bumped when
   T-1439's process-control BenignCapability entry was added to
   DEFAULT_BENIGN_CAPABILITIES (now 16 entries); the entry's own
   caught_by text was already substantive, not a placeholder -- only the
   count assertion and its explanatory comment needed updating.

4. test_export_golden::test_k8s and ::test_seccomp -- both goldens
   (tests/golden/frob_export_k8s.yaml, tests/golden/frob_export_seccomp.json)
   predated design/frob.strata's `security` node (src/frob/security/**,
   zero `may` capabilities). Confirmed via a direct diff before
   regenerating: the only change in both is a new, empty-capability
   NetworkPolicy/seccomp block for that one node (no egress, default-
   deny syscalls) -- a genuine addition, not exporter-logic drift.
   Re-derived both goldens from the current design/frob.strata via
   export_k8s_netpol/export_seccomp.

Verification: targeted pytest runs for every failing test/file (all now
pass), the full tests/unit/strata/ directory (139 passed), design/frob.strata
still parses (`frob.lang.parse_file`), `frob sys sync-interface` reports no
drift, `frob check --only test --only invariant --only sys --only decisions
--ticket T-1589` (0 errors). Did not run the full unscoped suite (playbook
3b/3c budget) -- that is T-1591's job and the coordinator's land-time job.

### Changed
```
 docs/design/registry/check-coverage.yaml          |  6 +-
 docs/guides/extending/registry_of_registries.json |  2 +-
 src/frob/__init__.py                              |  4 ++
 src/frob/gates/_fix_engine.py                     |  1 +
 src/frob/gates/_rule_id_scan.py                   | 13 +++-
 src/frob/gates/_waive.py                          |  6 ++
 tests/unit/test_extending_guides_complete.py      |  2 +-
 tickets.md                                        | 84 ++++++++++++++++++++++-
 8 files changed, 111 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 2025 warning(s), 787 waived
- error-findings: none (measured, zero errors)
