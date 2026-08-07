## Done report

Changed:
- src/frob/gates/_fmt_directives.py::_canonical_lines
- tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984 (new)
- docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441 (AFFECT001 touch note)

Root cause: `_canonical_lines`'s word-boundary cut search used
`remaining.rfind(" ", 0, budget + 1)`, whose end bound is exclusive, so a
space AT index `budget` itself was allowed to match. Keeping that space
attached to the earlier line (`remaining[: cut + 1]`) then produced a
`head` of length `budget + 1` -- one column over budget, hence one column
over `limit` once `prefix` and the trailing `\` continuation marker were
added. This is exactly the "wraps to 89 chars against an 88-char limit"
bug T-0972 hit running `uv run frob fmt src/frob` repo-wide. Fix: exclude
index `budget` from the search span (`rfind(" ", 0, budget)`), so the
latest possible cut still leaves `head` at length `budget`, never
`budget + 1`.

Reproduced on synthetic fixtures at the exact boundary (space landing at
index `budget`; directive lines at exactly the limit, one under, and one
over) before fixing -- confirmed the pre-fix code emits an 89-column line
at limit=88 and the post-fix code stays at 88. Manually re-broke the fix
(restored the old `budget + 1` span) and reran the new tests to confirm
they fail against the bug and pass against the fix.

Evidence: 4 pytest node ids recorded via `frob ticket evidence T-0984`
(TestBoundaryOffByOneT0984's 4 tests). Full existing
`tests/test_gates_fmt_directives.py` suite (32 tests) still green.
`frob test --base main` touched-set run: `[PASS] python exit=0` (twice,
before closing).

Real-data proof: ran `uv run frob fmt src/frob` in this worktree after
the fix. It still reformatted ~218 files -- confirmed by inspection this
is NOT the T-0984 off-by-one (zero `frob:` directive lines exceed 88
columns in any of the 218 changed files, checked mechanically) but two
separate, pre-existing causes: (1) many multi-line directives were
hand-wrapped/formatted with more physical lines than the current
"fewest lines" canonical form needs, so a repo-wide fmt run legitimately
recompacts them, and (2) some `frob:tests`/`frob:waive` lines carry a
deliberate `# noqa: E501` suffix as an escape hatch for one unbreakable
token (e.g. a long dotted pytest node id) which `canonicalize_text`
currently folds into the directive's own text and force-wraps anyway.
Reverted all 217 out-of-scope files this run touched (`git checkout
--pathspec-from-file`) so only the fix + tests + doc note remain in this
ticket's diff; filed T-0985 for the broader repo-wide
reformat-drift/noqa-handling gap rather than silently expanding this
ticket's scope to ~218 unrelated files.

Filed: T-0985 (frob fmt repo-wide run still reformats ~218
files: recompaction drift + noqa-suffix lines wrongly wrapped) -- separate
from T-0984's off-by-one, scoped for its own review.

Gates: `frob check --ticket T-0984 --only gates-fast` PASS (0 errors),
`--only gates-native` PASS (0 errors), `--only gates-security` PASS
(0 errors), `--only static` PASS (0 errors), `--only lint` PASS
(ruff-check/ruff-format/ty all clean).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_space_exactly_at_budget_boundary_does_not_overflow` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_directive_line_at_exact_limit_is_byte_identical` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_directive_line_one_under_limit_is_byte_identical` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984::test_directive_line_one_over_limit_wraps_and_stays_in_bounds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4889 warning(s), 304 waived
- error-findings: none (measured, zero errors)
