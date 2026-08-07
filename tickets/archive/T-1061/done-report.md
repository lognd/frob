## Done report

check_mode_conformance (SYS205, T-0701/T-1060) had no production caller
and no waiver channel until this ticket -- the same disclosed cut
_access.py's own SYS204 module docstring names. T-1061 closes it on all
three fronts named in its title:

1. CLI dispatch: sys_runner.py's _run_audit now runs SYS205 alongside
   SYS100-103/SYS2xx/REL2xx via check_mode_conformance, printing a new
   _print_mode_conformance_report (PROVED/GAP summary, waived count
   carried inline, matching _print_contention_report's style); a SYS205
   finding now makes the whole audit exit nonzero.
2. frob check's SELFAUDIT001 gate: gates/__init__.py's
   _selfaudit_violations now folds SYS205 findings into the SAME wrapped
   Violation stream as the other four families.
3. Waiver channel: check_mode_conformance gained REAL waiver
   application (_apply_mode_conformance_waivers, mirroring
   _contention.py's _apply_contention_waivers pattern exactly).
   ModeConformanceReport gained a `waived` field. SYS205 joined
   _waive.py's MULTI_INSTANCE_WAIVER_FAMILIES (it can fire more than
   once per node, once per resource).

Shared plumbing both CLI/gate callers needed: _design_load.py's
DesignIds gained a `resources: tuple[ResourceDecl, ...]` field
(collected the same way store_ids already is, off each file's parsed
pre-elaboration Module.resources) so both callers can build the Module
argument check_mode_conformance needs to resolve a lock/arbitrated_by
arbiter, without re-parsing every design file a second time.

REAL REGRESSION FOUND AND FIXED DURING WIRING (not silently worked
around): wiring SYS205 live against frob's OWN design/frob.strata
surfaced a genuine new finding -- the five tickets_ledger write-mode
accessors (cli/gates/fleet/core/serve) declare no owns/acl path,
tripping the new no_declared_path category T-1060 built. Declaring a
synthetic owns="tickets.md" to discharge it was tried and REJECTED after
measuring the actual consequence: it creates 20 NEW SYS201 overlapping-
path findings across the five writers (verified directly with a throwaway
script calling check_resource_contention), since SYS201 has no
arbiter-awareness (unlike SYS203/T-1025). This is exactly why the
waiver-channel piece (#3 above) was added to this ticket's scope
mid-flight -- without it there was no clean way to land this at all.
Each of the five nodes now carries a
`waive "SYS205:tickets_ledger" reason="..." ticket "<successor>";` clause in
design/frob.strata with the full reasoning above.

Scope widened during the ticket (frob ticket scope --add, each with a
recorded reason): src/frob/gates/__init__.py (the SELFAUDIT001 site,
narrowed from the broader src/frob/gates/** already declared),
src/frob/strata/_design_load.py, tests/test_gates.py,
tests/system/test_cli_sys_audit.py, docs/commands/sys.md,
docs/modules/gates.md, docs/strata/surface.md, design/frob.strata,
src/frob/strata/_mode_conformance.py, src/frob/strata/_waive.py.

Tests (18 total in test_mode_conformance.py -- 17 pre-existing + 1 new
waiver test; 4 in TestSelfAuditGate -- 3 pre-existing + 1 new; 5 in
TestSysAuditCli -- 4 pre-existing + 1 new):
- test_a_waived_sys205_finding_is_discharged_and_reported_waived: a
  node-level waive "SYS205:<resource>" clause moves the matching finding
  from violations into waived.
- test_selfaudit001_folds_mode_conformance_violation: production
  sys_gate (not check_mode_conformance called directly) fires an
  unwaived SELFAUDIT001 naming the underlying SYS205 finding.
- test_mode_nonconformance_exits_nonzero_with_named_gap: production
  `frob sys audit` CLI exits nonzero with a named SYS205 gap.

A DEPR005 false positive was hit and waived (not fixed by removing the
call): the new test_cli_sys_audit.py test's `run("sys", "audit", ...)`
call tips this file's resolved reference count for tests.system.
conftest.run past its committed baseline -- but the resolver conflates
that bare name with three UNRELATED deprecated CLI functions
(xref_runner.run/outline_runner.run/map_runner.run) that this test never
calls, by name-only coincidence (the same resolver-precision class
PERF008 already discloses elsewhere in this repo). Waived with a full
explanation at the import site.

Gate verification (all foreground, chunked):
- uv run pytest (all four touched test files): 34 passed total.
- uv run frob check --ticket T-1061 --only gates-native: 0 errors (2
  pre-existing ARCH001 findings confirmed unrelated -- _close_cmd.py/
  doctor.py, untouched by this diff, from concurrent T-1126/T-1130
  lands).
- uv run frob check --ticket T-1061 --only gates-security: 0 errors (2
  pre-existing PII012 suggestions in tests/system/test_cli_doctor.py,
  untouched by this diff, confirmed from the same concurrent lands).
  SELFAUDIT001's own SYS205 fold is clean; a separate, confirmed
  pre-existing SYS100 finding (net.connect observed in
  src/frob/app/_daemon_proxy.py, from T-1126, unrelated to this ticket)
  surfaced once via SELFAUDIT001 during one intermediate check run but
  is NOT part of this ticket's own diff and is not fixed here (out of
  scope; disclosed).
- uv run frob check --ticket T-1061 --only static: 0 errors.
- uv run frob check --ticket T-1061 --only lint: 0 errors in this
  ticket's own files (ruff-format applied to _design_load.py/
  _mode_conformance.py/test_gates.py); remaining ruff-check/format
  findings are pre-existing in unrelated files.
- git diff main --diff-filter=D --stat: empty (required THREE merges of
  main during this ticket -- main advanced with T-1099/T-1125/T-1130/
  T-1126 lands mid-flight; natives rebuilt after each).

Filed: T-1149 ("strata: SYS201 gains arbiter-awareness (or a
first-class shared-path concept) so SYS205 WRITE path-scoping can
discharge without regressing SYS201") -- cite the REAL renumbered id
after landing (grep tickets.md). The five design/frob.strata
`waive "SYS205:tickets_ledger" ...` clauses' `ticket=` attribute points
at this successor, not T-1061, so T-1061 itself can close cleanly (T-1146,
the SYS203-wiring follow-up, was filed earlier during T-1025, not this
one).

### Changed
```
 design/frob.strata                         |  27 +++
 docs/commands/sys.md                       |   8 +
 docs/modules/gates.md                      |  14 +-
 docs/strata/host.md                        |  53 ++++++
 docs/strata/surface.md                     |  13 ++
 src/frob/app/sys_runner.py                 |  99 ++++++++--
 src/frob/gates/__init__.py                 |  42 ++++-
 src/frob/strata/_design_load.py            |  65 +++++--
 src/frob/strata/_mode_conformance.py       |  39 +++-
 src/frob/strata/_waive.py                  |   8 +
 tests/system/test_cli_sys_audit.py         |  27 +++
 tests/test_gates.py                        |  26 +++
 tests/unit/strata/test_mode_conformance.py |  31 +++-
 tickets.md                                 | 283 ++++++++++++++++++++++++++++-
 14 files changed, 693 insertions(+), 42 deletions(-)
```

### Evidence
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_a_waived_sys205_finding_is_discharged_and_reported_waived` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_mode_conformance_violation` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_mode_nonconformance_exits_nonzero_with_named_gap` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
