---
id: T-0911
title: 'SELFAUDIT001: src/frob/arch/_logging_checks.py capabilities undeclared on
  graphlang node'
state: dropped
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/_logging_checks.py
- design/*.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while verifying T-0897 (unrelated fix): `frob check --only gates-security`
fails gate:SELFAUDIT with 5 SELFAUDIT001 errors, all against
src/frob/arch/_logging_checks.py (capabilities 'exec'/'net'/'fetch_url'
observed at specific lines but not declared on the `graphlang` design
node). This file was newly landed via a recent main merge (arch smells/
fallibility/logging-checks tickets), not touched by T-0897's scope
(src/frob/gates/_render_lint.py, _pii_structural.py,
_cve_fingerprint_scan.py). Needs either a std.capabilities declaration
added to design/*.strata for `graphlang`, or a `frob:waive SELFAUDIT001
reason="..."` if these are false positives, so `frob check
--only gates-security` is clean again.

## Drop reason
- 2026-07-26: duplicate of T-0910 (same SELFAUDIT001 finding on _logging_checks.py, filed independently by two concurrent agents)