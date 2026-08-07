---
id: T-0905
title: Partial tree-sitter parse (salvaged, has_error) silently drops symbols -- partial_parse_files()
  has zero gate consumers
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/__init__.py
- src/frob/gates/_parse_failures.py
- docs/modules/gates.md
- docs/modules/lang.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 requires touching the affects()-closure docs for parse_failure_gate/partial_parse_files;
    PARSE001 row was also missing entirely from the rule-catalog table (pre-existing
    gap), added alongside PARSE002
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/modules/lang.md
  reason: AFFECT001 requires touching the affects()-closure docs for parse_failure_gate/partial_parse_files;
    PARSE001 row was also missing entirely from the rule-catalog table (pre-existing
    gap), added alongside PARSE002
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_gates.py::TestParseFailureGate::test_parse_failure_is_an_error_violation
- tests/test_gates.py::TestParseFailureGate::test_no_parse_failures_is_clean
- tests/test_lang.py::TestErrors::test_syntax_error_logs_partial_tree_warning
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep).

frob.lang's tree-sitter ingestion (src/frob/lang/__init__.py's `_parse`/
`_warn_if_partial_tree`, ~line 280-315) already distinguishes a HARD parse
failure (unusable tree: `root_node is None` or `has_error and
child_count == 0`) from a PARTIAL/salvaged parse (`has_error` but the
grammar still produced usable top-level structure). The hard-failure case
is a real, loud gate violation (PARSE001, `frob.gates._parse_failures`,
T-0558/T-0561). The partial case is NOT: `_warn_if_partial_tree` only logs a
WARNING and records the path into the module-level `_partial_parse_files`
set, exposed via the public `partial_parse_files()` accessor -- but nothing
in `frob.gates` (or the `frob check` CLI dispatch) ever calls
`partial_parse_files()`. Verified via repo-wide grep: the only references to
`partial_parse_files`/`_partial_parse_files` are the definition site itself,
its own docstring, and the `__all__` export -- zero gate, zero CLI, zero
test consumes it.

This is the PARSE001 vacuousness bug (T-0404 finding 2, T-0558's own
module docstring) reopened for the partial-tree half: "a syntax error
present, some top-level symbols may be silently dropped from the salvaged
tree" -- exactly the class PARSE001 exists to make loud for a full parse
failure -- but for a partial parse, every downstream gate (COV001, DRIFT,
INV, TEST001-*, ...) sees only the symbols tree-sitter's error-recovery
happened to salvage, with the missing remainder invisible and unflagged.
A source file with a syntax error near its top (a stray unmatched brace, an
unterminated string before the real content) can silently drop obligations
for everything after it, with only a DEBUG/WARNING-level log line as
evidence -- which the T-0558 module docstring itself calls "only visible
above the default log level" and explicitly names as the still-open gap
(finding 1 in that docstring: "no gates stage at all ... to notice a
WARNING here").

Fix direction: add a PARSE002 (or extend PARSE001) ERROR-tier gate over
`frob.lang.partial_parse_files()`, symmetric with PARSE001's hard-failure
handling -- loud by default, waivable with an honest reason for a known
intentionally-malformed fixture.