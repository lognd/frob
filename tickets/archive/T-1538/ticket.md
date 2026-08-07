---
id: T-1538
title: gates.md stale doc anchor for moved redaction engine (frob.security._redact)
state: dropped
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Refiled: original draft T-1538 (filed during T-1318) died in the t-1350 ledger corruption spans. One stale doc anchor in docs/modules/gates.md still points at the pre-move frob.gates._secrets redaction internals; file was leased by T-1205 at the time. Repoint to frob.security._redact's section.

## Failure log
- 2026-08-06 attempt 1: already fixed: docs/modules/gates.md's frob.security._redact.py::_redact anchor was corrected in T-1318's own land (commit a579f23e), before this refile of the ledger-corrupted draft was created; verified 0 DOC004/DOC006/DRIFT001 findings against gates.md's redaction section

## Drop reason
- 2026-08-06: already fixed: T-1318's own land (commit a579f23e) already corrected docs/modules/gates.md's frob:describes anchor to src/frob/security/_redact.py::_redact before this refile of the ledger-corrupted draft was even created; verified 0 DOC004/DOC006/DRIFT001 findings scoped to the file's redaction section (frob check --only docanchor --only doclink --only drift --only docblocks --ticket T-1538)