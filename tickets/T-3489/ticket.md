---
id: T-3489
title: T-2642 changelog generator emits a DOC006 symbol pointer into land-owned changelog.d/T-2691.md,
  failing the live-repo DOC004/DOC006 test
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
- tests/unit/test_ticket_runner_land_release.py
- changelog.d/T-2691.md
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: changelog.d/**
  reason: T-3489 only touches the existing T-2691 fragment for repair, not the whole
    directory
  actor: logan
  at: '2026-08-30'
- op: add
  glob: changelog.d/T-2691.md
  reason: T-3489 only touches the existing T-2691 fragment for repair, not the whole
    directory
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: root-cause fix lives in _docptr.py (a DOC006 exemption for changelog.d/,
    matching the existing CHANGELOG.md archival precedent), not in the generator
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_docptr_gate.py
  reason: adding a changelog.d/ exemption unit test alongside the existing archival-record
    tests in this file
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33311990183 (macos-latest and, by the same
mechanism, ubuntu-latest on the next run), HEAD 986f8671c:
  tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
    DOC006: file changelog.d/T-2691.md line 2 -- a code symbol pointer that does not resolve.
T-2642 changed the changelog fragment generator (_changelog_note_for_ticket in
src/frob/app/ticket_runner/_land_cmd.py) to prefer the Done report's WHY
prose; T-2691's Done report mentioned a dotted symbol path, so the generated
fragment now carries a DOC006-shaped pointer. changelog.d/ is LAND-OWNED
(worktree edits to it are reset), so the fix is in the GENERATOR: sanitize
the note (wrap dotted paths in backticks the gate treats as literal, or
strip them) AND add changelog.d/** to DOC006's exemptions if release notes
are not meant to carry resolvable pointers -- decide which from the DOC006
docstring and state it. Also repair the existing changelog.d/T-2691.md via
the sanctioned path (regenerate through the generator, never a hand edit
that the next land resets). Must-fire: a Done report containing
`frob.app.telemetry._state` yields a fragment with zero DOC006 findings.

## Unblock log
- 2026-08-30: unblocked by T-2450 -- root-cause fix is a DOC006 exemption for changelog.d/ in _docptr.py, matching the existing CHANGELOG.md/tickets-archive.md archival-record precedent -- no longer needs to touch src/frob/app/ticket_runner/_land_cmd.py, so the T-2450 lease collision is moot
