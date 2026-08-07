## Done report

Disposed T-1038's last 3 out-of-scope OPAQUE001 sites:
- src/frob/gates/__init__.py:6723 (getattr(logging, level_name)): real fix
  -- replaced with logging.getLevelNamesMapping()[level_name], a literal
  dict lookup the static resolver can see through; level_name is always
  one of that mapping's own keys (written by
  _stamp_worker_stdout_log_level_env via logging.getLevelName's reverse).
- src/frob/gates/_docblocks.py:391-392 (importlib.import_module +
  getattr for the DOC004 console-parser plugin loader): reasoned
  frob:waive OPAQUE001 on both lines -- dotted is a repo-owner-authored
  frob.toml [[doc004.source]].parser config value, never untrusted input;
  resolving it statically would defeat the plugin mechanism itself.

Verified 0 unwaived OPAQUE001 findings repo-wide (`frob check --only
opaque`, 0 errors/0 warnings/107 waived), then promoted OPAQUE001 from
Severity.WARN to Severity.ERROR in _opaque.py's Violation construction
AND added OPAQUE001 = "error" to frob.toml's [gates.severity] table in
this same land, matching the SEC110 (T-0973)/PII010+PII012
(T-0971)/ARCH001 (T-0976)/PERF001-004 (T-0972) promote-at-zero precedent.

Fallout from the promotion: tests/test_vet.py::TestOpaqueIndirectionGate
.test_opaque_gate_emits_warn_severity_violation asserted Severity.WARN
directly -- updated the assertion to Severity.ERROR (kept the test's
original name since T-0665/T-1038 cite that exact evidence node id by
name; renaming it broke COV003/DRIFT002 against those closed tickets'
recorded evidence). Added tests/test_vet.py and frob.lock to T-1185's
scope (both direct, unavoidable consequences of the in-scope
_opaque.py change: the test assertion and the frob ack digest refresh
for opaque_gate's changed body).

### Changed
```
 frob.lock                    |  2 +-
 frob.toml                    | 11 +++++++++++
 src/frob/gates/__init__.py   |  7 ++++++-
 src/frob/gates/_docblocks.py |  9 +++++++++
 src/frob/gates/_opaque.py    |  7 ++++++-
 tests/test_vet.py            |  4 +++-
 tickets.md                   | 23 +++++++++++++++++++++--
 7 files changed, 57 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 831 warning(s), 680 waived
- error-findings: none (measured, zero errors)
