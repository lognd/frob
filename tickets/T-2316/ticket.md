---
id: T-2316
title: 'DOC012: document remaining subcommands with no dedicated doc file (cli.md)'
state: queued
kind: docs
origin: human
created: '2026-08-17'
priority: medium
parent: T-2299
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given the 14 listed subcommands, when frob check --only docblocks runs, then
    none of ack/agent/debt/deprecated/design/docs/explore/ops/pool/profile/quality/registry/test/worktree
    appear in the DOC012 finding list
  evidence: []
- text: given docs/modules/cli.md, when read, then each of the 14 subcommands has
    a real `## frob <name>` (or deeper) heading with actual descriptive prose, not
    an empty placeholder
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Part of the T-2299 DOC012 burn-down (parent tracker).

Re-measured (2026-08-17, `uv run frob check --only docblocks`): DOC012
still reports 24 undocumented subcommands, matching T-1783's original
count exactly (no drift since).

This ticket covers the subset of that 24 with NO existing dedicated
`docs/modules/` or `docs/commands/` file at all -- their only current
mention is a table row / passing reference inside `docs/modules/cli.md`
(the CLI command-tiers overview, which already uses the `## frob <name>
(T-####)` heading style DOC012's parser recognizes for several other
commands, e.g. `## frob coverage (T-1525)`).

Subcommands with no dedicated file (all currently only referenced from
docs/modules/cli.md and/or docs/modules/app.md):
 - frob ack
 - frob agent
 - frob debt
 - frob deprecated
 - frob design
 - frob docs
 - frob explore
 - frob ops
 - frob pool
 - frob profile
 - frob quality
 - frob registry
 - frob test
 - frob worktree

REQUIRED: for each of the 14 subcommands above, add a `## frob <name>`
(or deeper) heading to docs/modules/cli.md with real prose describing
what the subcommand does, its main flags, and any gotchas -- matching
the existing style of that file's other command sections. A bare empty
heading does not satisfy DOC012's intent (see the gate's own docstring
in src/frob/gates/_docblocks.py::doc012_gate) even though the mechanical
check only looks for the heading text.

If any of these 14 turn out to warrant their OWN dedicated file instead
of a cli.md section (e.g. `frob worktree` already has real behavior
documented piecemeal across tickets-landing.md/tickets-lifecycle.md/
tickets-verify-sweep.md and a section in cli.md might be thin) -- use
judgment, but keep this ticket's scope to docs/modules/cli.md plus, if
needed, one new file per such promoted command; do not touch the
sibling group's already-existing per-command files (T-2299's other
child, "docs/modules per-command files").

Re-run `uv run frob check --only docblocks` and confirm these 14
commands drop out of the DOC012 finding list.
