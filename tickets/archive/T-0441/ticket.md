---
id: T-0441
title: 'frob fmt: auto-wrap over-length frob: directive comment lines via T-0286 continuation
  so ruff E501 never fires on waive reasons'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/
- src/frob/app/
- docs/
- tests/test_gates_fmt_directives.py
- tests/unit/graph/test_dsl.py
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_fmt_directives.py
  reason: 'T-0441 evidence: round-trip/property/mutant-killer tests for frob fmt live
    here, per playbook section 5 evidence discipline'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'T-0441 evidence: round-trip/property/mutant-killer tests for frob fmt live
    here, per playbook section 5 evidence discipline'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: README.md
  reason: DOC005 requires the frob fmt command-table row + count bump in README.md
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates_fmt_directives.py::TestMarkerFor::test_python_uses_hash
- tests/test_gates_fmt_directives.py::TestMarkerFor::test_rust_uses_slash_slash
- tests/test_gates_fmt_directives.py::TestMarkerFor::test_unsupported_suffix_is_none
- tests/test_gates_fmt_directives.py::TestReadLineLength::test_reads_configured_limit
- tests/test_gates_fmt_directives.py::TestReadLineLength::test_missing_file_defaults_to_88
- tests/test_gates_fmt_directives.py::TestReadLineLength::test_missing_ruff_section_defaults_to_88
- tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_short_text_stays_one_line
- tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_long_text_wraps_and_folds_back_identical
- tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_wrap_then_fold_is_identity
- tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_indent_is_preserved_on_every_physical_line
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_wraps_over_long_single_line_directive
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_joins_over_split_directive_that_now_fits
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_three_line_continuation_that_fits_collapses_to_one
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_re_wraps_to_minimal_split_when_only_first_line_over_long
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_idempotent_on_already_canonical_text
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_non_directive_comments_are_untouched
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_unsupported_language_returns_text_unchanged
- tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_rust_double_slash_marker_round_trips
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_check_mode_reports_without_writing
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_already_canonical_file_reports_no_changes
- tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller::test_every_physical_line_is_strictly_within_limit
- tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller::test_no_breakable_space_still_stays_within_limit
- tests/unit/graph/test_dsl.py::TestFoldCommentRuns::test_run_length_matches_consumed_physical_lines
- tests/unit/graph/test_dsl.py::TestFoldCommentRuns::test_single_line_run_has_count_one
- tests/unit/graph/test_dsl.py::TestFoldCommentRuns::test_matches_fold_continuations_text_and_lineno
- tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_backslash_at_exact_wrap_boundary_round_trips
- tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_double_backslash_in_body_round_trips
- tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_canonicalize_text_preserves_crlf_on_untouched_lines
- tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_canonicalize_text_is_a_no_op_on_second_pass
- tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_format_paths_preserves_crlf_end_to_end
designated_repro_test: null
threat: null
component: null
---
Friction hit by hand 2026-07-20: a `frob:waive` reason long enough to be
useful overflows ruff's E501, so `frob check` (ruff) and the waive author
fight -- you truncate the reason (losing the explanation) or hand-wrap it
with the T-0286 trailing-backslash continuation. frob owns the continuation
syntax, so frob should own the wrapping.

Design:
- `frob fmt` (or `frob check --fix-directives`) detects any `frob:<verb>`
  directive comment line exceeding the project's configured line length
  (read the real limit from ruff/pyproject, per-language for TS/Rust/C++
  too, not a hardcoded 88) and rewrites it into a T-0286 continuation run:
  break at a word boundary before the limit, end each physical line with
  ` \`, keep every physical line under the limit, and preserve the exact
  logical directive text (round-trip: fold(wrap(x)) == x).
- Idempotent: re-running on already-wrapped directives is a no-op.
- When run inside `frob check` without the fix flag, emit a remediation
  hint on the offending line: "directive line over NN cols; run `frob fmt`
  to wrap" -- same self-remedying-message contract as every other gate.
- Cover comment prefixes for all supported languages (`#`, `//`), and the
  continuation-line prefix each language needs so the fold still parses.
- Tests: property test that wrap then fold is identity on arbitrary
  directive text; fixtures per language; an idempotency test.

REFINEMENT (user): frob fmt must be a CANONICAL-FORM NORMALIZER, not a
one-way wrapper -- it needs DEDENTING / UN-WRAPPING capability too. If a
directive was previously split across continuation lines (trailing `\`) but
now fits within the configured limit on a single line -- because the reason
text was shortened, the limit was raised, or it was split unnecessarily in
the first place -- frob fmt must JOIN it back into one physical line (strip
the `\` continuations and the continuation-line comment prefixes, fold the
text, re-emit as a single line) rather than leaving a needlessly-split
directive. Canonical form = the FEWEST physical lines that keep every line
under the limit: one line when it fits, wrapped only as far as necessary.
So the operation is idempotent in BOTH directions: fmt(wrapped-but-fits) ->
single line; fmt(single-line-too-long) -> minimally wrapped; fmt(already-
canonical) -> no-op. Add tests for the un-wrap direction: a 3-line
continuation whose joined form fits collapses to 1 line; a 2-line split
where only the first line was over-long re-wraps to the minimal split;
round-trip join(split(x)) == canonical(x). This shares the fold logic with
T-0286's `_fold_continuations` (reuse, do not duplicate) -- fmt's job is to
choose the canonical physical-line layout, folding to normalize then
re-splitting only where a physical line would exceed the limit.