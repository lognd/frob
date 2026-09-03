---
id: T-3590
title: 'Error burn-down: clear the 73 live frob check errors (DRIFT/DOC cluster dominant)'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/release.md
- docs/index.md
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/check_runner.py
- src/frob/tickets/_land_queue.py
- src/frob/tickets/_land_squash.py
- src/frob/verify/_bisect.py
- tests/test_ticket_leases.py
- tests/test_check_runner.py
- tests/unit/verify/test_bisect.py
- docs/design/macos-portability.md
- docs/design/land-splice-test-then-impl.md
- docs/design/ledger-mirror-batching.md
- frob.lock
- tickets/archive/T-1809/ticket.md
- tickets/archive/T-1969/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: burn-down umbrella tracking ticket spanning DOC/DRIFT/ARCH/COV/PII/LARGE/OPAQUE/TICK/REF/REL
  families across many unrelated files; scope is added per-family as each fix lands
scope_changes:
- op: add
  glob: docs/guides/release.md
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/index.md
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/app/check_runner.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/tickets/_land_queue.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/verify/_bisect.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/test_ticket_leases.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/test_check_runner.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/unit/verify/test_bisect.py
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/design/macos-portability.md
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/design/land-splice-test-then-impl.md
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/design/ledger-mirror-batching.md
  reason: DOC/DRIFT/COV/PII/OPAQUE burn-down fixes span all these files -- stale test-rename
    directives, missing doc anchors, opaque argparse waiver, PII false-positive waiver
  actor: logan
  at: '2026-08-31'
- op: add
  glob: frob.lock
  reason: frob ack lockfile entries + archived-ticket evidence re-pointing for the
    check_runner.py test rename orphaning
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tickets/archive/T-1809/ticket.md
  reason: frob ack lockfile entries + archived-ticket evidence re-pointing for the
    check_runner.py test rename orphaning
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tickets/archive/T-1969/ticket.md
  reason: frob ack lockfile entries + archived-ticket evidence re-pointing for the
    check_runner.py test rename orphaning
  actor: logan
  at: '2026-08-31'
body_changes:
- mode: append
  reason: 'unblock BUG002 land gate: this ticket makes no behavior changes, only directive/waiver/doc
    corrections'
  actor: logan
  at: '2026-08-31'
  old_length: 499
  new_length: 875
evidence:
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_identity_less_environment_falls_back_to_throwaway_git_identity
- tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding::test_empty_candidates_refuses
- tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding::test_converges_to_the_known_culprit_within_log2_n_steps
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-08-31 on main via budgeted frob check --json: 73 live errors led by DRIFT002 24, DRIFT001 10, DOC007 8, CLAUDE001 5. Re-measure per family with frob check --only <family> --budget 300, fix real findings at their source (DRIFT = re-verify the doc paragraph then frob ack, never blanket-ack; DOC = fix the pointer or the doc; CLAUDE001 = frob claude sync drift; TICK004 = queue hygiene), and record the remainder per rule with disposition if zero is not honestly reachable in one ticket.

frob:waive BUG002 reason="burn-down umbrella ticket: directive/waiver/doc corrections (stale test-name citations after T-3600s rename, missing doc anchors, argparse OPAQUE001 false-positive waiver, PII012 git-config-key-name false-positive waiver, TICK004 triage) -- no code behavior change for a mutation-killing test to target, so no evidence can genuinely fail at parent"