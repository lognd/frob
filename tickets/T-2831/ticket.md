---
id: T-2831
title: 'LARGE001: promote large-file from WARN to ERROR in _arch.py (T-2375 successor)'
state: done
kind: bug
origin: agent
created: '2026-08-21'
priority: medium
blocked_by:
- T-2822
- T-2823
- T-2824
- T-2825
- T-2826
- T-2827
- T-2828
- T-2829
- T-2830
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_arch.py
- tests/unit/test_arch_srp.py
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error
designated_repro_test: null
acceptance:
- text: given all 9 blocking children are terminal (done or dropped --absorbed-by),
    when frob.gates._arch._ERROR_SEVERITY_CATEGORIES is read, then it contains 'large-file'
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error
- text: given the promotion has landed, when frob check --json --budget 500 runs,
    then LARGE001 fires at Severity.ERROR (not WARNING) for any surviving finding,
    and the two updated test files assert ERROR not WARN
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2375's own declared scope (src/frob/gates/_arch.py's _ERROR_SEVERITY_CATEGORIES: add 'large-file' so LARGE001 promotes from Severity.WARN to Severity.ERROR) was deliberately NOT executed by T-2375 -- T-2375 itself only measured (85 LARGE001 warnings, confirmed against T-2796's independent measurement), characterized (many independent oversized-file causes, no shared root fix, T-1651 precedent applies: forced splits with no real seam are worse than the warning), and decomposed into 9 disjoint child tickets covering all 84 non-_selfconform.py files (T-2822/T-2823/T-2824/T-2825/T-2826/T-2827/T-2828/T-2829/T-2830; T-2729 separately owns src/frob/strata/_selfconform.py, the single largest offender, and is not one of these 9).

Promoting severity now, before those 9 children land, would turn every one of their still-open findings into a fresh ERROR and red main for work already accounted for -- exactly the premature-spend mistake T-2809/T-2816 both name in a different context (do not spend a shared/global state change before the work it depends on is actually done). This ticket is therefore --blocked-by all 9 children and must not start until every one of them is in a terminal state (done, or dropped --absorbed-by with a named survivor).

Closure: add 'large-file' to _ERROR_SEVERITY_CATEGORIES in src/frob/gates/_arch.py, update tests/unit/test_arch_srp.py and tests/test_arch_gate.py's TestArchGateLargeFile (currently asserts WARN, e.g. test_large_file_fires_large001_warn) to assert ERROR instead, and re-measure 'frob check --json --budget 500' to confirm LARGE001 now reads zero WARN-severity findings (the 6 pre-existing frob:waive T-1651 waivers on _models.py/_waive.py/_land_git_ops.py/check_runner.py/config.py/sys_runner.py stay at severity=note regardless of the promotion -- a waiver silences the finding at any severity, confirm this rather than assuming it).

## Failure log
- 2026-08-22 attempt 1: measured 57 total LARGE001 findings (55 waived, 2 unwaived): src/frob/gates/_doclink_docanchor.py (1035 lines, split active under T-2843) and src/frob/tickets/_leases.py (3182 lines, seam flagged in T-2822 but not yet split/waived). Promoting WARN to ERROR now would red main for this still-open work. Not a code defect -- refusing to promote per this ticket's own stated rule; re-run once both files are terminal (waived or split).