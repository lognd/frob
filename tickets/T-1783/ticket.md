---
id: T-1783
title: 'New rule: every top-level CLI verb needs a dedicated doc section, not just
  a table row'
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_waive.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow package glob to the specific files DOC012 (new gate) touches
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: narrow package glob to the specific files DOC012 (new gate) touches
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/_waive.py
  reason: narrow package glob to the specific files DOC012 (new gate) touches
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/__init__.py
  reason: narrow package glob to the specific files DOC012 (new gate) touches
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/gates.md
  reason: narrow package glob to the specific files DOC012 (new gate) touches
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_gates.py
  reason: narrow package glob to the specific files DOC012 (new gate) touches
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_gates.py::TestDoc012CommandSectionGate::test_undocumented_subcommand_fails
- tests/test_gates.py::TestDoc012CommandSectionGate::test_documented_subcommand_passes
- tests/test_gates.py::TestDoc012CommandSectionGate::test_table_row_alone_does_not_satisfy
- tests/test_gates.py::TestDoc012CommandSectionGate::test_no_config_means_no_checking
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 153f84bbaddd32ed6f521deecad6f3d154e8746c
---
T-1611 classification: T-1610's docs-completeness sweep found `frob
coverage` (T-1516/T-1525) has no dedicated doc section -- it is named in
docs/modules/cli.md's verb table but its own flags/behavior are
documented only in a passing aside inside docs/modules/testing.md about
a different topic (docs/audits/docs-completeness-2026-08-06.md, gap 3).
Every other top-level verb of comparable weight (`frob clean`, `frob
vet`, `frob release`) has its own dedicated `## ` section.

Classified as NO RULE EXISTS for this obligation. Checked DOC004
(src/frob/gates/_docblocks.py, the `[[docblocks.commands]]`-configured
console/table drift check) specifically, since it is the closest
existing mechanism: DOC004 verifies a verb TABLE's rows are neither
missing a real subcommand nor stale-naming a removed one, and verifies
fenced console examples against the live argparse tree. `frob coverage`
already has a table row (docs/modules/cli.md), so DOC004 correctly finds
nothing wrong -- it was never designed to ask whether a verb with a
table row also has a dedicated section elsewhere describing its own
flags in depth. That is a different, deeper obligation DOC004's own
scope does not cover, not a misfire.

Add a rule (next free id, same `[[docblocks.commands]]`-style config
family as DOC004) that: for every top-level subcommand the live argparse
tree exposes, requires at least one `## `-level (or deeper) markdown
heading under `docs/commands/` or `docs/modules/` whose heading text (or
a documented alias table) names that subcommand -- a table-row mention
alone does not satisfy it. This ticket is the RULE; T-1682 (already
filed by T-1610) is the CONTENT fix for `frob coverage` specifically --
they do not block each other.