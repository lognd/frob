---
id: T-0267
title: 'docs(dup): correct stale DUP001/DUP002 unwired claim in dup-sota-survey.md
  sec 0'
state: done
kind: docs
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/dup-sota-survey.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:grep -q "\"clones\"" src/frob/gates/__init__.py exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
T-0191's Done report: dup-sota-survey.md section 0 says DUP001/DUP002 are 'pure rule functions but NOT wired into frob.gates.__init__' -- stale since a3eef8d8 (2026-07-17), one day before the survey landed. dup_gate already calls the real smart find_clones pipeline and is registered as the opt-in 'clones' gate. Correct section 0's claim to describe the actual state (wired, opt-in via [dup].enforce, connection-pooled as of T-0191) so a future reader does not re-investigate an already-closed gap. (Note: T-draft-2a3adb6d, the T-0253 release-stamp follow-up, was resolved during T-0253's landing -- coordinator stamped 0.3.0 in that motion -- so it is dropped here.)