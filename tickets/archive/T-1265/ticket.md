---
id: T-1265
title: CI cannot verify gitignored .frob coverage/stamp/baseline signal (T-1193 successor)
state: done
kind: security
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1193
tier: ticket
sprint: null
scope:
- .github/workflows/ci.yml
- src/frob/gates/_coverage.py
- src/frob/gates/_baseline.py
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/_filehash.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'scope-closure warnings: coverage/baseline tests and shared filehash helper
    are load-bearing for this ticket''s ci-verification fix'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: src/frob/gates/_filehash.py
  reason: 'scope-closure warnings: coverage/baseline tests and shared filehash helper
    are load-bearing for this ticket''s ci-verification fix'
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: repoint CHK-THEME-GITIGNORED-TRUST from T-1265 to its successor T-1366
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_gates.py::TestTestGate::test_ci_workflow_self_gate_does_not_swallow_errors
- tests/test_gates.py::TestTestGate::test_ci_workflow_hard_fails_on_test012_drift
designated_repro_test: null
acceptance:
- text: GIVEN a PR that would locally fail TEST005/006 (stale/missing coverage-stamp)
    or TEST012 (frob-coverage.lock.json drift) WHEN the same change runs through the
    CI workflow THEN the CI job exit code reflects that failure (nonzero), not just
    a printed warning -- i.e. ERROR-tier violations for at least TEST005/006/012 fail
    the CI step outright.
  evidence:
  - tests/test_gates.py::TestTestGate::test_ci_workflow_hard_fails_on_test012_drift
  - tests/test_gates.py::TestTestGate::test_ci_workflow_self_gate_does_not_swallow_errors
- text: GIVEN a fresh CI checkout with no prior .frob state (the gitignored derived
    cache is never restored between runs) WHEN the CI workflow runs THEN either a
    coverage-stamp/baseline gets produced fresh in that same job before the gate step
    runs, or the workflow own comments/docs explicitly disclose which TEST00x checks
    are structurally inert in CI and why, so a passing CI run is never silently read
    as a full-strength guarantee it does not provide.
  evidence:
  - tests/test_gates.py::TestTestGate::test_ci_workflow_hard_fails_on_test012_drift
threat: null
component: null
---
Successor row from T-1193 (CHK-THEME-GITIGNORED-TRUST, docs/design/registry/check-coverage.yaml).

Verified real (2026-07-29): .gitignore:21 and :72 both list .frob/ (derived
cache, gitignored by design -- frob.lock/tickets.md/invariants/ are the
tracked truth). .frob/coverage-stamp and .frob/baseline live ONLY there.
.github/workflows/ci.yml self-gate step (line 44) runs the aggregate check
with a warning-only fallback -- it cannot fail the build on ANY gate
violation, including TEST005/006 (coverage-stamp staleness) or TEST012
(frob-coverage.lock.json drift). CI never runs the stamp-coverage variant,
so no fresh .frob/coverage-stamp or .frob/baseline exists in that job at
all -- a contributor local claim of "I ran coverage" is unverifiable from
the PR itself. T-0545 already landed frob-coverage.lock.json (committed,
root-level, exempt from .gitignore) as a narrow SUMMARY channel that
TEST012 diffs against a live CoverageData, but TEST012s own violation is
currently swallowed by the same non-blocking CI step, so drift there is
invisible to reviewers too.

Right-way fix direction (pick one, or combine):
1. Make the CI self-gate step fail the build on ERROR-tier gate
   violations (drop the warning-only swallow, or gate it behind an
   explicit allowlist of WARN-only families) so TEST012/DRIFT/COV
   findings are enforced in CI, not just locally.
2. Add a CI step that stamps coverage BEFORE the self-gate step, so the
   coverage-stamp/baseline that TEST005/006 checks against is freshly
   produced in-job rather than trusted from a gitignored local artifact
   that never reaches the runner.
3. At minimum, make the CI job explicitly assert (not warn) that
   frob-coverage.lock.json (the one committed, non-gitignored channel) is
   present and undrifted for any PR touching coverage-relevant source, so
   the one artifact that CAN travel with the diff is actually checked.

Do NOT weaken this to doc-only -- CHK-THEME-GITIGNORED-TRUST is a
security-relevant trust-boundary finding (a locally-green check proves
nothing to a reviewer or to CI), not a cosmetic one.