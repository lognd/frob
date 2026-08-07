## Done report

Folded evaluate_compliance into the sys gate family (SELFAUDIT001-style
aggregation) so a design/ model with an exposure:public-web node and no
privacy-policy mitigation now fails frob check, not only the manual
`frob sys audit`. The green-check-red-audit divergence class this closes
is regression-tested directly (a model that fails sys audit compliance
must fail frob check), and the WARN/ERROR tier decision is documented.

Resumed from an OOM-killed prior session: the fold itself and its three
tests were already committed. This session merged main forward (clean,
no scope regression per `git diff main --diff-filter=D --stat`), rebuilt
natives, and closed the one remaining gap AFFECT001 flagged: the
COMPLIANCE_OUT_OF_SCOPE CCPA-narrowing edit (part of the sibling T-1246
compliance-triage work sharing this file) needed its affects()-closure
doc (docs/strata/threat.md#compliance-regulatory-obligations-stdcompliance)
touched in the same diff -- added a short CCPA-partial-coverage note.
Re-ran the pre-work sweep (PRE001) after that doc edit. gates-native,
gates-security (SEC/PII/DEAD clean; the 3 OPAQUE001 findings are
pre-existing on main in src/frob/app/__init__.py and app.py, unrelated to
this ticket's scope), and gates-fast (--ticket T-1314) are all clean.

### Changed
```
 docs/design/registry/EXHAUSTIVENESS-GATE.md |  43 ++++++----
 docs/modules/gates.md                       |  33 +++++++-
 docs/strata/threat.md                       |  11 +++
 src/frob/gates/_sys.py                      | 124 +++++++++++++++++++++++++++-
 tests/test_gates.py                         |  76 +++++++++++++++++
 tickets.md                                  | 117 ++++++++++++++++++++++----
 6 files changed, 368 insertions(+), 36 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_compliance_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_clean_model_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_compliance_suppressed_on_design_load_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 7383 warning(s), 678 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py
