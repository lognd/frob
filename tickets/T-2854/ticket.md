---
id: T-2854
title: 'malformed-directive false-positive: docstring prose containing ''frob:waive
  reason'' parsed as an attribute'
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_coordinator_scripts.py
- tests/unit/graph/test_dsl_mention_escape.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/graph/test_dsl_mention_escape.py
  reason: T-2854's fix needs a regression test in the canonical T-1970 mention-escape
    home (tests/unit/graph/test_dsl_mention_escape.py), not just the one docstring
    reworded in test_coordinator_scripts.py, so the docstring-carrier false positive
    has a durable positive-control pair (escaped/unescaped) rather than only a fixed
    fixture
  actor: logan
  at: '2026-08-22'
- op: add
  glob: tests/unit/graph/test_dsl_mention_escape.py
  reason: T-2854's fix needs a regression test in the canonical T-1970 mention-escape
    home (tests/unit/graph/test_dsl_mention_escape.py), not just the one docstring
    reworded in test_coordinator_scripts.py, so the docstring-carrier false positive
    has a durable positive-control pair (escaped/unescaped) rather than only a fixed
    fixture
  actor: logan
  at: '2026-08-22'
evidence:
- tests/unit/test_coordinator_scripts.py::TestOwnDocstringHasNoMalformedDirective::test_no_malformed_directives_in_this_file
- tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_unescaped_docstring_prose_is_malformed
- tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_escaped_docstring_prose_produces_no_malformed_or_edge
- tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_real_directive_inside_a_docstring_still_parses
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestOwnDocstringHasNoMalformedDirective::test_no_malformed_directives_in_this_file
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 20357be014ae73564d859eddcb79ddc06f1829fc
---
Found during T-2846's land: tests/unit/test_coordinator_scripts.py:5110's docstring prose (T-2845's added test) contains the substring 'frob:waive reason still parses as one directive and still binds,' -- the directive scanner appears to treat this prose as an attempted frob:waive directive and reports 'malformed directive: bad attribute syntax'. This is a WARNING, not currently gate-blocking, but is either (a) a real directive-scanner false positive that should not fire inside a docstring/comment quoting the DSL by name, or (b) confirms directive scanning is comment-scoped correctly and the fix is simply to reword the docstring to avoid the substring. Fix by rewording the docstring in the smaller-scope case; if the scanner is firing outside comments entirely, that is the larger and more concerning finding.