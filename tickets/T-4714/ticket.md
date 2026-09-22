---
id: T-4714
title: 'Strip no-longer-needed noqa from directive lines: Tier-A fix plus lint, without
  re-tripping T-1987''s ARCH001 line-count regression'
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4712
- T-4713
parent: T-4703
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/gates/_fix_engine_text.py
- tests/test_gates_fmt_directives.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'coordinator instruction: register FMT-noqa-strip rule id in _KNOWN_GATE_RULES,
    frob.toml severities, and docs/modules/gates.md'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/modules/gates.md
  reason: 'coordinator instruction: register FMT-noqa-strip rule id in _KNOWN_GATE_RULES,
    frob.toml severities, and docs/modules/gates.md'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: frob.toml
  reason: 'coordinator instruction: register FMT-noqa-strip rule id in _KNOWN_GATE_RULES,
    frob.toml severities, and docs/modules/gates.md'
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/test_gates_fmt_directives.py::TestStripNeedlessNoqaText::test_strips_a_noqa_that_no_longer_fits_the_line
- tests/test_gates_fmt_directives.py::TestStripNeedlessNoqaText::test_load_bearing_noqa_is_left_untouched
- tests/test_gates_fmt_directives.py::TestStripNeedlessNoqaText::test_bare_noqa_with_no_code_is_also_stripped_when_it_now_fits
- tests/test_gates_fmt_directives.py::TestStripNeedlessNoqaText::test_idempotent_second_pass_is_a_no_op
- tests/test_gates_fmt_directives.py::TestStripNeedlessNoqaText::test_never_changes_physical_line_count_reconstructing_t1970_shape
- tests/test_gates_fmt_directives.py::TestNoqaStripViolations::test_flags_a_directive_whose_noqa_no_longer_fits_the_reason
- tests/test_gates_fmt_directives.py::TestNoqaStripViolations::test_load_bearing_noqa_is_not_flagged
- tests/test_gates_fmt_directives.py::TestNoqaStripViolations::test_clean_file_with_no_noqa_at_all_is_not_flagged
- tests/test_gates_fmt_directives.py::TestStripNeedlessNoqaPaths::test_check_mode_reports_without_writing
- tests/test_gates_fmt_directives.py::TestStripNeedlessNoqaPaths::test_second_run_reports_zero_changes
- tests/test_gates_fmt_directives.py::TestFixFmt002NoqaStrip::test_strips_and_is_idempotent
- tests/test_gates_fmt_directives.py::TestFixFmt002NoqaStrip::test_only_paths_scoping_leaves_an_unlisted_file_untouched
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4714
branch: t-4714
---
Leaf 5 of T-4703. 2 points. noqa strip. Blocked by leaves 3 and 4 -- stripping before the wrap
narrows and the stacks merge would re-trip the exact regression T-1987 reverted.

## The regression this leaf must answer, not rediscover

`_rewrite_directive_run` (src/frob/gates/_fmt_directives.py:595-640) treats a run ending in
`# noqa` / `# noqa: CODE` (`_NOQA_SUFFIX_RE`, :81) as an unconditional "leave this run alone"
marker. T-1605 once made it self-retiring; T-1987 REVERTED that because rewrapping one
noqa-suppressed physical line into four changed the PHYSICAL LINE COUNT of the enclosing
function and tripped ARCH001 on two real lands (T-1970, T-1968). Read that docstring in full
before touching the branch.

The answer this story commits to: leaves 1, 2 and 4 SHRINK physical line count (one reverse copy
deleted, one multi-target header replacing a stack). So the strip runs AFTER them, and "no
touched file gains physical lines, and no new ARCH001 anywhere" is an ACCEPTANCE CRITERION of
this leaf, measured, not an assumption.

## What to build

(a) A Tier-A fix that removes `# noqa: E501` and bare `# noqa` from a directive line that now
    fits within that file's resolved line length (`resolve_line_length`,
    src/frob/gates/_fmt_directives.py:389 -- per-file, not a single hardcoded 88).
(b) A lint that flags a directive line carrying a noqa it no longer needs.
(c) The `_NOQA_SUFFIX_RE` escape hatch stays available for the genuine residue: a single token
    longer than the line. It stops being a blanket freeze and becomes what it is measured to be.
(d) docs/modules/gates.md section, replacing the T-1987 "unconditional leave-alone" wording with
    the new contract and the reason it is now safe.

## Positive control

- Plant a directive line whose noqa IS load-bearing (one token longer than the line) and assert
  it is untouched. Plant one whose noqa is not and assert it is stripped. The first is the
  control that the fix is not simply deleting every noqa.
- Reconstruct T-1970's shape (a WALK001 waiver deliberately on one noqa-suppressed physical
  line) and assert the enclosing function's physical line count does NOT grow.
- Assert idempotence: strip, re-canonicalize, strip again -> zero further changes.

## Acceptance

- The 5,663 noqa-carrying directive lines (2026-09-19 18:15 baseline) drop to the genuine
  residue; BOTH numbers pasted in the Done report, with the residue characterized (how many are
  a single over-long node id, how many something else).
- Zero new ARCH001 and zero new E501 across the repo after the strip.
- `ruff check src tests` clean -- the whole point of owner decision 1 is that hand-run ruff is
  not broken.