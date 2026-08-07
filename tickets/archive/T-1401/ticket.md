---
id: T-1401
title: 'frob-coverage.lock.json disagrees with the coverage.xml it was stamped from:
  81.2 percent recorded for a file with zero hits'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_records_a_genuine_zero
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_still_clamps_a_nonzero_drop
- tests/test_gates.py::TestCoverageLoad::test_unjoined_modules_are_enumerated_not_silently_omitted
designated_repro_test: null
acceptance:
- text: GIVEN a make coverage run WHEN the lock is stamped THEN every module_line
    value equals the coverage computed from that run coverage.xml for the same module
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_still_clamps_a_nonzero_drop
- text: GIVEN a module with zero recorded hits in coverage.xml WHEN the lock is stamped
    THEN it records zero for that module, never a non-zero value carried from elsewhere
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_records_a_genuine_zero
- text: GIVEN the stamped lock WHEN load_coverage reports module_join_fraction below
    0.95 THEN the unjoined modules are enumerated explicitly rather than silently
    omitted
  evidence:
  - tests/test_gates.py::TestCoverageLoad::test_unjoined_modules_are_enumerated_not_silently_omitted
threat: null
component: null
---
Measured on main 2026-08-01 from the stamped artifacts of a clean, crash-free make coverage run (exit 0, 851 files stamped, no worker crash, suite reached 100 percent).

frob-coverage.lock.json records source_sha=de76e283 and, in its module_line map:

    src/frob/__main__.py             81.2
    src/frob/serve/_socketd.py       65.1
    src/frob/serve/_leases.py        40.3
    src/frob/strata/_selfconform.py  79.6

The coverage.xml produced by that same run (preserved at .frob/coverage.partial.xml) says otherwise, read directly out of the XML:

    __main__.py        0 of 133 lines hit,   0 of 12 branch lines hit
    serve/_socketd.py  0 of 264 lines hit,   0 of 21 branch lines hit

Every branch line in those files carries hits="0" and condition-coverage="0% (0/2)". The two artifacts describe the same run and disagree completely.

This matters because the lock file is the persisted record. It is what survives the recipe's own frob clean, what delta and ratchet comparisons read, and what a coordinator inspects after the fact when coverage.xml is already gone. A lock that reports 81.2 percent for a file with zero recorded hits will silently certify a regression as fine, and it is actively misleading during diagnosis -- this ticket exists because it misled one: the lock's numbers were taken as ground truth and used to file T-1398 against a join defect that does not exist.

Determine which side is wrong. Either the stamp writes values not derived from the report it is stamping, or it is merging in stale data from a previous run, or module_line means something other than "coverage of this module in this run" and is being read as though it does. Any of the three is a defect in either the code or its documentation.

Related and deliberately NOT folded in:

- T-1398 was filed on the premise that the per-symbol join was broken. That premise is disproven -- the join is correct and TEST005 faithfully reports what coverage.xml contains. T-1398 should be dropped in favour of this ticket.

- The open question T-1398's acceptance [1] raised is still live and belongs here: load_coverage reports module_join_fraction=0.53, and only 447 of 851 known .py modules appear in coverage.xml at all. Whether that is the same defect or a second one is part of this investigation.

- The genuinely-zero coverage of __main__.py and serve/** is a THIRD, separate matter and is T-1395's original premise, which stands after all. Those modules really are unexercised in the measured process, even though agents proved they trace correctly under the subprocess rc in isolation. T-1395 failed because the fix was not in the two files it scoped to, not because the problem was imaginary.

- T-1375 already landed a provenance audit trail for lock writes (.frob/coverage-lock-audit.log). Check it first: it may already record who wrote these values and when.