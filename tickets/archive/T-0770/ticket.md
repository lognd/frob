---
id: T-0770
title: 'self-conformance: graphlang node missing may exec after T-0695 landed _concurrency.py'
state: dropped
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Discovered while working T-0717 (unrelated ticket) and merging main
forward: T-0695 landed src/frob/arch/_concurrency.py (subprocess/fork
usage) without design/frob.strata's graphlang node declaring may "exec"
for it. tests/unit/strata/test_selfconform.py::TestRealGateGreen::
test_repo_design_and_declarations_are_self_conformant now fails with 4
SYS100 findings:

capability 'exec' observed at src/frob/arch/_concurrency.py:28/... but
not declared, node=graphlang.

Fix: add may "exec" to design/frob.strata's graphlang node declaration
(or the correct owning node per its code= glob), then re-verify
TestRealGateGreen passes. Scope: design/frob.strata,
tests/unit/strata/test_selfconform.py (verification only).

## Drop reason
- 2026-07-22: wrong remedy: the exec observations on _concurrency.py were docstring/comment prose false-positives, not real capabilities; declaring may exec on graphlang would falsely widen the declared threat surface. Superseded by T-0769 (observer excludes non-executable spans) plus the mitigation reword commit; TestRealGateGreen is green on main (absorbed by T-0769)