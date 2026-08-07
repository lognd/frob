## Done report

T-1279's substantive work (2 genuine TEST005 gaps closed: mutation_evidence_violations
Err/ExecDisabled branch, and 3 scan_emitted_rule_ids branches) was already implemented
and landed to main under commit 8e7503ce "test(gates): cover mutation-evidence Err
branch and rule-id-scan edges" -- this worktree's own `git log` confirms
tests/gates/test_mutation_evidence_err_branches.py and
tests/gates/test_rule_id_scan_branches.py are present in main's history. A prior
agent's Done-report prose (visible via `frob ticket show T-1279`) already documents
this investigation: 10 of the 12 listed 0.0%-branch symbols already carried real,
behavioral frob:tests-bound coverage in existing files (tests/test_secrets_gate.py,
tests/test_gates.py's TestParseFailureGate/TestKnownGateRuleIds/TestScopeDigest*/
TestPreworkGate*/TestTestGate*/TestReleaseGate*/TestPerfGate*/TestRunGates*,
tests/test_vet.py's TestOpaqueIndirectionGate) and their reported 0.0% is most
plausibly the known subprocess/multiprocess coverage-attribution gap tracked by
T-1235/T-1395 (out of this ticket's scope to fix). The ticket's ledger state had
regressed to queued after a stale-lease release (see commits 87d07376 "requeue
T-1279" and d0c5cc34 "register T-1402's gate-module scope after releasing T-1279's
stale lease") even though the code/tests were already merged.

This session re-took the lease (`frob ticket start T-1279`), re-verified the 6
tests still collect and pass (`pytest tests/gates/ -q` -- 6 passed), and re-recorded
evidence via the CLI (a prior evidence-recording attempt did not survive the
requeue -- `frob ticket show` reported "no evidence recorded" before this run).

MEASUREMENT CAVEAT: no coverage.xml/coverage stamp exists in this worktree
(`frob check --only test` reports "WARNING: load_coverage: no coverage.xml at
coverage.xml" and TEST006 "no coverage stamp found"). TEST005 is therefore
UNMEASURED in this worktree, not zero -- per playbook section 6b/6c, a full
unscoped `make coverage` run is a coordinator-only step; this dispatch did not
run it. The last COMMITTED frob-coverage.lock.json (dated Aug 5 15:41, already
on main going into this ticket) is the only on-disk reference point, and per
playbook section 6d it is NOT trustworthy as a TEST005 count (T-1401 documented
disagreements against the real coverage.xml it was derived from). No trustworthy
before/after unscoped TEST005 package number can be produced from this worktree
without running make coverage, which is out of scope for a dispatched sub-agent.

No new out-of-scope work found. T-1396 (already filed by the prior agent) tracks
the remaining ~167 non-0.0%-tier TEST005 findings in src/frob/gates.

### Changed
```
 tickets.md | 19 +++++++++++++++----
 1 file changed, 15 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches::test_exec_disabled_degrades_to_no_violations` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_commented_out_rule_literal_is_skipped` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_missing_scanned_base_directory_is_skipped_not_an_error` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_unresolved_const_ref_is_left_out` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestGeneratedGateRuleIdsRetiredOverride::test_default_retired_set_is_module_constant` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 571 warning(s), 784 waived
- error-findings: none (measured, zero errors)

### Acceptance amendments
- [0] remove: removed 'GIVEN the gates package at the 75%/70% floors WHEN frob check --only test runs THEN it reports 0 TEST005 findings under src/frob/gates/**' (reason: Unsatisfiable by construction, replaced with a triage-shaped criterion.

The removed criterion asserted zero TEST005 findings across a package holding
hundreds. No single dispatch can reach that, so the ticket could never close
honestly -- and since T-1410 wired the gate-claim guard, frob correctly REFUSES
to close it, stranding genuine completed work behind an aspiration.

This is a correction, not goalpost-moving. The criterion was authored before we
knew the count itself was partly artifact: T-1418 is currently classifying the
306 symbols reporting exactly 0.0 percent, and three agents independently found
that many already carry real, behavioral, frob:tests-bound tests -- the code is
exercised, just in a process pytest-cov does not attribute back. Demanding zero
findings therefore demanded work that in some cases does not exist, and pushed
agents toward writing filler tests against already-tested code.

The replacement is the shape used on T-1400 and it is strictly harder to satisfy
dishonestly: every remaining finding must be triaged, a genuine gap must be
closed with a behavioral test, and an artifact must be recorded with the
covering test named so the claim is checkable. Filler still fails it.
; logan, 2026-08-02)
