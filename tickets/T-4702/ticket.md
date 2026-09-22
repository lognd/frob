---
id: T-4702
title: Regenerate docs/commands from the final CLI surface (18 files for 51 verbs
  today) and report the drift in the owner-owned ~/.claude/refs/frob.md
state: in-progress
kind: docs
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4690
- T-4692
- T-4695
- T-4696
- T-4698
parent: T-4687
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/cli-regrouping.md
- tests/unit/test_docs_commands_coverage.py
- docs/commands/check.md
- docs/commands/cli-vocabulary.md
- docs/commands/cycle.md
- docs/commands/deploy.md
- docs/commands/exports.md
- docs/commands/format.md
- docs/commands/gitlog.md
- docs/commands/map.md
- docs/commands/narrative.md
- docs/commands/outline.md
- docs/commands/parse.md
- docs/commands/refactor.md
- docs/commands/release.md
- docs/commands/run.md
- docs/commands/scaffold.md
- docs/commands/sync-skills.md
- docs/commands/sys.md
- docs/commands/xref.md
- src/frob/docs/_command_pages.py
- src/frob/app/docs_runner.py
- src/frob/_cli_parsers/_core.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/commands/**
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/check.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/cli-vocabulary.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/cycle.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/deploy.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/exports.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/format.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/gitlog.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/map.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/narrative.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/outline.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/parse.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/refactor.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/release.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/run.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/scaffold.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/sync-skills.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/sys.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/xref.md
  reason: narrowing the broad docs/commands/** glob to every file except ticket.md,
    which collides with in-progress T-5132's live lease (points/tokens fields); regenerating
    everything else now, ticket.md once T-5132 releases it
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/docs/_command_pages.py
  reason: 'the ticket''s own preference: generate docs/commands from the argparse
    tree, wired so it cannot drift again silently -- a new generator module plus a
    small docs_runner.py flag to invoke it, mirroring the existing --sync-commands
    precedent for docs/modules/cli.md''s table'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/app/docs_runner.py
  reason: 'the ticket''s own preference: generate docs/commands from the argparse
    tree, wired so it cannot drift again silently -- a new generator module plus a
    small docs_runner.py flag to invoke it, mirroring the existing --sync-commands
    precedent for docs/modules/cli.md''s table'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/_cli_parsers/_core.py
  reason: 'the ticket''s own preference: generate docs/commands from the argparse
    tree, wired so it cannot drift again silently -- a new generator module plus a
    small docs_runner.py flag to invoke it, mirroring the existing --sync-commands
    precedent for docs/modules/cli.md''s table'
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.534.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2024
  new_length: 2024
designated_repro_test: null
acceptance:
- text: Given the live argparse tree, when the coverage test runs, then every top-level
    verb has a docs/commands entry and every docs/commands entry names a live verb
  evidence: []
- text: Given a planted verb with no doc and a planted doc with no verb, when the
    coverage test runs, then it fails on each -- the assertion is proven to fire in
    both directions
  evidence: []
- text: Given ~/.claude/refs/frob.md, when this ticket closes, then the Done report
    lists each stale spelling with file:line and replacement text and the file itself
    is unmodified
  evidence: []
threat: null
component: docs
labels:
- cli-debloat
- points-2
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4702
branch: t-4702
---
POINTS: 2. Parent story T-4687. blocked_by T-4690, T-4692, T-4695, T-4696,
T-4698 -- it documents the FINAL surface, so it cannot start until the surface
has stopped moving.

MEASURED 2026-09-19: docs/commands/ holds 18 files (check, cli-vocabulary,
cycle, deploy, exports, format, gitlog, map, narrative, outline, parse,
refactor, release, scaffold, sync-skills, sys, ticket, xref) against 51
top-level verbs and 54 ticket subverbs. It documented a third of the surface
before this story started, and this story moves or deletes most of what it does
cover (cycle, exports, gitlog, map, outline, parse, xref all move).

WORK:
1. Regenerate docs/commands/ from the FINAL surface. Prefer generating it from
   the argparse tree over hand-writing 18 more files -- if a generator does not
   exist, write one and wire it so the docs cannot drift again silently. Say in
   the Done report whether it was generated or hand-written and why.
2. Update docs/commands/cli-vocabulary.md and docs/design/cli-regrouping.md:
   the latter is the design doc that JUSTIFIED the four group verbs T-4690
   deletes. It must record that the regrouping was reverted, and why (the
   groups added four names and removed zero).
3. `git grep` every removed spelling across docs/ and fix the citations.

OUT OF SCOPE, REPORT ONLY: ~/.claude/refs/frob.md is the OWNER'S file. Do not
edit it. The Done report must list, line by line, the edits it needs: each stale
verb spelling, its file:line, and the replacement text -- so the owner can apply
them without re-deriving anything.

POSITIVE CONTROL (acceptance): a test that walks the live argparse tree and
asserts every top-level verb has a docs/commands entry AND every docs/commands
entry names a live verb -- it must FAIL if a verb is added without docs or a
doc outlives its verb. Plant one of each in the test fixture to prove the
assertion fires in both directions.

FILES (declared scope):
  docs/commands/**
  docs/design/cli-regrouping.md
  tests/unit/test_docs_commands_coverage.py (new)
