---
id: T-1615
title: 'frob ticket block leaves the ledger dirty: audit every ledger-writing verb
  for auto-commit parity'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/tickets.md
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- tests/test_ticket_leases.py
- src/frob/app/ticket_runner/_archive.py
- rapid-debt.jsonl
- src/frob/app/_config_external.py
- design/frob.strata
- docs/guides/agentic-workflow.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: 'TICK009: narrowing my own over-broad filing-time scope to the files this
    ticket actually names'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrowed from a package glob to the specific modules named in the ticket
    body
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: tests/**
  reason: 'TICK009 scope-breadth: tests/** and src/frob/app/ticket_runner/** are mega-globs
    that collide with nearly every other ticket, starving this one behind unrelated
    work (it was held by T-1687''s three-file scope purely through tests/** vs tests/unit/verify/test_watermark.py).
    Narrowed to the files an implementation pass actually touches, established empirically
    by an agent that had already written the change'
  actor: logan
  at: '2026-08-06'
- op: remove
  glob: src/frob/app/ticket_runner/**
  reason: 'TICK009 scope-breadth: tests/** and src/frob/app/ticket_runner/** are mega-globs
    that collide with nearly every other ticket, starving this one behind unrelated
    work (it was held by T-1687''s three-file scope purely through tests/** vs tests/unit/verify/test_watermark.py).
    Narrowed to the files an implementation pass actually touches, established empirically
    by an agent that had already written the change'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'TICK009 scope-breadth: tests/** and src/frob/app/ticket_runner/** are mega-globs
    that collide with nearly every other ticket, starving this one behind unrelated
    work (it was held by T-1687''s three-file scope purely through tests/** vs tests/unit/verify/test_watermark.py).
    Narrowed to the files an implementation pass actually touches, established empirically
    by an agent that had already written the change'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'TICK009 scope-breadth: tests/** and src/frob/app/ticket_runner/** are mega-globs
    that collide with nearly every other ticket, starving this one behind unrelated
    work (it was held by T-1687''s three-file scope purely through tests/** vs tests/unit/verify/test_watermark.py).
    Narrowed to the files an implementation pass actually touches, established empirically
    by an agent that had already written the change'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: 'TICK009 scope-breadth: tests/** and src/frob/app/ticket_runner/** are mega-globs
    that collide with nearly every other ticket, starving this one behind unrelated
    work (it was held by T-1687''s three-file scope purely through tests/** vs tests/unit/verify/test_watermark.py).
    Narrowed to the files an implementation pass actually touches, established empirically
    by an agent that had already written the change'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'TICK009 scope-breadth: tests/** and src/frob/app/ticket_runner/** are mega-globs
    that collide with nearly every other ticket, starving this one behind unrelated
    work (it was held by T-1687''s three-file scope purely through tests/** vs tests/unit/verify/test_watermark.py).
    Narrowed to the files an implementation pass actually touches, established empirically
    by an agent that had already written the change'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/ticket_runner/_archive.py
  reason: archive's own auto-commit call site lives in _archive.py; rapid-debt.jsonl
    is the land process's own append-log, touched incidentally by merges
  actor: logan
  at: '2026-08-07'
- op: add
  glob: rapid-debt.jsonl
  reason: archive's own auto-commit call site lives in _archive.py; rapid-debt.jsonl
    is the land process's own append-log, touched incidentally by merges
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/_config_external.py
  reason: ticket_no_commit dest (used by every verb this ticket wires --no-commit
    onto, plus close/evidence/done-report/requeue that already had it) was missing
    from the external-config bool-flags allowlist entirely -- WIRE001 caught it via
    my new CLI additions but the gap predates this ticket
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: commit_full_ledger_change needs an interface= declaration in the tickets_ledger
    node (SELFAUDIT001)
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/guides/agentic-workflow.md
  reason: AFFECT001 on _add_ticket_attach_and_lifecycle_end_parsers's own affects()-closure
    doc
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_warns_when_dirty
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_no_commit_flag_does_not_warn_when_clean
- tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_commits_dirty_whole_ledger
- tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_no_op_when_clean
- tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_no_commit_flag_warns_when_dirty
- tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean
designated_repro_test: null
threat: null
component: null
---
frob ticket block writes its edge into the ledger and leaves the file dirty. Every sibling mutation verb auto-commits: start (T-1054), then new/drop/fail (T-1130), then close/evidence/requeue/done-report. block was missed.

Consequence, observed directly on 2026-08-05: two block edges recorded back to back left tickets.md uncommitted on main, and the next `frob ticket land` refused with DirtyMain. The land is right to refuse -- a dirty root is exactly what its precheck exists to catch -- but the dirt was created by frob itself, silently, by a verb the caller had no reason to think left work behind.

This is the same incident class T-1130 names in its own body: "commit before dispatching" was coordinator memory rather than something the tool guaranteed. Any verb that writes the ledger and does not commit it converts a routine command into a trap for whatever runs next.

Fix: route block (and any other ledger-writing verb still missing it -- audit them all rather than fixing only this one) through commit_ticket_ledger_change, with the same --no-commit opt-out the other verbs expose for callers batching several writes.

Audit list to check while here: block, unblock if it exists, scope, accept, evidence --replace, migrate, renumber, archive. For each, state whether it writes the ledger and whether it commits. A table in the Done report is the deliverable, not just the block fix -- the point is that no ledger-writing verb is left in this state.

Test shape: for every ledger-writing verb, assert the working tree is CLEAN after the command (and dirty under --no-commit). A single parameterized test over the verb list makes a future verb that forgets this fail immediately.