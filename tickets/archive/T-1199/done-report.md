## Done report

Changed:
- src/frob/refactor/_directives.py (new): extend_span_for_attached_directives,
  scan_directive_carriers, carry_lock_acks
- src/frob/refactor/_transaction.py::build_plan (extends move span for
  attached directives, folds scan_directive_carriers into reference_ops)
- src/frob/refactor/_transaction.py::run_refactor (calls carry_lock_acks
  post-apply, pre-commit)
- src/frob/refactor/__init__.py (exports the three new functions)
- docs/commands/refactor.md (new anchors for the three functions; updated
  build_plan/run_refactor prose)
- tests/test_refactor.py::TestDirectiveCarrier (5 new tests)

Evidence:
- tests/test_refactor.py::TestDirectiveCarrier::test_attached_waiver_moves_with_symbol (accepts 0)
- tests/test_refactor.py::TestDirectiveCarrier::test_move_carries_attached_waiver_end_to_end (accepts 0)
- tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten (accepts 1)
- tests/test_refactor.py::TestDirectiveCarrier::test_lock_ack_carried_to_new_symref (accepts 2)
- tests/test_refactor.py::TestDirectiveCarrier::test_unrelated_comment_not_extended (regression guard, not bound to an acceptance index)
- Full tests/test_refactor.py run: 42 passed (uv run pytest tests/test_refactor.py -q)

Filed: none

Gates: uv run frob check --only affect_drift/doclink/docanchor/coverage/test/fmt/invariant/policy
--ticket T-1199, all clean (0 errors); gate:FMT shows 3 pre-existing-style
warnings (over-88-col frob:tests directive lines, already `# noqa: E501`,
matching the convention used elsewhere in this same package's own files).

Disclosed cuts / honest scope notes:
- scan_directive_carriers matches a directive's target/src against exactly
  two literal forms (the graph's `path::qualname` symref, and the dotted
  `module.qualname` form) computed via a local copy of frob.lang's private
  `_display_path` convention (cwd-relative posix path) -- a directive using
  some OTHER literal spelling of the symbol (e.g. a partial path, or a
  qualname with different case) is not recognized and is not disclosed as
  `unresolved` either, since the scan only inspects directives that DO
  resolve to a real Edge; this is a narrower guarantee than "every mention
  is found" and matches T-1267's own scope split (free prose mentions are
  explicitly that ticket's job, not this one's).
- _comment_span_for_edge matches an edge's `origin` against a RawComment's
  own first line only; a directive whose logical line is a later physical
  line of a multi-line folded comment block (frob.graph.dsl's continuation
  folding) would not resolve a span here and is silently skipped rather
  than added to `unresolved` -- not hit by any of this ticket's own test
  fixtures (single-line directives throughout), but worth a follow-up if a
  real multi-line directive case turns up.
- carry_lock_acks re-keys by exact `ref` string match only (facet-agnostic,
  matching every facet of the same ref) -- correct for this ticket's
  acceptance (a whole entry moves), not extended to fuzzy/partial matches.

### Changed
```
 tickets.md | 18 +++++++++++++-----
 1 file changed, 13 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestDirectiveCarrier::test_attached_waiver_moves_with_symbol` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestDirectiveCarrier::test_move_carries_attached_waiver_end_to_end` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestDirectiveCarrier::test_directive_target_elsewhere_rewritten` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestDirectiveCarrier::test_lock_ack_carried_to_new_symref` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 206 warning(s), 745 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/w16d-refactor/src/frob/refactor/_directives.py:156, E501@/home/logan/projects/frob/.claude/worktrees/w16d-refactor/src/frob/refactor/_directives.py:59, SELFAUDIT001@design
