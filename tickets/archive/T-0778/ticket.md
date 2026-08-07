---
id: T-0778
title: 'security: FROB_DISABLE_EXEC kill switch is a partial no-op -- wire gitio/serve/tickets
  through the T-0200 guard, delete stale waivers'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gitio.py
- src/frob/process/_guard.py
- design/frob.strata
- tests/test_gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning
designated_repro_test: null
acceptance:
- text: GIVEN FROB_DISABLE_EXEC=1 WHEN any frob code path attempts a git spawn via
    run_argv (including the serve daemon and lease reads) THEN the spawn is refused
    by the guard and logged; GIVEN the five strata nodes THEN no LINT004 waiver cites
    T-0200 as pending
  evidence:
  - tests/test_gitio.py::TestRunArgv::test_kill_switch_refuses_without_spawning
threat: denial-of-service
component: null
---
Audit H2 (docs/audits/frob-blindspots-2026-07-23.md): five strata nodes (core,
fleet, tickets_ledger, stratamod, vet) waive LINT004 with reason "no real kill
switch around subprocess spawning yet -- T-0200 is the follow-on ticket to
build one". T-0200 is DONE (archived) and shipped
src/frob/process/_guard.py::guarded_subprocess_run, but only check/_python.py,
check/_ts.py, check/_native.py wired in. gitio.run_argv (the single git seam),
the serve daemon (spawning git every 20s in a background thread), and the
tickets lease git calls all bypass the guard -- so FROB_DISABLE_EXEC=1 is a
partial no-op while _guard.py's docstring promises it "genuinely stops EVERY
process this component spawns". Fix: route gitio.run_argv through
guarded_subprocess_run (which transitively covers serve+tickets since all git
IO flows through run_argv), verify no other subprocess call sites bypass it
(grep subprocess. outside _guard.py/gitio.py), DELETE the five stale waivers
from design/frob.strata (the mechanism exists; honest state is wired, not
pending), and add a test that FROB_DISABLE_EXEC=1 makes run_argv refuse.