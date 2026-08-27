---
id: T-3142
title: Break the 182-node import cycle (name the real next cut from the current cycle
  output)
state: done
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'T-3142 is a naming/decision ticket per its own brief (name
  one real next

  cut, do not attempt it, do not plan the whole decomposition) -- no code

  change belongs to this ticket itself; the actual cut lands under the

  newly-filed sibling ticket instead.

  '
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): Naming/decision ticket per its own brief: measures
    the current cycle,

    names one real next cut with edge evidence, and files it as a sibling

    ticket (T-3155) rather than attempting the cut or duplicating

    T-2202/T-2667/T-2835. No source behavior changes under this ticket

    itself.'
  actor: logan
  at: '2026-08-27'
  old_length: 897
  new_length: 1218
- mode: append
  reason: 'BUG002 front door (T-2393): Naming/decision ticket per its own brief: measures
    the current cycle,

    names one real next cut with edge evidence, and files it as a sibling

    ticket (T-3155) rather than attempting the cut or duplicating

    T-2202/T-2667/T-2835. No source behavior changes under this ticket

    itself.'
  actor: logan
  at: '2026-08-27'
  old_length: 1218
  new_length: 1539
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 26aa3de93c90ace2bdfaf59e18b63ed182ecaf16
---
T-3086 extracted frob.gates._models's universal value types (Severity,
WaiverRef, DebtEntry, Violation) into a new leaf module frob.findings.
Both `import frob.gates._models` and `import frob.findings` succeed;
existing tests pass unchanged.

MEASURED: `frob cycle src/frob`'s 182-node SCC is UNCHANGED before and
after that cut -- src/frob/gates/_models.py was never itself a member of
the printed 182-node cycle path, so removing those four symbols from it
did not touch the cycle's own membership.

Re-run `frob cycle src/frob` against the current tree (post-T-3086) and
name ONE real cut from the ACTUAL 182-node cycle's own printed node list
-- do not assume gates/_models-adjacent files are involved; verify by
reading the current cycle output directly. Do not try to plan the whole
decomposition here -- one cut, then re-measure, then file the next sibling,
matching T-3086's own directive.

frob:no-behavior-change reason="Naming/decision ticket per its own brief: measures the current cycle,
names one real next cut with edge evidence, and files it as a sibling
ticket (T-3155) rather than attempting the cut or duplicating
T-2202/T-2667/T-2835. No source behavior changes under this ticket
itself."

frob:no-behavior-change reason="Naming/decision ticket per its own brief: measures the current cycle,
names one real next cut with edge evidence, and files it as a sibling
ticket (T-3155) rather than attempting the cut or duplicating
T-2202/T-2667/T-2835. No source behavior changes under this ticket
itself."