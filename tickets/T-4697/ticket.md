---
id: T-4697
title: 'frob narrative: bulk mode over a file or directory with --apply (today it
  is one block per invocation; 507 measured runs need a sweep)'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4691
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/commands/narrative.md
- tests/narrative
- src/frob/narrative/_migrate.py
- src/frob/narrative/_bulk.py
- src/frob/narrative/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/narrative
  reason: T-4546 leases src/frob/narrative/_cli.py; narrow to non-leased files, CLI
    wiring deferred to Done report
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/narrative/_migrate.py
  reason: T-4546 leases src/frob/narrative/_cli.py; narrow to non-leased files, CLI
    wiring deferred to Done report
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/narrative/_bulk.py
  reason: T-4546 leases src/frob/narrative/_cli.py; narrow to non-leased files, CLI
    wiring deferred to Done report
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/narrative/__init__.py
  reason: T-4546 leases src/frob/narrative/_cli.py; narrow to non-leased files, CLI
    wiring deferred to Done report
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: given a fixture directory of three files citing a live ticket, an archived
    ticket, and no ticket, when 'frob narrative move <dir> --apply' runs, then the
    first two blocks are in their ticket bodies with one-line pointers left behind
    and the third is SKIPPED and reported, never deleted
  evidence: []
- text: given that sweep has run once, when --apply runs a second time, then nothing
    changes in any file or ticket body (idempotency, T-2994 constraint 4)
  evidence: []
- text: given a block citing an ARCHIVED ticket, when --apply runs, then the append
    lands on the archived path and 'frob ticket list' exits 0 afterwards (T-2994 constraint
    3)
  evidence: []
- text: given the existing 'file line' positional form, when this lands, then it still
    works unchanged as the per-block escape hatch
  evidence: []
- text: given --apply is omitted, when a directory is swept, then the plan is printed
    and neither source nor ledger is written
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TOOL leaf of T-4691. This is NOT a "verify and document" leaf -- measured, the
bulk mode does not exist.

MEASURED 2026-09-19: `frob narrative --help` exposes exactly one subverb, `move`,
and `frob narrative move --help` is:
    frob narrative move [-h] [--keep-file KEEP_FILE] --reason REASON [--dry-run]
                        file line
One FILE, one 1-indexed LINE, one block, one invocation. There is no directory
argument, no `--apply`, no sweep. Against the measured 507 over-cap comment runs
in src/frob alone, that is 507 hand-typed invocations, each needing the agent to
first find the block's start line. That cost is why the eight cluster leaves are
sized at 15-25 files instead of 40+.

WHAT THIS LEAF ADDS:
- accept a FILE or a DIRECTORY (recursive) instead of `file line`, keeping the
  existing `file line` form working -- it is the precise escape hatch when the
  bulk heuristic picks the wrong block.
- `--apply` to write; default stays dry-run-shaped (print the plan) so a
  directory sweep is inspectable before it touches the ledger.
- for each block: create or APPEND to the cited ticket's body, then replace the
  block with a one-line `# see T-####` pointer (or nothing, when the block is
  wholly narrative and nothing above it needs the pointer).
- `--keep-file` semantics must survive into bulk mode or be explicitly dropped
  with a reason; T-2994 constraint 2 (the load-bearing sentence STAYS) is the
  whole reason that flag exists.

CONSTRAINTS (inherited from T-2994, all binding, all acceptance-bearing):
- MOVE, NEVER DELETE. A bulk sweep that loses narrative is strictly worse than
  the bloat. Every moved block must be readable back out of the ticket.
- ARCHIVED-TICKET WRITE HAZARD (constraint 3). Most cited tickets are archived;
  `frob ticket body` on a done ticket has previously written the ACTIVE path and
  produced a DuplicateId that downed every ledger load repo-wide. Prove the
  archived-write path on ONE ticket, verified, BEFORE any batch, and run
  `frob ticket list` (must exit 0) after every batch. In bulk this hazard is
  multiplied by the batch size -- a single bad append downs the fleet's ledger.
- IDEMPOTENCY (constraint 4). Running the sweep twice must not duplicate content.
- A block citing NO ticket has no destination. Bulk mode must SKIP it and report
  it, never invent a ticket and never delete the block.

POSITIVE CONTROL: a fixture directory of three files -- one block citing a live
ticket, one citing an archived ticket, one citing no ticket. `--apply` moves the
first two into their ticket bodies leaving pointers, skips and reports the third,
`frob ticket list` exits 0, and a second `--apply` is a no-op on all three.
