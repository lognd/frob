---
id: T-1429
title: T-1422 landed a fresh INV006 on src/frob/tickets/_accept.py
state: dropped
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_accept.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1422's landed commit (frob ticket accept --amend/--remove) introduced src/frob/tickets/_accept.py, which makes incidental "only" wording in its docstrings/log messages -- an unscoped frob check --only invariant now reports INV006 on this file with no frob:invariant anchor and no waiver. Check each occurrence: most look like incidental prose (module docstring, a log format string) rather than a genuine new normative claim, matching the same shape T-1424 just resolved for the _cli_parsers/_ticket/ split -- likely needs either a targeted waiver with a real reason or a light reword, not a new invariant. Found while verifying T-1424's unscoped frob check (playbook section 6c); out of T-1424's declared scope (src/frob/tickets/** is not in it), so filed separately rather than fixed inline.

## Drop reason
- 2026-08-02: T-1427 already resolved this: src/frob/tickets/_accept.py carries a reasoned frob:waive INV006; frob check --only invariant confirms 0 findings on this file. Re-dropped on main after the worktree drop was lost to the ledger splice (T-1437's resurrect class).