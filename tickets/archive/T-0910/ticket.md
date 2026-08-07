---
id: T-0910
title: 'arch: declare exec/net/fetch_url capabilities for _logging_checks.py graphlang
  node (SELFAUDIT001)'
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/_logging_checks.py
- design/frob.strata
- src/frob/vet/_capability.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability.py
  reason: root cause is the SYS100-family scanner's self-pattern-path exclusion missing
    this file, same class T-0729 fixed for _srp.py -- fixing scope per dispatch instruction
    rather than declaring fake capabilities
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_vet.py
  reason: regression tests for the is_self_pattern_path exclusion fix
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_logging_checks_needle_tuples
- tests/test_vet.py::TestFingerprintScan::test_line_effects_reports_no_capability_on_logging_checks_module
designated_repro_test: null
threat: null
component: null
---
gates-security's SELFAUDIT001 stage flags src/frob/arch/_logging_checks.py:67,70,71,73 (exec/net capability markers, T-0622's own _LOG_CALLEE_MARKERS/_BOUNDARY_CALLEE_MARKERS text-matching heuristics) and a fetch_url capability as observed-but-undeclared on the graphlang design node. Discovered while verifying T-0625's gates-security stage; out of scope there (file untouched by T-0625, pre-existing since T-0622 landed on main). Declare the capabilities on the design node or waive with a reason if these are false-positive text matches, not actual exec/net/fetch_url use.