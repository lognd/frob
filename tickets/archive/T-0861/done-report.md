## Done report

TEST016 send-back: frob ticket land refused because the previously bound
evidence killed 0 of 3 mutants introduced on this ticket's changed-line
spans in src/frob/__main__.py and src/frob/app/config.py (both files
picked up context/merge churn from this ticket's dup extractions):

- src/frob/__main__.py:2556 -- exc_info=True negated to exc_info=False in
  main()'s top-level exception handler.
- src/frob/app/config.py:1033 -- the Path division building the
  pyproject.toml path in _declared_frob_version swapped to another binop.
- src/frob/app/config.py:1042 -- the project-name inequality guard in
  _declared_frob_version swapped from != to ==.

All three are killed by tests that already exist in the repo but were not
bound as T-0861 evidence:
tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_logs_with_exc_info
asserts _log.error is called with exc_info=True (hand-verified: flipping
the literal to False makes the assertion fail).
tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
exercises _declared_frob_version through stale_install_warning: the Div
mutant raises TypeError building the path (hand-verified), and the NotEq
mutant makes repo_version resolve to None so the expected warning never
fires, failing the "warning is not None" assertion (hand-verified).

Both are now bound as T-0861 evidence; no source change was needed since
the mutants were already dead, just previously unbound.

### Changed
```
 design/frob.strata                         |   2 +-
 src/frob/app/check_runner.py               |   8 ++
 src/frob/app/debt_runner.py                |   5 +
 src/frob/app/deprecated_runner.py          |   3 +
 src/frob/app/sys_runner.py                 | 148 +++++++++++---------------
 src/frob/arch/_async_hazards.py            |   3 +
 src/frob/arch/_concurrency.py              |   3 +
 src/frob/arch/_concurrency_model.py        |   5 +
 src/frob/arch/_exceptions.py               |   2 +
 src/frob/arch/_kotlin.py                   |   5 +
 src/frob/arch/_lock_ordering.py            |   9 ++
 src/frob/arch/_mayraise.py                 |   2 +
 src/frob/arch/_python.py                   |   6 ++
 src/frob/arch/_rust.py                     |  11 ++
 src/frob/arch/_shared_state_race.py        |  13 +++
 src/frob/arch/_typescript.py               |  65 ++++++------
 src/frob/deploy/_generate.py               |   5 +
 src/frob/deploy/_generate_windows.py       |  16 +++
 src/frob/dup/_cache.py                     |   2 +
 src/frob/dup/_pipeline.py                  |   7 +-
 src/frob/dup/_rules.py                     |   4 +
 src/frob/gates/__init__.py                 |  52 ++++++----
 src/frob/gates/_cve_fingerprint_scan.py    |  33 +++---
 src/frob/gates/_design_invariants.py       |   2 +-
 src/frob/gates/_docblocks.py               |  20 ++--
 src/frob/gates/_docptr.py                  |   5 +
 src/frob/gates/_exclude_hazard.py          |   3 +
 src/frob/gates/_exhaustive_handling.py     |   3 +
 src/frob/gates/_opaque.py                  |   6 ++
 src/frob/gates/_parse_failures.py          |  32 ++++++
 src/frob/gates/_pii_structural.py          |  47 +++++----
 src/frob/gates/_registry_exhaustiveness.py |   9 ++
 src/frob/gates/_render_lint.py             |  64 ++++--------
 src/frob/gates/_secrets.py                 |   4 +
 src/frob/gates/_walk_lint.py               |  32 ++++--
 src/frob/graph/affects.py                  |  69 +++++++------
 src/frob/graph/callgraph.py                |  26 ++++-
 src/frob/graph/dsl.py                      |   7 ++
 src/frob/lang/_walk_kotlin.py              |   3 +
 src/frob/perf/_dup_spawn.py                |   4 +
 src/frob/perf/_loop_effects.py             |   7 ++
 src/frob/perf/_recursion.py                |   3 +
 src/frob/perf/_redundancy.py               |  17 ++-
 src/frob/perf/_sketch_store.py             |  20 ++--
 src/frob/process/parsers/common.py         |   7 ++
 src/frob/scaffold/_managed.py              |   5 +
 src/frob/strata/_access.py                 |   2 +
 src/frob/strata/_contention.py             |  16 +--
 src/frob/strata/_host.py                   |  23 ++++-
 src/frob/strata/_host_isolation.py         |  22 +---
 src/frob/strata/_krb_movement.py           |   5 +
 src/frob/strata/_reliability.py            |  17 +--
 src/frob/strata/_starvation.py             |   3 +
 src/frob/tickets/__init__.py               |  98 ++++++++----------
 src/frob/tomlio.py                         |  36 +++++++
 src/frob/vet/_capability.py                |   8 ++
 src/frob/vet/_scan.py                      |   5 +
 tickets.md                                 | 160 +++++++++++++++++++++++++++++
 58 files changed, 797 insertions(+), 402 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestRenderLintGate::test_render_package_exempt` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_skips_below_two_users` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_sketch_store.py::TestSketchStoreConfig::test_missing_frob_toml_returns_defaults` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestRglob::test_raw_rglob_fires` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSprintAssign::test_updates_sprint_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_logs_with_exc_info` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 12 error(s), 4303 warning(s), 384 waived
- error-findings: AFFECT001@design/frob.strata, AFFECT001@src/frob/gates/_design_invariants.py, AFFECT001@src/frob/gates/_parse_failures.py, AFFECT001@src/frob/gates/_walk_lint.py, AFFECT001@src/frob/graph/affects.py, AFFECT001@src/frob/graph/callgraph.py, AFFECT001@src/frob/strata/_contention.py, AFFECT001@src/frob/strata/_host.py, AFFECT001@src/frob/strata/_host_isolation.py, AFFECT001@src/frob/strata/_reliability.py, AFFECT001@src/frob/tomlio.py, INV006@src/frob/gates/_opaque.py
