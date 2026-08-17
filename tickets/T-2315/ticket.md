---
id: T-2315
title: 'DOC012: add missing command headings to existing docs/modules per-command
  files'
state: done
kind: docs
origin: human
created: '2026-08-17'
priority: medium
parent: T-2299
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/arch.md
- docs/modules/clean.md
- docs/modules/dup.md
- docs/modules/fleet.md
- docs/modules/graph.md
- docs/modules/mutate.md
- docs/modules/perf.md
- docs/modules/serve.md
- docs/modules/stats.md
- docs/modules/vet.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: given the 10 listed subcommands, when frob check --only docblocks runs, then
    none of arch/clean/dup/fleet/graph/mutate/perf/serve/stats/vet appear in the DOC012
    finding list
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: given each edited docs/modules/*.md file, when read, then it contains a real
    `## frob <name>` (or deeper) heading with actual prose about that subcommand's
    behavior, not an empty placeholder
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: c7fee2f5318df8705761b1d66f1ae6df69bb4be7
---
Part of the T-2299 DOC012 burn-down (parent tracker).

Re-measured (2026-08-17, `uv run frob check --only docblocks`): DOC012
still reports 24 undocumented subcommands, matching T-1783's original
count exactly (no drift since).

This ticket covers the subset of that 24 whose owning `docs/modules/`
file ALREADY exists as a dedicated per-command doc (it documents the
underlying module/gate family in prose) but lacks the specific `## frob
<name>` (or backtick-quoted equivalent) heading DOC012's parser looks
for -- these files currently use a `# frob.<name> -- ...` title style
(a dotted module name, not the `frob <name>` two-token CLI-invocation
shape DOC012 requires), so DOC012 does not recognize them as satisfying
the command even though the file is squarely about that command.

Subcommands and their existing owning file:
 - frob arch     -> docs/modules/arch.md
 - frob clean    -> docs/modules/clean.md
 - frob dup      -> docs/modules/dup.md
 - frob fleet    -> docs/modules/fleet.md
 - frob graph    -> docs/modules/graph.md
 - frob mutate   -> docs/modules/mutate.md
 - frob perf     -> docs/modules/perf.md
 - frob serve    -> docs/modules/serve.md
 - frob stats    -> docs/modules/stats.md
 - frob vet      -> docs/modules/vet.md

REQUIRED: add a `## frob <name>` (or deeper) heading to each file above
naming the subcommand, placed so it reads naturally next to the existing
prose (do not just bolt an empty heading onto the end -- DOC012 wants the
command's own behavior documented, per its own gate docstring). Re-run
`uv run frob check --only docblocks` and confirm these 10 commands drop
out of the DOC012 finding list.

Scope kept disjoint from the sibling docs/modules/cli.md-owned group
(the remaining 14 subcommands with no dedicated file) so both can land
in parallel.