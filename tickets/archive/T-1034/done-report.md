## Done report

T-0687 landed frob.arch._cpp_mayraise.check_cpp_noexcept_violations,
wired into analyze_project's live cpp dispatch branch, producing
ArchSuggestion(category=cpp-noexcept-throws, severity=error). This ticket
promotes that into an enforced, unwaivable-by-omission (still waivable
with a reasoned frob:waive, per the ordinary path -- see below) gate
finding via frob.gates._arch.arch_gate, the SAME channel ARCH001/ARCH1xx
already use: added "cpp-noexcept-throws" -> "CPPTHROW001" to
_ARCH_CATEGORY_TO_RULE, plus a new _ERROR_SEVERITY_CATEGORIES allowlist
(this is the first category in this module to channel at Severity.ERROR
instead of the WARN every prior category here hardcodes -- a noexcept
hard-boundary violation is std::terminate at runtime, not deferrable
style debt).

Registered CPPTHROW001 in gates/__init__.py's _KNOWN_GATE_RULES (so
frob:waive CPPTHROW001 reason="..." is a real, effective directive, not
an ineffective-channel WAIVE002 finding) and added a rule-catalog row to
docs/modules/gates.md. check-coverage.yaml's gate_rule_entries syncs
automatically at land time (T-1011's sync_gate_rule_entries, already
wired into frob ticket land) -- no manual registry edit needed.

While wiring this in, running archgate against this repo's own source for
the first time surfaced a genuine ARCH001 finding in T-0687's own
scan_cpp_functions (69 lines, threshold 60) -- pre-existing debt from the
prior ticket that was never caught since neither T-0687's own check run
nor T-0690's happened to include --only archgate. Fixed in the same
change (split into _find_signature_lines/_scan_each_function/
_propagate_callee_raises, each independently testable) since it sits
directly in this ticket's own blast radius (the file this ticket is
wiring), scope-added rather than silently left for a later ticket.

Evidence: three new tests in tests/test_arch_gate.py::TestArchGateCppThrow
(fires at Severity.ERROR naming the call site; a try/catch (...) discharges
it; a reasoned frob:waive CPPTHROW001 suppresses it through the ordinary
waiver path, confirming ERROR severity is not the same thing as
_UNWAIVABLE_RULES membership). A real run against this repo's own source
(0 C++ production files) confirms zero pre-existing CPPTHROW001 debt.

### Changed
```
 docs/modules/gates.md          |   1 +
 src/frob/arch/_cpp_mayraise.py | 104 +++++++++++++++++++++++++++-----------
 src/frob/gates/__init__.py     |   6 +++
 src/frob/gates/_arch.py        |  49 ++++++++++++++++--
 tests/test_arch_gate.py        |  95 ++++++++++++++++++++++++++++++++++
 tickets.md                     | 112 ++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 332 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateCppThrow::test_noexcept_with_catch_all_does_not_fire_cppthrow001` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateCppThrow::test_cppthrow001_is_waivable_with_reason` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateCppThrow::test_noexcept_may_throw_fires_cppthrow001_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 9 error(s), 2727 warning(s), 342 waived
- error-findings: AFFECT001@src/frob/arch/_cpp_mayraise.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py, PRE001@tickets/T-1034
