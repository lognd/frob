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
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
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
- src/frob/app/config.py
- src/frob/app/_config_external.py
- docs/commands/ack.md
- docs/commands/agent.md
- docs/commands/claude.md
- docs/commands/clean.md
- docs/commands/coverage.md
- docs/commands/doctor.md
- docs/commands/explore.md
- docs/commands/fleet.md
- docs/commands/graph.md
- docs/commands/mutate.md
- docs/commands/natives.md
- docs/commands/perf.md
- docs/commands/pool.md
- docs/commands/process.md
- docs/commands/profile.md
- docs/commands/registry.md
- docs/commands/serve.md
- docs/commands/status.md
- docs/commands/test.md
- docs/commands/verify.md
- docs/commands/vet.md
- docs/commands/worktree.md
- docs/index.md
- docs/modules/app.md
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
- op: add
  glob: src/frob/app/config.py
  reason: the new --sync-command-pages flag needs its bool field declared on AppConfig
    and added to from_external's field-copy allowlist (the T-4690 gap found before
    -- doctor_whereis silently no-op'd without it)
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/app/_config_external.py
  reason: the new --sync-command-pages flag needs its bool field declared on AppConfig
    and added to from_external's field-copy allowlist (the T-4690 gap found before
    -- doctor_whereis silently no-op'd without it)
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/ack.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/agent.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/claude.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/clean.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/coverage.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/doctor.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/explore.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/fleet.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/graph.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/mutate.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/natives.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/perf.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/pool.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/process.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/profile.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/registry.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/serve.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/status.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/test.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/verify.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/vet.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/commands/worktree.md
  reason: 22 new generated stub pages from frob docs --sync-command-pages, closing
    the doc-coverage gap for every live verb that had none
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/index.md
  reason: 22 new docs/commands stub pages generated by this ticket need a docs/index.md
    link or DOC001 refuses them as orphaned
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/modules/app.md
  reason: frob:doc home for _command_pages.py's 4 new public symbols (frob.docs library
    section)
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
evidence:
- tests/unit/test_docs_commands_coverage.py::TestLiveSurfaceMatchesDocsCommands::test_every_live_verb_has_a_doc_page
- tests/unit/test_docs_commands_coverage.py::TestLiveSurfaceMatchesDocsCommands::test_every_doc_page_names_a_registered_verb
- tests/unit/test_docs_commands_coverage.py::TestAssertionFiresInBothDirections::test_planted_verb_with_no_doc_is_caught
- tests/unit/test_docs_commands_coverage.py::TestAssertionFiresInBothDirections::test_planted_doc_with_no_verb_is_caught
- tests/unit/test_docs_commands_coverage.py::TestSyncMissingCommandPages::test_generate_command_page_renders_help_text_and_usage
- tests/unit/test_docs_commands_coverage.py::TestSyncMissingCommandPages::test_sync_writes_only_missing_pages_and_never_overwrites
designated_repro_test: null
acceptance:
- text: Given the live argparse tree, when the coverage test runs, then every top-level
    verb has a docs/commands entry and every docs/commands entry names a live verb
  evidence:
  - tests/unit/test_docs_commands_coverage.py::TestLiveSurfaceMatchesDocsCommands::test_every_live_verb_has_a_doc_page
  - tests/unit/test_docs_commands_coverage.py::TestLiveSurfaceMatchesDocsCommands::test_every_doc_page_names_a_registered_verb
  - tests/unit/test_docs_commands_coverage.py::TestSyncMissingCommandPages::test_generate_command_page_renders_help_text_and_usage
  - tests/unit/test_docs_commands_coverage.py::TestSyncMissingCommandPages::test_sync_writes_only_missing_pages_and_never_overwrites
- text: Given a planted verb with no doc and a planted doc with no verb, when the
    coverage test runs, then it fails on each -- the assertion is proven to fire in
    both directions
  evidence:
  - tests/unit/test_docs_commands_coverage.py::TestAssertionFiresInBothDirections::test_planted_verb_with_no_doc_is_caught
  - tests/unit/test_docs_commands_coverage.py::TestAssertionFiresInBothDirections::test_planted_doc_with_no_verb_is_caught
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