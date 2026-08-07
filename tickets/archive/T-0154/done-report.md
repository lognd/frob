## Done report

Changed:
- strata-core/src/parse.rs -- new `carries STRING+` clause on node and
  store (mirrors the T-0132 code/may STRING-quoted shape); 5 rust parser
  fixture tests.
- src/frob/strata/_ast.py -- carries tuple on NodeDecl/StoreDecl.
- src/frob/strata/_elaborate.py, _infra.py -- carries desugars to
  pii=<tag> node attrs (same per-atom convention as code=<glob>).
- src/frob/strata/_pii.py (new) -- std.pii: PII_CATEGORIES
  (identifier/contact/financial/health/biometric/behavioral/credentials),
  PiiViolation/PiiReport, node_pii_tags/node_carries_pii, four joins
  PII001 (malformed category) / PII002 (trust-boundary crossing without an
  assumed pii:PROTECTION claim, THREAT003-style discharge) / PII003
  (retention+erasure, reusing _compliance.py _retention_limit and
  _REVOCATION_ATTR, not duplicating) / PII004 (undeclared-PII lint);
  evaluate_pii entrypoint.
- src/frob/strata/_audit.py -- evaluate_exhaustiveness runs evaluate_pii
  under a pii:model view, joined into AuditReport.gaps.
- src/frob/strata/__init__.py -- public exports for the new _pii symbols.
- docs/strata/threat.md, surface.md -- PII section + carries grammar.
- design/frob.strata -- explicit zero-PII posture (not silent).
- editors/vscode-strata/syntaxes/strata.tmLanguage.json -- carries added
  to clause-keywords (tmLanguage drift-lock consequence; scope extension
  justified here).
- Tests: litmus pii_vuln/pii_hardened.strata, test_litmus_pii.py,
  test_pii.py (incl. self-model zero-PII assertions), one new audit test.

Evidence: 27 pytest node ids recorded (catalog/boundary/retention/lint/
join/self-model/litmus/tmLanguage-drift-lock). Rust fixtures verified via
cargo test parse:: (89 passed), not collectible as python node ids.

Gates: frob check --ticket T-0154 exit 0, 0 unwaived violations, 6 new
waivers each with written reasons (5 PERF003/004 false-positive
sort/dict-comp matching existing _compliance/_threat precedent, 1 TEST005
branch-coverage debt on evaluate_exhaustiveness Err paths). frob sys
audit PROVED, 9 views incl. pii:model, 0 gaps, self-conformance PROVED.
Full pytest green. ruff/ruff-format/ty clean on touched files.

Reviewer: APPROVE -- verified reuse-not-parallel-build (PII003 calls
_compliance helpers, carries mirrors T-0132 parse path, PII002 reuses
THREAT003 assume machinery), grammar soundness on node AND store (T-0166
trap does not recur), mutation-probed each join non-vacuous, self-model
zero case non-tautological, category-to-compliance join sound.

Filed: none.
