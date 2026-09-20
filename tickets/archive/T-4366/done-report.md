## Done report

Changed:
tests/conftest.py::_harden_loadscope_scheduler
tests/conftest.py::_safe_remove_node
tests/unit/test_conftest_stackdump.py::TestLoadscopeSchedulerHardening.test_reentrant_remove_node_during_reschedule_does_not_raise
tests/unit/test_conftest_stackdump.py::_ReentrantCrashNode

Evidence:
tests/unit/test_conftest_stackdump.py::TestLoadscopeSchedulerHardening::test_reentrant_remove_node_during_reschedule_does_not_raise

Filed: none (WIRE001 false-positive on the shutting_down property waived
against the pre-existing T-4371, filed while working the prior ticket in
this series)

Gates: frob check --ticket T-4366 clean of scope-relevant findings; the
2 remaining COV003/COV007 findings are pre-existing repo-wide gate
results unrelated to tests/conftest.py or
tests/unit/test_conftest_stackdump.py (T-4346, src/frob/tickets/
_mutation_evidence.py -- neither touched by this diff).

--check-repro genuinely FAILED_AT_PARENT: committed the regression test
alone first (dcd31ce7c, before the fix), confirmed it raises
'RuntimeError: dictionary changed size during iteration' at that commit,
then committed the fix and re-ran --check-repro --base-ref against the
repro-only commit -- FAILED_AT_PARENT confirmed, matching what BUG002
wants. 39/39 tests in tests/unit/test_conftest_stackdump.py pass under
xdist (-n auto, this repo's default) post-fix.

### Changed
```
 tests/conftest.py                     |  80 +++++++++++++++++++-
 tests/unit/test_conftest_stackdump.py | 133 ++++++++++++++++++++++++++++++++++
 tickets/T-4366/ticket.md              |   6 ++
 3 files changed, 218 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestLoadscopeSchedulerHardening::test_reentrant_remove_node_during_reschedule_does_not_raise` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4785 warning(s), 961 waived
- error-findings: COV003@tickets/T-4364/ticket.md, COV007@src/frob/tickets/_mutation_evidence.py
