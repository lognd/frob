## Done report

Changed: docs/design/registry/system-design.yaml -- reworded all 14
manifest-extraction-artifact disposition strings (SDC-1-*, SDC-5-*,
SDC-10-*, SDC-13-* entries) from bare `out-of-scope(manifest-extraction-artifact)`
to `out_of_scope:none -- manifest-extraction artifact from
docs/design/system-design-corpus.md heading parsing (e.g. a bare
checkability-tier heading or best-practice bullet with no distinct property
name); not a real named entry with a property to check, no static check
applies`, matching T-0722's reasoned-none phrasing style.

Evidence:
tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign::test_no_system_design_violations
(pass, foreground); full tests/test_registry_reconciliation_system_design.py
(8 passed, foreground).

Filed: none

Gates: `uv run frob check --ticket T-0912` shows zero REG011 findings against
system-design.yaml (grep confirmed no manifest-extraction/system-design.yaml
hits remain in REG output). Remaining FAIL gates in that same run (ty, COV,
DRIFT, SYS, and REG011 findings in compliance.yaml/patterns.yaml) are
pre-existing and outside this ticket's declared scope
(docs/design/registry/system-design.yaml only) -- not caused by this change,
which touched only disposition string text in that one file.
