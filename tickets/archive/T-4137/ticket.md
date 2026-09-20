---
id: T-4137
title: Migrate thin-wrapper Makefile targets to frob subcommands
state: dropped
kind: docs
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- Makefile
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
Found while working T-4131 (README/community-docs release presentation).

The owner directive (T-1382) says workflows belong in frob subcommands, not
GNU-make recipes. Makefile audit for T-4131 found a MIX, not a clean answer
either way:

REAL LOGIC (leave alone): coverage: (native staleness + reconcile/doctor
sequencing before "frob coverage --full"), the historical crash-recovery
narrative comments document why; deploy-audit: (VirtualBox harness with
required-var checks); test-fast: (--testmon incremental rerun, no "frob
test" equivalent yet, disclosed gap per T-2244).

THIN WRAPPERS (candidates for removal/further migration): format,
lint, lint-fix, typecheck, sync-skills, pool-warm/pool-lease/
pool-status, core, install-tool, coverage-fast are each 1-3 line
delegations straight to "uv run frob <subcommand>" (T-2244/T-0877 already
did this migration for their bodies) -- the Makefile target itself is now
pure indirection with no logic of its own, exactly the "second name for
the same operation" duplication T-1382 warns against.

Proposal: either (a) remove the thin-wrapper targets and document the
"uv run frob ..." commands directly (CONTRIBUTING.md already does this),
or (b) leave them as documented aliases but mark them clearly as
deprecated/wrapper-only in a comment, so nobody adds real logic to one by
mistake. Do not delete the Makefile itself -- coverage/deploy-audit/
test-fast still carry real logic other tooling depends on.

## Drop reason
- 2026-09-07: duplicate of T-1382 (Decouple frob from the Makefile), which already tracks migrating the Makefile's thin-wrapper targets to frob subcommands; T-4131's Makefile investigation is a data point for T-1382, not a new ticket
