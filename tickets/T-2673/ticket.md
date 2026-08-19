---
id: T-2673
title: DOCENUM001's ID_TOKEN_RE cannot match hyphenated ids ending in letters (PORT001-IDENT,
  PORT001-PATH)
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docenum.py
evidence_scope:
- tests/test_docenum_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_docenum_gate.py::TestDocenum001HyphenatedLetterSuffixIds::test_hyphenated_letter_suffix_id_with_doc_row_does_not_fire
- tests/test_docenum_gate.py::TestDocenum001HyphenatedLetterSuffixIds::test_hyphenated_letter_suffix_id_with_no_doc_row_still_fires
designated_repro_test: tests/test_docenum_gate.py::TestDocenum001HyphenatedLetterSuffixIds::test_hyphenated_letter_suffix_id_with_doc_row_does_not_fire
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f3ae5993b2b86709f7d2073119b562388e88d2a3
---
Found while working T-2670 (writing DOCENUM001 backlog documentation
rows for gates.md).

_ID_TOKEN_RE in src/frob/gates/_docenum.py is:
  ^[A-Z][A-Z0-9_-]*[0-9]$|^[A-Z][A-Z-]{3,}$

Neither alternative matches an id like PORT001-IDENT or PORT001-PATH:
the first alternative requires the token to END in a digit (fails,
these end in a letter suffix after the hyphen); the second alternative
requires the token to contain ONLY letters and hyphens, no digits
(fails, these contain "001").

Effect: even a correctly-written table row whose first cell is exactly
"PORT001-IDENT" or "PORT001-PATH" can never be recognized as
documentation by _documented_ids/_ids_in_cell, so DOCENUM001 will keep
reporting these two ids as undocumented forever, regardless of what
docs/modules/gates.md actually contains for them.

T-2670 added real, from-implementation table rows for both ids in
docs/modules/gates.md (port_selfcheck rows describing PORT001-PATH/
PORT001-IDENT's actual hardcoded-package-name checks) -- confirmed via
`frob check --ticket T-2670` that a docs-only fix cannot clear this;
the gap is in the detector's own token regex, not the doc content.

Suggested fix: widen _ID_TOKEN_RE to accept a hyphenated suffix after
a digit-containing prefix, e.g. something like
  ^[A-Z][A-Z0-9_]*[0-9](-[A-Z][A-Z0-9]*)?$
or a dedicated third alternative for the "RULEID-SUFFIX" shape, while
verifying it still rejects genuinely non-id prose tokens (the existing
test suite for _ids_in_cell/_documented_ids should cover this).