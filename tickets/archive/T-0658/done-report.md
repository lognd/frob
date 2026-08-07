## Done report

Added `tests/unit/strata/test_system_design_coverage.py`, the epic T-0331
close condition's own N:M coverage meta-test, binding
`docs/design/registry/system-design.yaml` (the system-design-corpus.md
denominator, 119 catalogued entries: 105 genuine + 14 manifest-extraction
artifacts) to a live disposition verdict, owned under this ticket's own
scope/test tree (distinct from T-0392's earlier `tests/
test_registry_reconciliation_system_design.py`, the one-time
reconciliation pass -- see the module docstring for why these are
separately owned, not merged).

Investigation first: `frob.registry.audit_registry_file` against the REAL
live file already reports `exhausted=True`, `unaccounted=0` (handled=21,
deferred=0, duplicate=1, out_of_scope=97, summing to 119) -- every one of
the 18 blocking obligation-family tickets (T-0640..T-0656) plus T-0392 and
T-0958 (a later dispositioning pass discovered while investigating, not
one of the 18 listed blockers) already drove this file to fully
dispositioned. T-0658's own job, given that, was to make this a STANDING,
epic-owned checkable claim rather than trust T-0392's now-somewhat-stale
reconciliation test (see the filed successor ticket below) -- and to
positively verify the epic's own obligation families (REL2xx/SYS2xx,
"systems-checks") are actually represented among the `handled_by`
dispositions, not just that SOME disposition exists.

Two test classes:
- TestSystemDesignCorpusCoverage: acceptance [0] ("every entry has a
  disposition... coverage total matches TOTAL") -- pins
  audit.exhausted/unaccounted/total against the live file, PLUS a new
  assertion T-0392's test never made: at least one `handled_by` target is
  itself a REL2xx/SYS2xx-family rule id (not just "some disposition
  exists" but "the epic's own obligation families are represented").
- TestSystemDesignGateLiveZero: acceptance [1] ("a future new entry with
  no disposition fails the build") -- verified by confirming the REAL
  `registry_gate` (wired into `frob check`'s default gate run) reports
  zero violations for `system-design.yaml` today, over the live ticket
  queue. The generic drift-lock MECHANISM itself (a fixture with an
  undispositioned/mismatched-total entry actually failing `registry_gate`)
  is already proven, over synthetic fixtures, by
  `tests/test_registry_exhaustiveness.py::TestDisposition::
  test_undispositioned_entry_fails` / `TestTotalDrift::
  test_total_mismatch_fails` -- not re-proven here, cited in the module
  docstring instead.

Out-of-scope finding, filed not fixed: `tests/
test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::
test_every_deferred_entry_targets_an_open_ticket` fails on a clean current
main, unrelated to this ticket's own scope (that test file is not in
T-0658's declared scope) -- it asserts `deferred` is non-empty, but the
live file now has ZERO deferred entries (T-0958 resolved them all into
handled_by/out_of_scope/duplicate, a strictly BETTER outcome than when
T-0392 wrote the test). Filed T-1032 for the reviewer to fix the
stale assertion.

Evidence: tests/unit/strata/test_system_design_coverage.py's 3 tests, all
independently re-run passing against the real file/gate/queue.

Gates: `frob check --ticket T-0658 --only gates-fast --only gates-native`
clean (0 errors both groups) after adding two `frob:waive DUP001`
waivers (this module's assertion shape is structurally similar to ~10
sibling per-domain reconciliation tests -- system-design.yaml/supply-
chain.yaml/evasion.yaml/weaknesses.yaml/... -- each independently owned
and pinning a DIFFERENT registry file's own live state; extracting a
shared helper across that many separately-scoped reconciliation tickets
is a real but distinct refactor, not this ticket's job, honestly
disclosed in both waiver reasons).

Filed: T-1032 -- fix stale
test_every_deferred_entry_targets_an_open_ticket in tests/
test_registry_reconciliation_system_design.py (a pre-existing, out-of-
scope failure found while investigating T-0658, unrelated to any change
made here).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 3118 warning(s), 347 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/agent-a81994cfb14c4292b/src/frob/strata/_host_isolation.py:290, E501@/home/logan/projects/frob/.claude/worktrees/agent-a81994cfb14c4292b/src/frob/strata/_host_isolation.py:331
