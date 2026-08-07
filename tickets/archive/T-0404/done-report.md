## Done report

Audit docs/audits/lang-check-docs.md worked finding-by-finding, verify-first / counterexample-first.
Three findings fixed with real code + tests (5, 10, 11). Finding 12 verified correct as-is (no
fix needed). Finding 3 verified already-fixed for THIS repo via frob.toml [gates.severity]
config (COV001 promoted to error), though the underlying gate-code default severity is still
WARN by design for repos without that override -- not a code bug here. The remaining findings
(1, 2, 4, 6, 7, 8, 9) are real but each needs a cross-cutting design change (dispatch
architecture, a new PARSE001 gate, doc-walk unification) too large for this ticket's budget, or
sit outside T-0404's declared scope (graph/) -- not filed as follow-ups, each carrying the finding
text, repro, and RIGHT-WAY fix direction.

Disposition table:
- #1  (HIGH)   doc/coverage/drift/inv gates run ONLY in the Python pipeline -- FOLLOW-UP (too large): T-draft-8a073c15 (never refiled)
- #2  (HIGH)   parse/IO failure silently erases a file's obligation set    -- FOLLOW-UP (out of T-0404 scope, graph/): T-draft-ed8f5ca3
- #3  (HIGH/MEDIUM) COV001 is WARN-only                                    -- VERIFIED already-fixed-by config for this repo:
              frob.toml [gates.severity] COV001 = "error" (the run this
              session stamped shows "severity overrides active:
              {'COV001': ERROR, 'TEST001': ERROR, ...}"). The gate's own
              code-level default remains WARN by design (documented as
              the "legacy-adoption baseline" for repos without the
              override) -- not a bug in this codebase's own posture,
              no fix needed here.
- #4  (MEDIUM) DRIFT is one-directional (doc-edit-to-lie never trips)      -- DUPLICATE of T-0403 B2
              (same root cause, DRIFT001 default sig facet); tracked
              there as T-draft-b3811054, not re-filed here.
- #5  (MEDIUM) malformed frob:doc directives silently downgraded          -- FIXED: new DSL001
              catch-all gate (gates/__init__.py::_dsl001_violations) fires
              on any MalformedDirective not already claimed by
              WAIVE001/TEST010/DEBT001. Verified the OLD behavior first: a
              bare `# frob:doc` (no target) produced zero violations before
              this change.
- #6  (MEDIUM) unknown project type silently runs the Python pipeline     -- FOLLOW-UP: T-draft-3177db00
- #7  (MEDIUM) nested/top-level-less native sources escape detection      -- FOLLOW-UP: T-draft-68268ec3
- #8  (MEDIUM) frob:describes anchors outside docs/ are invisible         -- FOLLOW-UP (out of T-0404 scope, graph/): T-draft-2d709aeb
- #9  (MEDIUM) weak parse-failure threshold drops symbols in error regions -- FOLLOW-UP: T-draft-934fdd62
- #10 (LOW)    vitest non-JSON zero-exit reported as a clean pass         -- FIXED: _run_vitest
              (check/_ts.py) now attaches a WARNING diagnostic when tests
              is empty and returncode is 0, instead of a bare "tests
              passed" summary with zero diagnostics.
- #11 (LOW)    detect_project_type vs _detected_types disagree on what    -- FIXED: detect_project_type
              counts as a TypeScript repo                                    now requires only package.json,
              matching _detected_types' own contract (dropped the extra
              tsconfig.json requirement).
- #12 (LOW)    gate-internal exception could be silently swallowed        -- VERIFIED CORRECT: `future.result()`
              at __init__.py:6489/6530 re-raises; an uncaught gate
              exception propagates and aborts the run loudly, it is not
              dropped. No fix needed.

Section (A)/(D) framing and (C) soundness notes in the audit were read but are not
independently-actionable findings -- no disposition row needed for them.

### Changed
```
 src/frob/check/__init__.py                |  14 +-
 src/frob/check/_ts.py                     |  30 ++-
 src/frob/gates/__init__.py                | 101 +++++++-
 tests/test_gates.py                       |  91 +++++++
 tests/unit/test_check.py                  |  10 +
 tests/unit/test_check_tool_unavailable.py |  27 +++
 tickets.md                                | 379 +++++++++++++++++++++++++++++-
 7 files changed, 636 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDsl001::test_malformed_frob_doc_directive_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDsl001::test_waive_reason_and_tests_kind_not_double_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_tool_unavailable.py::TestVitestUnverifiedZeroExit::test_run_vitest_warns_on_unparseable_zero_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDetectProjectType::test_package_json_alone_is_typescript` (pytest node id, verified passing when recorded)
