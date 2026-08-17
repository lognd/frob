---
id: T-2298
title: frob fmt with a broad path rewrote 49 unrelated .strata fixture files; a test-input
  corpus must not be reformattable by an unscoped fmt
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
evidence_scope:
- tests/test_gates_fmt_directives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_broad_path_formats_source_but_leaves_strata_fixtures_untouched
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_include_test_corpora_opts_back_in
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_explicit_single_fixture_path_is_still_formatted
- tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file
designated_repro_test: tests/test_gates_fmt_directives.py::TestFormatPaths::test_broad_path_formats_source_but_leaves_strata_fixtures_untouched
acceptance:
- text: given a tree with .strata fixtures and unformatted source, when frob fmt runs
    with a broad path, then source is formatted and fixture files are left byte-identical
  evidence:
  - tests/test_gates_fmt_directives.py::TestFormatPaths::test_broad_path_formats_source_but_leaves_strata_fixtures_untouched
  - tests/test_gates_fmt_directives.py::TestFormatPaths::test_include_test_corpora_opts_back_in
  - tests/test_gates_fmt_directives.py::TestFormatPaths::test_explicit_single_fixture_path_is_still_formatted
  - tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file
- text: given an agent context, when frob fmt would rewrite files outside the invoking
    ticket's declared scope, then it refuses or excludes them rather than rewriting
    silently
  evidence:
  - tests/test_gates_fmt_directives.py::TestFormatPaths::test_broad_path_formats_source_but_leaves_strata_fixtures_untouched
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
DISCOVERED 2026-08-17 by an implementer agent working T-1783, self-corrected
before it reached main, and therefore never tracked.

`frob fmt .` -- invoked with a broad path argument rather than a scoped one
-- rewrote **49 unrelated `.strata` fixture files**. The agent caught it via
`git status` and reverted with `git checkout --` before committing, so main
was never affected. That is luck plus vigilance, not a guarantee.

WHY THIS MATTERS RATHER THAN BEING A ONE-OFF: fixture files are test INPUTS.
A formatter that rewrites them can silently change what a test asserts
against while every gate still reads green -- the diff looks like
"formatting", so a reviewer skims it. Had the agent committed before running
`git status`, 49 fixture files would have landed reformatted inside an
unrelated docs ticket, and the resulting test-semantics change would have
been attributed to whatever landed next.

This is the standing "systematize friction" case: the agent fixed its own
instance, and the footgun remains armed for the next agent.

FIX DIRECTIONS (choose after measuring; do not guess):
 (a) `frob fmt` should refuse a path argument that expands beyond the
     invoking ticket's declared scope, the same way land-path guards already
     scope edits to the moving ticket -- the scope is already in hand.
 (b) `.strata` fixture directories (and any other test-input corpus) should
     be excluded from `frob fmt` by default, opt-in via an explicit flag.
 (c) At minimum, `frob fmt` should print the file COUNT it is about to
     rewrite and require confirmation past a threshold in agent context
     (`FROB_AGENT` set), where no human is watching the terminal.

(a) is preferred if the scope is reachable from `fmt`'s call site; (b) is
the cheap backstop. (c) alone is weakest -- per the standing "automatic over
commands" directive, a guard that depends on an agent reading a warning is
not a guard.

POSITIVE CONTROL REQUIRED: a test that runs the fmt path against a tree
containing `.strata` fixtures plus genuinely-unformatted source, and asserts
the source IS formatted while the fixtures are NOT touched. A fix verified
only by "the 49 files no longer change" would also pass if fmt stopped
working entirely.