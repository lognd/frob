## Done report

Changed:
- src/frob/gates/_fmt_directives.py::_canonical_lines
- src/frob/gates/_fmt_directives.py::_shift_cut_off_boundary_space (new)
- tests/test_gates_fmt_directives.py::TestConventionUnitBinding (new)

Root cause: in `_canonical_lines`'s fallback branch (no breakable space
found by `rfind(" ", 0, budget)`), the split point was always `cut =
budget` verbatim. `rfind`'s search range `[0, budget)` cannot see a space
sitting exactly AT index `budget` -- one column past its exclusive upper
bound. When that boundary space existed (e.g. a `frob:tests` directive's
target immediately followed by ` kind="unit"`, wrapped at the exact width
where the space between them lands at that index), the naive split
stranded the space as the FIRST character of the continuation line's
content. The real directive parser's comment extraction
(`frob.lang._common._strip_comment_delims`) fully `.strip()`s each
physical comment line (unlike this test file's own lenient
one-leading-space `_fold_lines` helper, which is why the T-0984-era
property test never caught this) -- so that leading space was silently
dropped on parse, gluing target+attribute into one corrupted token with
no separator. A live DRIFT002 with no fix visible at HEAD.

Fix shape: extracted `_shift_cut_off_boundary_space` (also keeps
`_canonical_lines` under ARCH001's 60-line threshold) which walks the
fallback `cut` back off `budget` while `remaining[cut]` is a space, so
neither `head` nor `tail` ever carries a boundary space at its edge --
the space lands safely mid-line on the next physical line instead, where
`.strip()` cannot touch it.

Property-test result: `test_logical_text_is_identical_across_widths_and_attribute_counts`
(Hypothesis, target length 5..90 / 0..2 trailing attributes / wrap width
40..120 / both `#` and `//` markers) plus a hand-verified brute-force
sweep during investigation (widths 40..120, target lengths 5..90 step 3,
0/1/2 attrs, both markers) found zero mismatches after the fix, against
the REAL parser's full-strip extraction semantics
(`_fold_lines_real_extractor`). The exact failing shape
(`test_target_plus_kind_attribute_splitting_after_target_round_trips`,
limit=71) now round-trips correctly.

Evidence: tests/test_gates_fmt_directives.py::TestConventionUnitBinding
(both tests), full `tests/test_gates_fmt_directives.py` suite (38 passed),
`uv run frob check --ticket T-0991` clean (0 errors across all gates,
including ARCH/PII/DOC/DRIFT after the helper extraction and test rename
fixed the two new findings my own diff introduced).

Filed: none.

Gates: `frob check --ticket T-0991` clean (0 errors, 4861 warnings, 318
waived -- pre-existing repo-wide baseline, none newly introduced by this
diff). `frob test --base main` surfaced pre-existing, out-of-scope
failures (ticket-land/registry-reconciliation/compliance-view suites) --
none touch `src/frob/gates/_fmt_directives.py` or
`tests/test_gates_fmt_directives.py`; `git status` confirms only this
ticket's two scoped files (plus `tickets.md`) are modified in this
worktree.
