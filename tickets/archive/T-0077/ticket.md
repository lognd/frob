---
id: T-0077
title: 'strata as 6th frob.lang grammar: design constructs become graph symbols'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0052
parent: T-0053
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- src/frob/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_strata.py::TestParseStrata::test_symbols_kinds_and_module_qualnames
- tests/unit/test_lang_strata.py::TestParseStrata::test_multiline_construct_span_covers_its_block
- tests/unit/test_lang_strata.py::TestParseStrata::test_comment_inside_a_block_binds_as_enclosing
- tests/unit/test_lang_strata.py::TestParseStrata::test_walk_strata_err_on_bad_syntax
- tests/unit/test_lang_strata.py::TestStrataTreeSitterEscapeHatchesUnsupported::test_raw_tree_unsupported_for_strata
designated_repro_test: null
threat: null
component: null
---
ParsedFile contract over .strata: components/boundaries/claims get qualnames, sig/body digests, acks, DRIFT, frob:doc edges, COV obligations -- the whole existing machinery for free.