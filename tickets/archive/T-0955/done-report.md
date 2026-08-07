## Done report

Verified on current main (post T-0860 land, which already fixed the strata
self-conformance + export-golden drift for undeclared mutate/deploy
capabilities on the natives node): tests/unit/strata/test_export_golden.py
(test_k8s, test_seccomp, test_iam) and tests/system/test_frob_self_model.py
all pass clean on this worktree with no code/golden changes needed. No
drift remains between the checked-in golden fixtures and the exported
seccomp/IAM/k8s JSON. No regeneration was required -- T-0860 already
regenerated the goldens for the natives-node addition before this ticket
was actioned. frob check --ticket T-0955 (gates-native, gates-fast) is
clean (0 errors both groups). Closing with no code change; evidence is the
already-passing golden/self-model suite.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 4924 warning(s), 333 waived
- error-findings: none (measured, zero errors)
