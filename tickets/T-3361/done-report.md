## Done report

Changed:
tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_refuses_when_evidence_passes_at_parent
tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_succeeds_when_evidence_fails_at_parent
tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_repro_timeout_s_is_forwarded
tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_no_node_id_resolves_designated_test

Root cause (one, across both files): T-3104 added a keyword-only
`env_absent` parameter to `frob.gates._bug_repro._bug_repro_outcome_at_ref`
and its own real call site now always passes it. Both test files still
assumed the pre-T-3104 3-positional-arg call shape: two monkeypatch
lambdas in test_ticket_close_bug002_t1427.py rejected the extra kwarg
outright (TypeError: unexpected keyword argument 'env_absent'), and two
`mock.assert_called_once_with(...)` expectations in
test_ticket_runner_designate_repro.py hardcoded the old call signature and
failed to match the real call (AssertionError: expected call not found).
Pure test-vs-code drift, not a product defect.

Fix: widen the lambdas to `lambda root, test_id, base_ref, **_:` (absorbs
env_absent and any future kwarg), and widen the two assertions to include
`env_absent=unittest.mock.ANY` (these tests are about timeout_s
forwarding / node-id resolution, not env_absent's exact value).

Evidence: tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_refuses_when_evidence_passes_at_parent
tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_succeeds_when_evidence_fails_at_parent
tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_repro_timeout_s_is_forwarded
tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_no_node_id_resolves_designated_test
Both full files re-run clean: test_ticket_close_bug002_t1427.py 2/2 passed;
test_ticket_runner_designate_repro.py 16/16 passed.

Filed: none

Gates: scoped fix only, both files' full suites green.

### Changed
```
 tests/unit/test_ticket_close_bug002_t1427.py     |  9 ++++++--
 tests/unit/test_ticket_runner_designate_repro.py | 20 +++++++++++++++---
 tickets/T-3361/ticket.md                         | 27 ++++++++++++++++++++++--
 3 files changed, 49 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_refuses_when_evidence_passes_at_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_succeeds_when_evidence_fails_at_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_repro_timeout_s_is_forwarded` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_no_node_id_resolves_designated_test` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
