## Done report

EXHAUST drain: gate:EXHAUST from 28 unwaived warnings to 0 errors, 0
warnings, 114 waived. All dispositions genuine: frob:waive
EXHAUST002/EXHAUST003 with real reasons on resolver-coverage-gap false
positives (stdlib/cross-module calls the static resolver cannot see,
dict.get chains that cannot raise KeyError), matching the T-1062/T-1402
prose convention -- except src/frob/graph/cache.py::_with_lock_retry,
which got a real frob:raises CacheLocked declaration since it genuinely
raises it.

Also repaired the warm-up merge's ledger resurrection (38 archived ids)
per playbook 10b and root-caused it: the git merge-driver registration
invokes BARE frob (stale 0.184.0, predating the T-1437 splice fix);
follow-up draft filed for routing the documented registration through
uv run frob. The coordinator fixed this clone's git config, and this
branch's final resync merge of main (post-T-1442) spliced cleanly under
the corrected driver -- the first live confirmation of the fix.

### Changed
```
 design/frob.strata                            |   1 +
 src/frob/app/_daemon_proxy.py                 |  14 ++
 src/frob/gates/_coverage.py                   |  90 ++++++++++--
 src/frob/gates/_debt_deprecated.py            |  32 ++++-
 src/frob/gates/_deprecated_baseline.py        |   5 +
 src/frob/gates/_docblocks.py                  |   5 +
 src/frob/gates/_docblocks_refs.py             |  11 ++
 src/frob/gates/_docptr.py                     |  22 +++
 src/frob/gates/_ffi_boundary.py               |  40 +++++-
 src/frob/gates/_fix_engine.py                 | 109 +++++++++++----
 src/frob/gates/_inv006_split_assist.py        |  18 ++-
 src/frob/gates/_pii_structural/_keywords.py   |   7 +
 src/frob/gates/_prework.py                    |  41 ++++--
 src/frob/gates/_protocol_summary.py           |  10 +-
 src/frob/gates/_ratchet.py                    |  16 ++-
 src/frob/gates/_registry_exhaustiveness.py    |   5 +
 src/frob/gates/_secrets.py                    |  18 ++-
 src/frob/gates/_suppress.py                   |  31 ++++-
 src/frob/gates/_walk_lint.py                  |  14 +-
 src/frob/gates/_wire.py                       |  37 +++++
 src/frob/graph/cache.py                       |   1 +
 src/frob/perf/_collectors.py                  |   8 ++
 src/frob/perf/_heat.py                        |   5 +
 src/frob/perf/_redundancy.py                  |  23 +++-
 src/frob/perf/_rules.py                       |  13 +-
 src/frob/perf/_serial_pools.py                |  10 ++
 src/frob/refactor/_scan.py                    |  73 ++++++----
 src/frob/refactor/_verify.py                  |  39 ++++--
 src/frob/testing/_collect.py                  |   6 +
 src/frob/tickets/_accept.py                   |   3 +
 src/frob/tickets/_land_git_ops.py             |  15 ++
 src/frob/tickets/_land_release.py             |  17 ++-
 src/frob/tickets/_leases.py                   | 150 ++++++++++++--------
 src/frob/tickets/_mutation_evidence.py        |   8 +-
 src/frob/tickets/_new_gate_rule_acceptance.py |  12 +-
 src/frob/tickets/_new_renumber.py             |  42 ++++--
 src/frob/tickets/_scope.py                    |   5 +
 src/frob/tickets/_setters.py                  |  41 ++++--
 src/frob/tickets/_store.py                    |  34 ++++-
 src/frob/tickets/clipboard.py                 |   5 +
 src/frob/vet/_capability.py                   |  46 +++++--
 src/frob/vet/_closedworld.py                  |  19 +++
 src/frob/vet/_cve.py                          |   6 +
 src/frob/vet/_scan.py                         |  13 ++
 src/frob/vet/_taint.py                        |   9 +-
 tests/test_gates.py                           |  64 +++++++++
 tickets.md                                    | 188 +++++++++++++++++++++++++-
 47 files changed, 1154 insertions(+), 227 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live` (pytest node id, verified passing when recorded)
- `tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_different_version_is_skew_not_live` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestSuppress001StringLiteralSafety::test_hash_suppression_inside_string_literal_is_not_a_comment` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_hash_inside_string_literal_is_not_treated_as_comment` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeTimeout::test_slow_package_returns_within_timeout_not_task_duration` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCoverageLockConflictMerges::test_conflicting_lock_merges_to_the_higher_of_both_sides` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_kwonly_param_never_passed_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_kwonly_param_passed_at_call_site_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 1 error(s), 7092 warning(s), 740 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w2-exhaust/src/frob/strata/_threat_catalog_cwe.py:9
