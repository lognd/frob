## Done report

Verified T-0346's close condition is genuinely met and closed the epic.

Children: all 6 direct children (T-0673, T-0674, T-0675, T-0676, T-0677,
T-0678) are state=done, confirmed by direct grep of tickets.md/
tickets-archive.md for `parent: T-0346` -- no open or blocked child
remains.

Acceptance [0] (single machine-readable registry + reconciliation test
catching prose-only and split-across-files misses): `docs/design/
registry/*.yaml` (10 files, 2190 entries) is the single canonical
registry every corpus doc's ids now route through; T-0678's `tests/
unit/strata/test_registry_cross_corpus_totality.py` (just landed) is the
standing meta-test for both miss classes -- `TestCrossCorpusLinkageIntegrity`
locks that every cross-file concept link (the "split across files" class,
finding (b)/(h)) stays resolvable and mutually navigable across the WHOLE
registry, and `TestProseOnlyRetrofitIntegrity` locks that the 156 ids
minted for the 3 previously prose-only docs (finding (a)) stay present
with correct source pointers.

Acceptance [1] (TRUE exhaustiveness, CWE-1000 full to per-entry
disposition): `weaknesses.yaml` carries 984 entries (944 CWE + 40 other
weakness-framework entries), matching RECONCILIATION.md's own stated
CWE-1000 total exactly -- verified live via `frob.registry.
audit_registry_file`: `total=984, exhausted=True, unaccounted=0`.
`tests/test_registry_reconciliation_weaknesses.py::
TestWeaknessesExhaustiveness::test_declared_cwe_total_is_944` and
`test_audit_reports_exhausted` both independently re-run passing,
confirming this against the live file.

Acceptance [2] (every registry entry carries a disposition, drift-locked):
verified live across the ENTIRE registry, all 10 files, not just the ones
this drive's tickets touched -- `frob.registry.audit_registry_file` over
every `docs/design/registry/*.yaml` file reports `unaccounted=0` for
EVERY file (arch-checks 311, check-coverage 240, compliance 27, evasion
112, patterns 346, pii 7, secrets 3, supply-chain 41, system-design 119,
weaknesses 984 = grand total 2190, unaccounted 0 across the board). T-0343's
exhaustiveness drift-lock (`registry_gate`, wired into `frob check`'s
default REG-family gates) is live and enforcing this today.

Disclosed gap, not silently claimed closed (found while verifying the
close condition, unrelated to any of T-0346's own children's work): `tests/
test_registry_reconciliation_weaknesses.py::
TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations`
fails on current main -- `registry_gate` reports 798 REG011 (WARN-severity,
T-0680, an out_of_scope reason-quality check that landed AFTER T-0384's
test was written) violations against `weaknesses.yaml`'s `out_of_scope`
dispositions. This does not affect acceptance [1]/[2] (REG011 is a
severity=WARN quality-bar check on REASON TEXT, not an exhaustiveness/
disposition-presence check -- `audit_registry_file`'s `unaccounted=0`
above is unaffected) but is real, live drift worth fixing. Filed
T-1037 rather than silently fixed (out of T-0346's own declared
scope: the affected test file and weaknesses.yaml belong to T-0384's
scope, not T-0346's `tests/unit/strata/` test-file scope).

Evidence: the T-0678 meta-test (already this ticket's own evidence, cited
again here as the epic's closing proof) plus the two passing weaknesses.yaml
exhaustiveness tests (CWE-1000 completeness), all independently re-run.

Gates: verified via direct `frob.registry.audit_registry_file` calls
against the live registry (see above) rather than a fresh `frob check`
run -- this ticket makes no code change, only verifies and closes; the
constituent meta-tests' own gate passes were already recorded at their
own land time (T-0678's Done report, this same session).

Filed: T-1037 (REG011 quality-bar drift in weaknesses.yaml,
found while verifying this epic's close condition, unrelated to T-0346's
own scope of work).

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 3382 warning(s), 340 waived
- error-findings: none (measured, zero errors)
