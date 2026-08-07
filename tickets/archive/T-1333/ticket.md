---
id: T-1333
title: coverage.py + CSafeLoader interaction corrupts YAML parse under --cov (test_tickets_brief.py)
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- tests/unit/test_ticket_store.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'Fixing T-1333 requires a real behavioral test of the new

    _coverage_tracer_active/_yaml_loader fallback (tests/unit/test_ticket_store.py,

    which already hosts TestYamlLoader) and a doc edge for the changed public

    symbol (docs/modules/tickets.md''s Storage internals section, per AFFECT001).

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/modules/tickets.md
  reason: 'Fixing T-1333 requires a real behavioral test of the new

    _coverage_tracer_active/_yaml_loader fallback (tests/unit/test_ticket_store.py,

    which already hosts TestYamlLoader) and a doc edge for the changed public

    symbol (docs/modules/tickets.md''s Storage internals section, per AFFECT001).

    '
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_ticket_store.py::TestYamlLoader::test_detects_coverage_tracer_by_module_name
- tests/unit/test_ticket_store.py::TestYamlLoader::test_no_active_tracer_is_not_coverage
- tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_under_active_coverage_tracer
designated_repro_test: null
threat: null
component: null
---
found while working T-1295: running tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing (and TestBriefCli::test_cli_prints_briefing) under coverage instrumentation (pytest-cov or plain coverage.py, --branch) makes _yaml_loader()'s CSafeLoader path fail to parse otherwise-valid frontmatter YAML with 'could not determine a constructor for the tag None'. Reproduces identically under bare coverage.py, not a pytest-cov-specific quirk. Does not reproduce at all without instrumentation -- both tests pass cleanly under plain pytest. Likely explains why TEST005 stamped src/frob/tickets/_brief.py::compose_brief at 0.0% branch coverage despite a real behavioral test existing and passing. Investigate whether CSafeLoader (libyaml C ext) has a known bad interaction with coverage.py's tracer/settrace, or whether falling back to the pure-Python SafeLoader under a detected coverage run avoids it.