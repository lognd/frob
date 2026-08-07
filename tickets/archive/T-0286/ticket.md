---
id: T-0286
title: 'comment DSL: multi-line reason= via backslash continuation'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
- docs/guides/extending/comment-dsl-directives.md
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/graph/test_dsl.py::TestContinuation::test_long_reason_continues_across_lines
- tests/unit/graph/test_dsl.py::TestContinuation::test_folded_directive_reports_first_physical_lineno
- tests/unit/graph/test_dsl.py::TestContinuation::test_join_uses_empty_string_not_space
- tests/unit/graph/test_dsl.py::TestContinuation::test_three_line_continuation
- tests/unit/graph/test_dsl.py::TestContinuation::test_normal_single_line_directive_unchanged
- tests/unit/graph/test_dsl.py::TestContinuation::test_dangling_backslash_on_last_comment_line_is_literal
- tests/unit/graph/test_dsl.py::TestContinuation::test_crlf_before_trailing_backslash_is_safe
- tests/unit/graph/test_dsl.py::TestContinuation::test_verb_agnostic_multiline_tests_directive
designated_repro_test: null
acceptance:
- text: given a frob:waive whose reason would exceed ruff line-length when written
    on one line, when the directive line ends with a backslash and continues on the
    next comment line, then the parser joins them into one logical directive with
    the full reason and no E501
  evidence: []
- text: given a joined multi-line directive, when it is malformed, then the MalformedDirective
    line number points at the FIRST physical line of the directive (start_line), not
    the continuation
  evidence: []
- text: 'given a normal single-line directive (no trailing backslash), when parsed,
    then behavior is byte-for-byte unchanged (regression: existing dsl tests stay
    green)'
  evidence: []
threat: null
component: null
---
User-reported (2026-07-19): the single-line frob:<verb> ... reason="..." DSL structurally collides with the ruff 88-col limit -- a self-explaining waiver reason routinely overflows, forcing the reason to be truncated to fit (just happened with the PERF004 waiver in _audit.py, shortened twice to squeeze under 88). Fix at the DSL level, not per-comment. Design: support backslash line-continuation. In parse_directives (src/frob/graph/dsl.py:183-195), before dispatching to _parse_line, fold any physical comment line whose stripped content ends in a trailing backslash into the following comment line (strip the backslash, join with a single space or empty -- pick empty so reasons control their own spacing; document the choice). Works uniformly across # , // , and /* */ comment bodies since it operates on comment.text.splitlines(). Keep lineno = start_line + offset of the FIRST line of a folded run. _LINE_RE / _ATTR_RE unchanged (they see the already-joined logical line). Add tests: continuation inside reason=, continuation with trailing backslash on the last line (dangling -> treat literally or malformed, decide + test), CRLF safety, and a multi-line frob:tests to prove it is verb-agnostic not waive-specific. Update comment-dsl-directives.md with the continuation syntax and a worked long-reason example.