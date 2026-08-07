## Done report

T-1056 closes a coherent partial slice of the EXHAUST001/002 residual
burn-down: the entire src/frob/gates/__init__.py concentration (16 of 176
sites), the largest single file in the ticket's per-file breakdown.

Two functions got real errors-as-values refactors matching the T-1022
precedent, both verified to reduce the leaked exception set rather than
just muting it:

- _has_assertion_evidence: the ast.walk loop over a parsed test module is
  now wrapped in a fail-open try/except Exception, matching the function's
  own documented "fails OPEN whenever the check cannot be performed"
  contract. This closed both its EXHAUST001 (Unknown) and EXHAUST002
  (KeyError) findings for real.
- _ceiling_ok: the metric<=ceiling comparison is now wrapped in try/except
  TypeError, fail-opening to "still waived" the same way its existing
  ValueError branch already does for a malformed ceiling attribute. This
  closed its EXHAUST002 (TypeError) finding for real; its residual
  EXHAUST001 (Unknown, traced to plain dict.get access) got a reasoned
  waiver alongside the new catch (no follow-up ticket needed: already
  fully disposed via the waiver, not a deferred cut).

The remaining 11 sites across decisions_gate, _tick005_merge_state_
regression, _tick010_stale_lease_report (both codes), compliance_gate,
_claims_markers_in_file, _pyproject_project_field, _changelog_mentions,
_uv_lock_version, _crawl_reachable, _doc_anchor_slugs, and
_pyproject_version_at each got a reasoned frob:waive EXHAUST001/EXHAUST002,
verified against the actual body of each function: every one already
degrades via an existing narrow except/Result check, and the leaked
Unknown/named type traces to either (a) a function-local deferred import
the resolver cannot follow through, (b) a Result-returning helper
(gitio.run_argv) whose own fallibility is already checked via .is_err, or
(c) a plain dict/regex/path-string operation on data already produced by
an upstream try/except (tomllib.load, read_text) -- none of these has a
real unhandled raise path; several are outright resolver false positives
(_tick010_stale_lease_report's EXHAUST002 is json.JSONDecodeError, a
ValueError subclass already caught by `except (OSError, ValueError)` --
the resolver does not do subclass reasoning against a caught tuple).

Verified: `frob check --only exhaustive_handling` shows 0 active (non-
waived) EXHAUST001/002 diagnostics left in src/frob/gates/__init__.py
(0/16), gate-wide active count dropped 183 -> 167, and gate:TEST/gate:COV
both stay clean (no new obligations from the two small code changes).

Disclosed residue (follow-up filed and landed as T-1062): the ticket's remaining ~150 sites across ~39 other
files (gates/_coverage.py 8, dup/_pipeline.py 6, tickets/_leases.py 6,
deploy/_conform.py 5, mutate/__init__.py 5, outline/__init__.py 5,
strata/_claims.py 5, tickets/__init__.py 5, app/check_runner.py 4,
check/_python.py 4, gates/_docptr.py 4, gates/_secrets.py 4,
mutate/_journal.py 4, strata/_host_isolation.py 4,
strata/_native_staleness.py 4, testing/_collect.py 4, and the rest spread
1-3 per file) were not attempted this pass -- budget cut, not a scope
carve-out. A follow-up ticket is filed for them (T-1062, "EXHAUST001/002
residual burn-down continuation (post T-1056)").

Per the coordination constraint, this pass did not touch or count
src/frob/perf/** (T-1053: _collectors.py 2, _redundancy.py 2, _rules.py 2,
_heat.py 1, _serial_pools.py 1 = 8 sites) or src/frob/vet/** /
src/frob/gates/_opaque.py (T-1051: vet/_capability.py 5,
vet/_closedworld.py 2 = 7 sites; gates/_opaque.py had 0 EXHAUST sites in
this run's snapshot).

### Changed
```
 src/frob/gates/__init__.py |  87 ++++++++++++++++++++----
 tickets.md                 | 162 ++++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 235 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_changelog_mentions_rejects_substring_in_prose` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_changelog_mentions_accepts_real_heading_entry` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance005_registered_in_known_gate_rules` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance005_fires_on_deferred_disposition` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance005_silent_on_handled_by_and_out_of_scope` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance005_missing_registry_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateWaivers::test_ceiling_refires_when_grown_past_it` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_forward_progress_across_a_merge_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_non_merge_commit_never_checked` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_archived_ticket_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_missing_worktree_reports_once_with_path_and_remedy` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_live_worktree_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_five_stale_leases_each_reported_exactly_once` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_no_leases_directory_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_dec001_dangling_decision_edge` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_dec002_accepted_decision_unanchored` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_accepted_and_anchored_passes` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_no_decisions_dir_skips` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_never_adopted_decisions_dir_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_decisions.py::test_deleted_after_adoption_fires_dec003` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 26 passed (from 26 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
