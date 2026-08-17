---
id: T-1780
title: 'Split docs/modules/tickets.md: 35 open tickets name it, so any one blocks
  the other 34'
state: done
kind: feature
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- docs/index.md
- design/frob.strata
- docs/commands/scaffold.md
- docs/guides/agent-playbook.md
- docs/guides/coordinator-scripts.md
- docs/guides/extending/ticket-kinds-states.md
- docs/guides/install.md
- docs/modules/app.md
- docs/modules/cli.md
- docs/modules/gates.md
- docs/modules/graph.md
- docs/modules/serve.md
- docs/modules/tickets-data-storage.md
- docs/modules/tickets-landing.md
- docs/modules/tickets-lifecycle.md
- docs/modules/tickets-merge-driver.md
- docs/modules/tickets-verify-sweep.md
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/check_runner.py
- src/frob/app/graph_runner.py
- src/frob/app/profile_runner.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/verify_runner.py
- src/frob/gates/_fix_engine_shared.py
- src/frob/gates/_mutation_evidence.py
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_waive.py
- src/frob/serve/_daemon.py
- src/frob/tickets/_archive.py
- src/frob/tickets/_brief.py
- src/frob/tickets/_draft_finalize.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_force_override.py
- src/frob/tickets/_journal.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land_ledger_merge.py
- src/frob/tickets/_land_merge.py
- src/frob/tickets/_land_queue.py
- src/frob/tickets/_land_release.py
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_verify.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_live_tracker.py
- src/frob/tickets/_models.py
- src/frob/tickets/_mutation_evidence.py
- src/frob/tickets/_mutation_sweep_queue.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_profile.py
- src/frob/tickets/_provisional.py
- src/frob/tickets/_reconcile.py
- src/frob/tickets/_reporting.py
- src/frob/tickets/_scope.py
- src/frob/tickets/_store.py
- src/frob/tickets/_worktree_guard.py
- src/frob/tickets/clipboard.py
- src/frob/verify/_attribution.py
- src/frob/verify/_backpressure.py
- src/frob/verify/_quarantine.py
- src/frob/verify/_selection.py
- src/frob/verify/_watermark.py
- src/frob/verify/_worker.py
- src/frob/yaml_io.py
- tests/test_gates_tickets_hygiene.py
- tests/test_ticket_merge_driver.py
- tests/test_tickets_organization.py
- tests/test_tickets_priority.py
- tests/test_tickets_tiers.py
evidence_scope:
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/commands/scaffold.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/extending/ticket-kinds-states.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/install.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/app.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/cli.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/graph.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/serve.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-merge-driver.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/graph_runner.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/profile_runner.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/gates/_fix_engine_shared.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/gates/_mutation_evidence.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/serve/_daemon.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_archive.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_brief.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_draft_finalize.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_force_override.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_journal.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_finalize.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_ledger_merge.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_merge.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_queue.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_release.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_land_verify.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_live_tracker.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_mutation_evidence.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_mutation_sweep_queue.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_profile.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_provisional.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_scope.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_store.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/tickets/clipboard.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_attribution.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_backpressure.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_selection.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_watermark.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_worker.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/yaml_io.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_gates_tickets_hygiene.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_ticket_merge_driver.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_tickets_organization.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_tickets_priority.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_tickets_tiers.py
  reason: 'T-1780: mechanical frob:doc anchor repointing to the new split files, and
    split-file creation itself, necessarily follows from the docs/modules/tickets.md
    split -- same class as CLI-wiring-implicitly-in-scope for a FEATURE ticket'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged
- tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`docs/modules/tickets.md` is the single largest throughput limiter on
this repo's queue. Measured: **35 open tickets name it in their scope.**

Because scope is also the lease, any one of those 35 blocks the other 34.
Observed continuously this session -- at every check, that file had a live
lease, and tickets waited behind it that shared no code at all:

- T-1720 (land should auto-rebase the worktree) and T-1771 (uv.lock
  coherence) sat blocked through multiple dispatch cycles, held first by
  T-1613/T-1743, then by T-1750/T-1779, never by anything they overlapped
  with in code.
- A five-agent wave could only ever run one agent on ledger/land work,
  because every such ticket needs this doc.
- Groups had to be assembled around "who gets tickets.md" rather than
  around the work, which is the opposite of how dispatch should be
  planned.

The file has grown to hold: the ticket lifecycle, the land pipeline, the
post-land sweep, the rapid profile, deferred verification, worktree
leases, the ledger v2 layout, the release quartet, worktree liveness, and
more. Those are separate subsystems that happen to share a doc.

SPLIT IT, one file per concern the tickets actually cluster around.
Suggested seams, but measure before committing to them -- group the 35
tickets by which SECTION they cite and let that drive the split:

- `docs/modules/ticket-lifecycle.md` (states, transitions, evidence,
  done reports)
- `docs/modules/land.md` (the land pipeline, squash/splice, release
  quartet, land-owned files)
- `docs/modules/verification.md` (post-land sweep, deferred verification,
  the watermark epic, rapid profile)
- `docs/modules/worktrees.md` (leases, liveness, isolation, sweep)
- `docs/modules/ledger.md` (v1/v2 layout, merge driver, archive)

REQUIREMENTS:

1. Every `frob:doc` anchor pointing into the old file must resolve after
   the split. There are many. This is exactly what DOC006/COV005 exist to
   catch, so a clean `frob check` is the completeness proof -- do not
   hand-audit and hope.
2. Update the SCOPE of the affected open tickets to name their new doc
   home. That is the entire point: if the 35 tickets keep naming one
   file, splitting the file changes nothing.
3. Do NOT leave `docs/modules/tickets.md` as a stub that re-includes the
   others. A stub everything still points at reproduces the lease
   exactly.
4. `docs/index.md` and any cross-references get updated in the same
   change.

MARK THIS `runs-last`. T-1613 landed that marker today for precisely this
shape: an operation that touches something everything else depends on,
and is safe only when nothing else is in flight. Splitting a file 35 open
tickets reference while any of them is being worked would produce exactly
the merge carnage the marker exists to prevent. Set it with
`frob ticket runs-last <id> on` and let the queue enforce the quiet
window rather than a coordinator remembering to.

This is a documentation change with no behavioural effect, and it will
unblock more parallel work than any code fix currently in the queue.

## Done report

Read T-2134 first, as instructed: it questions the SEPARATE root
`tickets.md` monofile (the pre-v2-migration ledger), not this doc file --
unrelated, no overlap, no change to what "split" means here.

Measured the seams from the document's own parsed H2 heading structure
(88 real headings; a second pass over ALL `#`-prefixed matches including
fenced code-comment pseudo-headers, matching the exact regex/slugify
`frob.gates._docptr._heading_slugs`/`frob.graph.dsl.slugify` use, so the
split boundaries and every anchor's post-split slug are provably
byte-identical to what gate:DOC already checks -- a token/grammar
approach, not a byte-offset one). Five subject clusters, matching the
document's own natural boundaries (confirmed by where each of the 61
`frob:doc`-referenced anchors landed):

- `docs/modules/tickets-lifecycle.md` -- filing, review, scope/lease,
  organization, state machine, provisional ids, promote (1420 lines)
- `docs/modules/tickets-landing.md` -- `frob ticket land` and its whole
  critical path (2297 lines)
- `docs/modules/tickets-verify-sweep.md` -- verification watermark,
  backpressure, quarantine, rapid profile (1215 lines)
- `docs/modules/tickets-merge-driver.md` -- the git merge driver (169
  lines)
- `docs/modules/tickets-data-storage.md` -- data models, storage
  internals, remaining organization primitives (1212 lines)

`docs/modules/tickets.md` itself keeps the overview, storage summary, and
Public API index (556 lines) plus a pointer section to the five split
files -- not a stub that re-includes them (requirement 3): every section
moved OUT bodily, nothing is duplicated.

Repointed every `frob:doc`/doc-cross-reference anchor whose target moved:
346 replacements across 66 source/test/doc files (mechanical, driven
directly by the split -- same class as CLI-wiring-implicitly-in-scope for
a FEATURE ticket, so added to scope via `frob ticket scope --add` rather
than touched silently) plus one `design/frob.strata` anchor and a small
prose cross-reference in `docs/modules/app.md`/`docs/modules/gates.md`/
`docs/modules/serve.md` that a naive regex missed (verified by re-grepping
for `docs/modules/tickets\.md#` afterward: every remaining hit either
targets the kept-in-index Public API section or is one of 5 anchors that
were ALREADY broken before this split -- no matching heading either way,
pre-existing DOC006-adjacent drift, unchanged by this ticket, listed
below rather than silently left).

Requirement 2 (the actual point): 8 open tickets named
`docs/modules/tickets.md` in their filed scope at start; re-measured after
finding the current queue, not trusting the ticket's own originally-filed
count of 35 (queue moved under 150+ lands since 2026-08-07). `frob ticket
scope --remove docs/modules/tickets.md --add <new home>` for the 7 that
were not T-1780 itself, each pointed at the file matching its own other
scoped code (T-1691/T-1696 -> verify-sweep, T-1748/T-1860/T-2166 ->
landing, T-1777/T-2116 -> lifecycle). Re-measured: 1 open ticket now names
`docs/modules/tickets.md` (T-1780 itself).

`design/frob.strata` and each of the 7 sibling tickets' scope-closure
checks produced non-blocking WARNINGS only (scope's own closure rule
wanting every doc-target's OTHER unrelated targets also in scope, an
inherent property of `design/frob.strata` naming many unrelated doc
targets) -- confirmed via `frob ticket land --dry-run` that these do not
block landing; the actual land-blocking gate reached was the ordinary
missing-evidence check, resolved below.

Pre-existing broken anchors, unchanged by this split (do not re-derive
this list; it was correct before and after):
- `#check-repro-post-land-limitation-t-2025` (2 hits,
  `_verify.py`/`_mutation_evidence.py`)
- `#frob-ticket-brief` (missing its `-t-0568` suffix, 1 hit)
- `#review-record` (no matching heading, 1 hit)
- `#scope-lease-model`/`#scope-lease-mutation` (missing suffix / no
  matching heading, 2 hits)

Evidence: `frob check --ticket T-1780 --only docanchor --only doclink
--only docmake --only docstatus` -- 0 errors both before writing this
report and after the ledger-scope commits above (re-run, not assumed).
`gate:FMT` clean after `frob fmt` rewrapped the frob:doc directive
comments the longer split-file names pushed past 88 cols (one prose
docstring line in `src/frob/tickets/_land.py` needed a manual wrap; fmt
only rewraps directive comments). `frob fmt` ran repo-wide once by
mistake (70 files); reverted everything outside this ticket's own
touched set (49 unrelated `.strata`/gates files) before committing, kept
only the 20 files it correctly fixed among ones this ticket already
touched.

`gate:DRIFT` (`_finish_only_if_already_landed`) and the Claude-config
drift note are both pre-existing, unrelated to any file this ticket
touches (confirmed via `git diff` -- neither function's body is anywhere
near my edits) -- not caused by this change.

Evidence: tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged,
tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
(the DOC002/DOC006 anchor-resolution mechanism this whole split's
correctness rests on).

Filed: none -- the 5 pre-existing broken anchors above are drift that
predates this ticket and is unrelated to its split (no heading ever
existed for any of them, before or after); noting them here satisfies
disclosure without opening a new ticket for pre-existing rot outside
T-1780's own scope.

Gates: frob check --ticket T-1780 --only docanchor/doclink/docmake/
docstatus/fmt clean (0 errors). gate:SCOPE surfaces 7 SCOPE002
"under-capture" NOTES against the wide mechanical-touch scope (the
whole-file call-graph closure these large already-existing modules
trigger once declared in scope) and 2186 scope-closure WARNINGS against
`design/frob.strata` -- both non-blocking, confirmed via `frob ticket
land --dry-run` reaching the ordinary evidence gate, not a scope refusal.
