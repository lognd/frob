---
id: T-3633
title: 'windows diag round 11: pwsh trailing-comma ParserError in $codeLines'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Run 33472403980: the round-10 instrumented step FAILED TO PARSE -- the
job log shows, at ~0.5s:

  ParserError: D:\a\_temp\....ps1:72
   72 |    "    raise",
      |                ~
      | Missing expression after ','.

The $codeLines array literal in the T-3624 step has a syntax error
around the element "    raise", (likely an inline # comment placed
between array elements, or a stray/trailing comma -- pwsh array
literals cannot hold a bare comment line between elements the way the
earlier rounds' arrays were formatted). NONE of round 10's
instrumentation ever executed.

Root cause found: `$codeLines = @( ... "    raise", )` -- the LAST
element of the array literal is followed by a trailing comma directly
before the closing `)`. PowerShell's `@()` array-literal grammar treats
`,` as an operator expecting a following expression; a comma with
nothing after it but the closing paren is a parse error ("Missing
expression after ','"), not a tolerated trailing comma the way Python
or JS would treat it.

## Plan

Fix: repair the array literal so the step parses -- validate locally
with: pwsh not available on this WSL host, so instead add/extend the
assertion in tests/test_ci_workflow_matrix.py that EXTRACTS the step's
run: block and checks the $codeLines array is syntactically balanced
(at minimum: every element line ends with `",` or `"` and no
comma-terminated element is followed by a comment/blank before the
next element or the closing paren). Keep all round-10 instrumentation
content (breadcrumbs, cmd /c child, BaseException traceback wrapper)
exactly as intended, just syntactically valid.

Scope: .github/workflows/ci.yml + tests/test_ci_workflow_matrix.py.
