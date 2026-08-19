---
id: T-2584
title: CYCLE001 findings never pass through the waiver pipeline -- frob:waive CYCLE001
  is silently inert
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/__init__.py
- src/frob/check/_python.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while working T-2363 (declare-vs-fix decision on the 160-node serve/stats/tickets/testing/app import cycle): CYCLE001 is listed among the known/waivable gate rules in src/frob/gates/_waive.py (T-2364's own comment there: 'import-cycle finding identity... was previously emitted with code=None/file=None, making a real cycle unownable (unfileable, unwaivable, unattributable to a commit)'), implying a frob:waive CYCLE001 comment should suppress a matching finding.

Measured directly: it does not. frob check --only cycle's frob-cycle tool (src/frob/check/_python.py::_run_cycle, wired in src/frob/check/__init__.py) builds its Diagnostic list and returns it straight into the ToolResult with zero calls into src/frob/gates/_waive.py or src/frob/gates::_apply_waivers anywhere in either check/__init__.py or check/_python.py (grepped both files for 'waive' -- zero hits in check/__init__.py). _apply_waivers only runs over Violation objects built by the separate frob.gates rule-check pipeline (src/frob/gates/__init__.py:7961 and a second call site in check/_python.py:645 for ARCH001 specifically) -- CYCLE001's Diagnostics never enter that stream.

Reproduced: added a # frob:waive CYCLE001 reason="..." comment at the top of src/frob/__init__.py (the representative file of the live 160-node CYCLE001 error) and re-ran frob check --only cycle --no-cache -- the error still reports, unchanged, byte-for-byte identical diagnostic text before and after the comment. Reverted before landing (an inert waiver would also likely trip WAIVE004 as a dead directive, since CYCLE001 never appears in the Violation stream WAIVE004 scans either).

Impact: any CYCLE001 finding is currently permanently unsuppressible by the documented mechanism -- a repo-owner-approved 'declare this coupling and move on' decision (exactly what T-2363 needed for its 160-node SCC) has no landable form today.

Acceptance: frob check --only cycle's diagnostics are routed through the same _match_waiver/_apply_waivers spine gates violations already use (or an equivalent CYCLE001-aware waiver check added to _run_cycle/check/__init__.py), such that a # frob:waive CYCLE001 reason="..." comment placed in the representative file suppresses that specific cycle's finding on a subsequent frob check --only cycle run. Positive control: plant a small synthetic 2-3 file cycle fixture, confirm it reports CYCLE001 unwaived, add a matching frob:waive CYCLE001 comment, confirm it then reports clean; negative control: confirm an unrelated file's frob:waive CYCLE001 comment does NOT suppress a different cycle's finding.