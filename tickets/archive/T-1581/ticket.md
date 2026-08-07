---
id: T-1581
title: COV002 Tier-A insertion handler must use the target file's comment leader
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- docs/modules/gates.md
- tests/test_gates_fix_engine.py
- src/frob/gates/_fmt_directives.py
- docs/modules/gates_e501_autofix.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: the real fix_cov002 regression tests live here, not tests/test_gates.py
    as the ticket originally listed
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/gates/_fmt_directives.py
  reason: reuse marker_for's existing per-suffix comment-leader table instead of a
    second hardcoded dict, and extend it with .strata
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/gates_e501_autofix.md
  reason: the real fix_cov002_ticket_directive_insertion writeup lives here (gates.md
    was under an in-progress lease at T-1548 land time)
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_strata_file_gets_slash_slash_leader
- tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_rust_file_gets_slash_slash_leader
- tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_python_file_gets_hash_leader
- tests/test_gates_fix_engine.py::TestInsertTicketDirectiveAboveCommentLeader::test_unknown_extension_refuses_insertion
designated_repro_test: null
threat: null
component: null
---
T-1548's fix_cov002_ticket_directive_insertion writes '# frob:ticket <id>' unconditionally. During T-1548's OWN land sweep it inserted that Python-style line into design/frob.strata (comment leader '//'), which broke strata parsing on main -- frob sys sync-interface died with ParseFailed until hand-repaired (commit on 2026-08-05). Fix: resolve the comment leader per target language (the dsl/lang layer already knows per-language comment syntax for directive PARSING -- reuse that, do not hardcode a second table), and refuse to insert into file types whose leader is unknown. Regression test: handler run against a .strata file and a .rs file inserts '//', against .py inserts '#', against an unknown extension inserts nothing.