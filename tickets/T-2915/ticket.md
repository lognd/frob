---
id: T-2915
title: Re-run branch stranded-work classification with the real directive parser,
  not bare regex
state: done
kind: feature
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/branch_stranded_work_analysis.py
- tests/unit/test_branch_stranded_work_analysis.py
- docs/audits/branch-stranded-work-2026-08-25.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_branch_stranded_work_analysis.py
  reason: the fix's own tests and the audit doc it updates
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/audits/branch-stranded-work-2026-08-25.md
  reason: the fix's own tests and the audit doc it updates
  actor: logan
  at: '2026-08-25'
evidence:
- tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch::test_string_literal_mention_is_not_a_directive
- tests/unit/test_branch_stranded_work_analysis.py::TestTicketIdsOnBranch::test_real_directive_comment_found_via_real_parser
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5a10e85ff6c5fa50e39bc8a6d7ca91084f082f70
---
T-2646's stranded-work analysis (docs/audits/branch-stranded-work-2026-08-25.md)
used a bare regex over blob text for the "frob:ticket T-####" directive
signal, deliberately, to stay a standalone script outside frob.lang (which
was under T-1604's scope lease at the time). That regex cannot distinguish
a real directive-position comment from the same text sitting inside a
string literal -- measured impact: tests/test_gates.py alone carries 389
literal "frob:ticket" occurrences in its own fixtures, which inflated the
ticket_ids list (and therefore the merged/ticket-done/stranded verdict)
for every branch that happens to touch that file.

Re-run scripts/branch_stranded_work_analysis.py's classification using the
real parser path (frob.lang.parse_file + frob.graph.dsl.parse_directives,
the same machinery frob.tickets._unlanded._directive_ids_via_real_parser
uses, T-2300) instead of the bare _TICKET_DIRECTIVE_RE grep, to sharpen the
"stranded" class down to its real membership before any deletion decision
is made against it.

Scope: scripts/branch_stranded_work_analysis.py, plus frob.lang if a new
text-in entrypoint is still needed (re-check T-1604's lease status first).