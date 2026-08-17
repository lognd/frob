---
id: T-1777
title: Wire frob.tickets._leases.force_release_lease into a CLI verb
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets-lifecycle.md
- src/frob/tickets/_leases.py
- src/frob/app/worktree_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the lifecycle cluster (filing, review, scope/lease), so
    its scope now names docs/modules/tickets-lifecycle.md instead of the monofile
    every other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the lifecycle cluster (filing, review, scope/lease), so
    its scope now names docs/modules/tickets-lifecycle.md instead of the monofile
    every other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: src/frob/_cli_parsers/_ticket/**
  reason: 'T-1777: narrow to the single parser module this ticket actually edits,
    avoiding collision with T-2302''s live lease on _new.py under the same glob'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'T-1777: narrow to the single parser module this ticket actually edits,
    avoiding collision with T-2302''s live lease on _new.py under the same glob'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'T-1777: real minimal design puts the --force override on the ALREADY-shipped
    frob worktree release-lease verb (T-2175) rather than duplicating a second frob
    ticket lease release CLI surface -- worktree_runner.py is where force_release_lease
    is called from; _leases.py needed to thread an operator-supplied --reason into
    force_release_lease''s own WARNING log (a persisted ticket-model audit field is
    blocked by T-2302''s concurrent lease on _models.py, filed as a follow-up)'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: 'T-1777: real minimal design puts the --force override on the ALREADY-shipped
    frob worktree release-lease verb (T-2175) rather than duplicating a second frob
    ticket lease release CLI surface -- worktree_runner.py is where force_release_lease
    is called from; _leases.py needed to thread an operator-supplied --reason into
    force_release_lease''s own WARNING log (a persisted ticket-model audit field is
    blocked by T-2302''s concurrent lease on _models.py, filed as a follow-up)'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/config.py
  reason: 'T-1777: redesigned around the ALREADY-shipped frob worktree release-lease
    verb (T-2175) instead of a new frob ticket lease subcommand tree -- AppConfig/_cli_parsers/_ticket/ticket_runner
    dispatch are not touched by this design, and T-2302 holds a live cross-worktree
    lease on config.py/_new.py blocking them anyway'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'T-1777: redesigned around the ALREADY-shipped frob worktree release-lease
    verb (T-2175) instead of a new frob ticket lease subcommand tree -- AppConfig/_cli_parsers/_ticket/ticket_runner
    dispatch are not touched by this design, and T-2302 holds a live cross-worktree
    lease on config.py/_new.py blocking them anyway'
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'T-1777: redesigned around the ALREADY-shipped frob worktree release-lease
    verb (T-2175) instead of a new frob ticket lease subcommand tree -- AppConfig/_cli_parsers/_ticket/ticket_runner
    dispatch are not touched by this design, and T-2302 holds a live cross-worktree
    lease on config.py/_new.py blocking them anyway'
  actor: logan
  at: '2026-08-17'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob.tickets._leases.force_release_lease` (T-1743) is a working,
tested Python-API release path for an orphaned cross-worktree lease --
it removes `<common-dir>/frob-leases/<ticket-id>.json` unconditionally,
independent of the ticket's own declared scope, logging a WARNING
naming exactly what it released. It has no CLI entry point yet: T-1743
declared scope only covered `src/frob/tickets/_leases.py`,
`src/frob/app/ticket_runner/_query.py`, a test file, and
`docs/modules/tickets.md` -- wiring an actual `frob ticket lease
release <id>` verb needs an argparse subcommand
(`src/frob/_cli_parsers/_ticket/**`) plus a new `AppConfig` field
(`src/frob/app/config.py`) plus dispatch wiring
(`src/frob/app/ticket_runner/__init__.py`), none of which T-1743's
scope covered.

Plan: add a `frob ticket lease` subcommand group (`list`, `release
<id> [--force]`) that calls `force_release_lease`/`read_all_leases`
directly, refusing by default when the lease's own worktree liveness
probe still reads "present" (require `--force` to override an
apparently-live worktree -- matches T-1743's own doc note that this is
meant for a worktree an operator has JUDGED abandoned, not an
automatic decision) and printing the same worktree-provenance
`lease_holder_worktree` already computes for `--show-blocked`.
