---
id: T-0858
title: 'xref sunset reevaluation: consumer-audit need is real and recurring but agents
  answer it with grep -- fold into exports/graph surface before 2026-10-01 deletion'
state: done
kind: ux
origin: human
created: '2026-07-23'
priority: medium
parent: T-0580
tier: ticket
sprint: null
scope:
- src/frob/app/xref_runner.py
- src/frob/exports/**
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_exports.py::TestExportsConsumers::test_finds_import_consumer
- tests/unit/test_exports.py::TestExportsConsumers::test_excludes_prose_mention
- tests/unit/test_exports.py::TestExportsConsumers::test_no_source_files
- tests/unit/test_exports.py::TestExportsConsumers::test_as_text_output
- tests/unit/test_exports.py::TestExportsConsumers::test_as_json_output
designated_repro_test: null
threat: null
component: null
---
2026-07-23 reevaluation prompted by the user after this session's exports triage (T-0600/T-0601) and TEST014 binding work (T-0588) leaned on who-imports-this-symbol queries. Telemetry verdict: root telemetry has 0 organic xref events today (82 historical, all tests); both surviving agent worktrees show 0 xref events despite dispatch prompts explicitly suggesting frob xref -- agents chose grep/Serena. BUT the underlying question (external consumers of a symbol, distinguishing imports from prose) is now RECURRING gate-driven work, and grep demonstrably errs in both directions (T-0601 reviewer caught a missed comment-prose reference; grep cannot cleanly separate import-consumers from mentions). Decision to make before the 2026-10-01 sunset executes: keep the standalone xref porcelain deprecated (telemetry supports it), and instead fold a consumer-lookup mode into a surface agents actually use (e.g. frob exports --consumers <symbol>, or a graph query verb) so the sunset does not delete the capability along with the porcelain. Re-check telemetry at sunset time; caveat that most worktree telemetry dies with worktree removal, so absence-of-evidence there is weak.