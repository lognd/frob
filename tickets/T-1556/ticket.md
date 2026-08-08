---
id: T-1556
title: 'cli hygiene remainder: warning collapse, read-only check --ticket, close porcelain,
  cli-hygiene principles doc (T-1271 split)'
state: queued
kind: ux
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/gates/_waive_lease.py
- docs/design/cli-hygiene.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ticket_runner/_close_cmd.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive_lease.py
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-hygiene.md
  reason: 'Four criteria, four concrete real anchors: scope-closure warning collapse
    (the observed flood site) in _new.py/_mutate.py, check --ticket lease enforcement
    in _waive_lease.py, close-porcelain next-command hints in _close_cmd.py (already
    carries _close_failure_hint), and a new cli-hygiene principles doc. No glob; the
    implementer will scope-add narrowly further once each piece is open, same as every
    other narrowed ticket this session.'
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
acceptance:
- text: GIVEN a command emits repeated advisory warnings (scope-closure on ticket
    new can flood thousands of lines) THEN they collapse to a counted summary with
    a --verbose escape hatch -- signal is never drowned
  evidence: []
- text: GIVEN a read-only invocation (check --ticket for review, show, brief) THEN
    it never requires a lease or mutates state -- reviewers repeatedly could not re-verify
    gate claims because check --ticket demands a lease
  evidence: []
- text: GIVEN a multi-step workflow (close needs start, done-report, evidence, accepts)
    THEN each refusal names the exact next command AND a single porcelain verb exists
    that sequences the happy path; hidden optional arguments that change behavior
    (e.g. renumber's positional-only contract) are documented in --help with examples
  evidence: []
- text: GIVEN the audit lands THEN a short cli-hygiene principles doc exists in docs/design/
    and a checklist test (or gate rule) verifies new parsers against it (every flag
    help string states its default; no flag silently changes another flag's meaning)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Split from T-1271: its dispatch delivered criterion 0 (enum-valued flag errors list every valid value inline) with bound evidence; these four criteria were not implemented in that worktree and were drafted there as T-1557, which cannot survive a land preview (land-splice draft-loss class). Filed as a real main-side ticket so T-1271 can land its delivered portion with an honest acceptance trail.