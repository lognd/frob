---
id: T-1223
title: 'rust(interim): tree-sitter Query captures for comment/docstring spans shared
  by sys+opaque+vet'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1219
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_core.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: T-1420 split moved the actual _comment_byte_spans_from_tree/_docstring_byte_spans_from_tree
    functions this ticket edits into _capability_core.py after the ticket's scope
    was written against the old single-file location -- same scope-drift precedent
    as T-1210's own Done report; tests/test_vet.py added for new-evidence node ids
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_vet.py
  reason: T-1420 split moved the actual _comment_byte_spans_from_tree/_docstring_byte_spans_from_tree
    functions this ticket edits into _capability_core.py after the ticket's scope
    was written against the old single-file location -- same scope-drift precedent
    as T-1210's own Done report; tests/test_vet.py added for new-evidence node ids
  actor: logan
  at: '2026-08-03'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_core.py'
  actor: logan
  at: '2026-09-19'
  old_length: 749
  new_length: 1901
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_core.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1900
  new_length: 4052
evidence:
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_docstring_query_does_not_treat_enum_value_as_docstring
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans
- tests/vet_suite/test_opaque_indirection.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
designated_repro_test: null
acceptance:
- text: GIVEN _comment_byte_spans (vet/_capability.py:212) and _docstring_byte_spans
    (:286) are per-node Python recursions independently re-run by sys and opaque (12
    pct of sys + 92 pct of opaque combined) WHEN they are replaced with tree-sitter
    Query captures ('(comment) @c' and the docstring-node equivalent), which run in
    C via the existing py-tree-sitter binding rather than a Python recursion, THEN
    sys+opaque's span-extraction share drops without requiring a new frob_core crate
    export
  evidence:
  - tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_docstring_query_does_not_treat_enum_value_as_docstring
  - tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_docstring_query_still_finds_real_docstrings
  - tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans
  - tests/vet_suite/test_opaque_indirection.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire
  - tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
  - tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Root cause and target: this is the interim zero-Rust step noted under Rust-migration candidate #1 ('use tree-sitter Query captures (C speed) for comment/docstring/identifier extraction from Python'), and it is the mechanism half of PERF-epic child T-1210 (report candidate #5). Split of ownership: this ticket owns the span-EXTRACTION mechanism (Query captures replacing Python recursion) since it is the natural home for a tree-sitter-API-level change; T-1210 owns the sort+bisect containment fix and the per-run cache for the resulting spans, and its acceptance criteria explicitly defer the mechanism to this ticket to avoid two owners writing to the same function. Do not duplicate the containment/caching acceptance criteria here -- see T-1210.

T-4718 sweep (condensed from src/frob/vet/_capability_core.py, the
`_comment_query_cache` block, trimmed for DOCARCH002's 12-line cap): the
trimmed block's full original text, kept verbatim below.

#: Process-lifetime memo of compiled `(comment-type) @c` alternation Queries,
#: keyed by `language_label` (T-1223: the interim zero-Rust half of the
#: report's Rust-migration candidate #1 -- replace the Python-recursion span
#: walk with a tree-sitter Query captured in C). A `Query` is bound to the
#: `tree_sitter.Language` instance it was compiled against, but two
#: `Language` instances for the SAME grammar/ABI are interchangeable for
#: `QueryCursor.captures` purposes (verified: compiling against one file's
#: `tree.language` and running the cursor over an unrelated file's tree of
#: the same grammar returns identical results) -- so the first tree seen for
#: a given `language_label` compiles the Query once, and every later file of
#: that language reuses it. Not keyed by `id(tree.language)`: `frob.lang`
#: does not itself cache `Language` objects across `_parse` calls, so a
#: per-instance cache would never hit past the first file.

T-4718 sweep (condensed from src/frob/vet/_capability_core.py, the
python docstring Query source block, trimmed for DOCARCH002's 12-line
cap): the trimmed block's full original text, kept verbatim below.

#: The python docstring Query source (T-1223): every module/class/function
#: body whose FIRST named child (after skipping any leading `comment`
#: nodes, T-2885) is a bare `string` node, or an `expression_statement`
#: wrapping one -- mirrors the exact shape `_py_leading_docstring_node`
#: (pre-T-1223) tested node-by-node in Python.
#: NOTE: `expression_statement` is a tree-sitter-python SUPERTYPE, not a
#: concrete node kind -- it also matches concrete nodes like `assignment`
#: (verified: `(expression_statement (string) @doc)` alone spuriously
#: captured an enum member's VALUE string, e.g. `NotADirectory = "..."`,
#: because `assignment` conforms to the `expression_statement` supertype
#: and its own `string` child satisfies the inner pattern). `_PY_DOC_CAPTURE
#: _FILTER` below is the required post-filter closing that gap: a capture
#: only counts as a real docstring if its immediate parent's own `.type` is
#: literally `"module"`, `"block"` (the bare-string case), or
#: `"expression_statement"` (the wrapped case) -- never `"assignment"` or
#: any other expression_statement-conforming concrete kind.
#: T-2885: the `.` anchor requires the docstring to be tree-sitter's
#: IMMEDIATE first named child -- this project's tree-sitter-python
#: grammar does NOT mark `comment` as an `extra` node the query engine
#: treats as anchor-transparent (confirmed empirically), so a file that
#: opens with a `#`-comment (e.g. any `frob:waive`/`frob:ticket` header
#: block, common repo-wide) silently defeated the anchor and the "real"
#: docstring was reported as unstarted, exposing every needle-shaped
#: substring in its prose to the needle-scan gates it should have been
#: excluded from (OPAQUE001, the `sys` capability scanner). Each pattern
#: now explicitly tolerates zero-or-more leading `(comment)*` nodes
#: before the anchored string/expression_statement, so a header comment
#: no longer breaks docstring-span detection.