## Done report

REVIEW ROUND 1 REWORK. Reviewer verdict: REJECT (1 CRITICAL, 1 MAJOR).
Both addressed in this worktree; see fixes below.

CRITICAL (CRLF corruption, reviewer-reproduced) -- FIXED:
`format_paths` used `Path.read_text()`/`write_text()` with default
universal-newline translation. On Linux this silently converts every
`\r\n` to `\n` on read and does not restore it on write (`os.linesep` is
`\n` on Linux), so running `frob fmt` over a CRLF-authored TS/Rust/C/C++
source flattened EVERY line's terminator, not just the directive run
being canonicalized. Fix: both read and write now go through the plain
`open()` builtin with `newline=""` (`pathlib`'s own `newline=` parameter
on `read_text`/`write_text` only exists from Python 3.13; this repo
targets 3.11). `canonicalize_text` splits on `"\n"` only (never
`"\r\n"`), so an untouched line's own trailing `"\r"` was already
preserved verbatim in-string; the fix adds re-attaching a matching `"\r"`
to freshly generated canonical directive lines, matched per-RUN from that
run's own original first physical line (not a single file-global guess).
Added:
- tests/test_gates_fmt_directives.py::TestCrlfPreservation
  (test_canonicalize_text_preserves_crlf_on_untouched_lines,
  test_canonicalize_text_is_a_no_op_on_second_pass,
  test_format_paths_preserves_crlf_end_to_end) -- the last one verified
  by hand against the pre-fix code: reverting to plain
  `read_text()`/`write_text()` makes it fail (asserts `b"\r\n" in raw`
  against output that had been flattened to bare `b"\n"`), and it passes
  against the fixed code.

MAJOR (Hypothesis alphabet gap) -- FIXED:
`test_wrap_then_fold_is_identity`'s alphabet
(`ascii_letters + digits + " _-="`) never generated a backslash -- the
exact character the continuation marker itself is built from. Widened
to `ascii_letters + digits + " _-=\"'\\"` (backslashes, both quote
styles). Ran under the wider alphabet: no counterexample found: the
append-one-backslash/fold-strips-one-backslash design is a net no-op
regardless of how many backslashes the body itself contributes at a cut
boundary, so this was a real gap in coverage, not a real bug. Also added
two explicit hand-constructed regression tests exercising the exact
adversarial shape the reviewer flagged (a body backslash landing exactly
at the wrap cut, and multiple consecutive body backslashes):
test_backslash_at_exact_wrap_boundary_round_trips,
test_double_backslash_in_body_round_trips.

New evidence recorded (5 new ids, 31 total; via `frob ticket evidence
T-0441`):
tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_backslash_at_exact_wrap_boundary_round_trips
tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_double_backslash_in_body_round_trips
tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_canonicalize_text_preserves_crlf_on_untouched_lines
tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_canonicalize_text_is_a_no_op_on_second_pass
tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_format_paths_preserves_crlf_end_to_end

Full suite re-run: tests/test_gates_fmt_directives.py (32 tests) +
tests/unit/graph/test_dsl.py + tests/test_graph.py all pass, 144 total.
`uv run ruff check`/`ruff format --check` clean on every touched file.
`uv run frob check --ticket T-0441` re-run via the chunked `--only` loop
(lint, static, gates-fast, gates-native, gates-security) -- zero errors
tied to this ticket after a fresh `frob ticket sweep T-0441` (PRE001 had
gone stale from the round-1 commits).

docs/modules/gates.md updated with a new "CRLF preservation (T-0441
review round 1 fix)" subsection documenting the `newline=""` mechanism
and why `pathlib`'s own `newline=` parameter could not be used directly
(3.13+ only, this repo targets 3.11).

T-0204 side investigation (coordinator request, not a T-0441 scope
change, no fix applied): `uv run frob ticket show T-0204` is clean here
(exit 0). The reviewer's Pydantic schema-validation error DOES reproduce,
but only under the STALE GLOBAL `frob` binary on PATH (`frob` resolves to
`/home/logan/.local/bin/frob`, version 0.9.0) -- running the bare `frob`
command (not `uv run frob`) against this worktree's current
`tickets.md` gives:
  ERROR: tickets: T-0204 failed schema validation: 2 validation errors for Ticket
  priority
    Extra inputs are not permitted [type=extra_forbidden, input_value='medium', ...]
  component
    Extra inputs are not permitted [type=extra_forbidden, input_value=None, ...]
`uv run frob --version` here is 0.127.0; the global `Ticket` pydantic
model is 118 versions stale and forbids `priority`/`component` fields the
current schema writes for every ticket, including T-0204's -- this is the
documented "Stale global frob" hazard (agent-playbook.md section 1.3: use
`uv run frob`, never the bare global binary, inside a worktree), not a
corruption in T-0204's own ledger block, and not caused by my ledger
writes (T-0441's evidence/scope/done-report CLI calls never touch
T-0204's block; `git diff tickets.md` below confirms). No fix applied to
T-0204 -- this is an environment/PATH issue on whoever's shell ran the
bare `frob`, not a repo bug.

Gates: `frob check --ticket T-0441` clean across lint/static/gates-fast/
gates-native/gates-security (chunked `--only` loop). `git diff main
--diff-filter=D --stat` empty.

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-aceb0dbbbc97766b3

### Changed
```
 README.md                          |   3 +-
 docs/modules/gates.md              |  77 +++++++
 src/frob/__main__.py               |  21 ++
 src/frob/app/app.py                |   4 +-
 src/frob/app/config.py             |  10 +
 src/frob/app/fmt_runner.py         |  50 +++++
 src/frob/gates/_fmt_directives.py  | 361 ++++++++++++++++++++++++++++++++
 src/frob/graph/dsl.py              |  43 +++-
 tests/test_gates_fmt_directives.py | 416 +++++++++++++++++++++++++++++++++++++
 tests/unit/graph/test_dsl.py       |  51 ++++-
 tickets.md                         | 233 ++++++++++++++++++++-
 11 files changed, 1262 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestMarkerFor::test_python_uses_hash` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestMarkerFor::test_rust_uses_slash_slash` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestMarkerFor::test_unsupported_suffix_is_none` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestReadLineLength::test_reads_configured_limit` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestReadLineLength::test_missing_file_defaults_to_88` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestReadLineLength::test_missing_ruff_section_defaults_to_88` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_short_text_stays_one_line` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_long_text_wraps_and_folds_back_identical` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_wrap_then_fold_is_identity` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_indent_is_preserved_on_every_physical_line` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_wraps_over_long_single_line_directive` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_joins_over_split_directive_that_now_fits` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_three_line_continuation_that_fits_collapses_to_one` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_re_wraps_to_minimal_split_when_only_first_line_over_long` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_idempotent_on_already_canonical_text` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_non_directive_comments_are_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_unsupported_language_returns_text_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalizeText::test_rust_double_slash_marker_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_check_mode_reports_without_writing` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_already_canonical_file_reports_no_changes` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller::test_every_physical_line_is_strictly_within_limit` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller::test_no_breakable_space_still_stays_within_limit` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestFoldCommentRuns::test_run_length_matches_consumed_physical_lines` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestFoldCommentRuns::test_single_line_run_has_count_one` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestFoldCommentRuns::test_matches_fold_continuations_text_and_lineno` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_backslash_at_exact_wrap_boundary_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip::test_double_backslash_in_body_round_trips` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_canonicalize_text_preserves_crlf_on_untouched_lines` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_canonicalize_text_is_a_no_op_on_second_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_format_paths_preserves_crlf_end_to_end` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 31 passed (from 31 evidence id(s))
- gates: 0 error(s), 1240 warning(s), 210 waived
- error-findings: none (measured, zero errors)
