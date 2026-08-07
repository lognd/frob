---
id: T-0342
title: 'frob.lang python walker never scans module/function docstrings for frob: directives'
state: done
kind: bug
origin: agent
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestDsl::test_function_docstring_directive_binds_to_function
- tests/test_graph.py::TestDsl::test_module_docstring_directive_binds_to_bare_file
designated_repro_test: null
acceptance:
- text: 'given a frob: directive (e.g. frob:tests, frob:ticket) inside a module-level
    or function docstring, when frob.lang parses the file, then the directive is extracted
    and produces an edge (or a MalformedDirective), same as a comment directive'
  evidence: []
threat: null
component: null
---
Found during T-0237: the original T-0159 repro line lived inside a module docstring, and frob.lang's Python walker never scans docstrings for frob: directives at all -- only comments. So a directive written in a docstring is silently ignored (no edge, no malformed report). This is an evasion/coverage gap: a frob:tests/frob:ticket/frob:waive in a docstring is invisible. Fix: have the python walker also scan string-literal docstrings (module, class, function) for frob: directives, binding them to the enclosing symbol like comment directives. Consider the same for other languages' docstring conventions. Disclosed by the T-0237 implementer, not fixed in that ticket's scope (src/frob/lang/** was out of scope).