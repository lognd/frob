---
id: T-2995
title: 'Docs narrative: 44% of doc lines sit in paragraphs citing a ticket id; keep
  the change info, move the story'
state: done
kind: docs
origin: human
created: '2026-08-26'
priority: high
parent: T-2994
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/narrative/**
- docs/commands/narrative.md
- tests/test_narrative_migrate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/narrative/**
  reason: 'T-2995 body is empty/no scope declared. Scoping to a representative proof

    sample per the coordinator''s scope-realism instruction: extend the T-2993

    narrative machinery to markdown paragraphs (src/frob/narrative/**), prove

    the migration on one representative doc (docs/commands/narrative.md,

    which also has a genuinely stale "Wiring status" paragraph now that T-3014

    landed), and update its own doc page. The bulk (137 files, 30,959 lines)

    is filed as a follow-up ticket with per-file counts, not scoped here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/commands/narrative.md
  reason: 'T-2995 body is empty/no scope declared. Scoping to a representative proof

    sample per the coordinator''s scope-realism instruction: extend the T-2993

    narrative machinery to markdown paragraphs (src/frob/narrative/**), prove

    the migration on one representative doc (docs/commands/narrative.md,

    which also has a genuinely stale "Wiring status" paragraph now that T-3014

    landed), and update its own doc page. The bulk (137 files, 30,959 lines)

    is filed as a follow-up ticket with per-file counts, not scoped here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_narrative_migrate.py
  reason: 'T-2995 body is empty/no scope declared. Scoping to a representative proof

    sample per the coordinator''s scope-realism instruction: extend the T-2993

    narrative machinery to markdown paragraphs (src/frob/narrative/**), prove

    the migration on one representative doc (docs/commands/narrative.md,

    which also has a genuinely stale "Wiring status" paragraph now that T-3014

    landed), and update its own doc page. The bulk (137 files, 30,959 lines)

    is filed as a follow-up ticket with per-file counts, not scoped here.

    '
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2994
  reason: 'T-2994 owns the one doctrine: code and docs carry utility, tickets carry
    narrative'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_narrative_migrate.py::TestParagraphAt::test_finds_blank_line_delimited_paragraph
- tests/test_narrative_migrate.py::TestParagraphAt::test_blank_line_returns_none
- tests/test_narrative_migrate.py::TestMigrateBlockSplit::test_markdown_paragraph_reference_line_is_plain_prose
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
