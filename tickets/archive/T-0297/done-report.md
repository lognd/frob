## Done report

Implemented candidate (a) only (git-diff-aware private-rebind detection);
(b) and (c) filed as a follow-up ticket (see Filed below), each needs its
own design (call-graph reachability for (b); anchor-vs-publicness for (c))
rather than folding into the same comparison.

New gate `COV005` (ERROR) in `src/frob/gates/__init__.py`: for every file a
diff touches, it parses the SAME file's blob at `diff.base`
(`git show <base>:<file>`, via a same-suffix temp file through
`frob.lang.parse_file` + `frob.graph.dsl.parse_directives`) and compares
each `(kind, target)` directive pair's OLD binding against its NEW one. If
the pair bound a PUBLIC symbol at `diff.base` and now binds a PRIVATE one,
AND the new private symbol's own span overlaps one of this diff's hunks in
that file (i.e. the private symbol itself is part of what this diff just
touched, not an unrelated pre-existing private helper that happens to
reuse the same doc anchor elsewhere in the file), COV005 fires. The
span-overlap restriction was added after the first working version flagged
~50 pre-existing, untouched private helpers repo-wide that legitimately
share this repo's `frob:doc docs/modules/gates.md#public-api` anchor
convention across many public functions in one file -- `(kind, target)`
alone is not a unique directive identity here, so the naive file-wide
comparison was a real false-positive source, not just noise; confirmed by
re-running `frob check --delta` before and after adding the hunk-overlap
filter.

Changed:
- `src/frob/gates/__init__.py`: `_cov005`, `_cov005_file`,
  `_old_directive_bindings` (new, private); `coverage_gate` now calls
  `_cov005` alongside COV001-004/TODO001. `COV005` added to
  `_KNOWN_GATE_RULES` so `frob:waive COV005` validates like every other
  ERROR gate.
- `docs/modules/gates.md`: COV005 row in the rule catalog table, plus a
  design-decisions entry describing the actual firing condition (the
  hunk-overlap restriction, not a file-wide compare).
- `tests/test_gates.py`: three new `TestCoverageGate` cases --
  `test_cov005_directive_rebound_to_private_symbol_flags` (the T-0297
  repro: `frob:ticket` directive lands on an extracted `_foo_impl` helper
  instead of staying on public `foo`), `test_cov005_same_symbol_no_rebind_is_clean`
  (a body-only change to the same still-public symbol does not fire), and
  `test_cov005_no_old_blob_is_clean` (a never-committed file has no
  "before" to compare, so COV005 stays silent -- COV001 alone covers a new
  file's own missing-doc obligation).

Evidence (3 of 3 new tests, all pass):
- `tests/test_gates.py::TestCoverageGate::test_cov005_directive_rebound_to_private_symbol_flags`
- `tests/test_gates.py::TestCoverageGate::test_cov005_same_symbol_no_rebind_is_clean`
- `tests/test_gates.py::TestCoverageGate::test_cov005_no_old_blob_is_clean`
Recorded via `frob ticket evidence T-0297 <ids>`. Full `tests/test_gates.py`
passes. `frob check --delta --ticket T-0297` clean of any new/COV005
violations after the review-round fixes (stale ledger churn undone via a
fresh `git merge main`; `COV005` added to `_KNOWN_GATE_RULES`; docs
corrected to describe the hunk-overlap firing condition).

Not Filed: T-draft-e6aafc2f (never refiled) -- candidates (b) (`frob:tests` evidence with no
call-graph reachability to the bound symbol) and (c) (`frob:doc
#public-api` anchor on a private helper), both out of scope for this pass.

Review round 1: REJECTED for (1) stale ledger churn in tickets.md from a
stale worktree snapshot, (2) `COV005` missing from `_KNOWN_GATE_RULES`,
(3) docs/modules/gates.md misdescribing COV005 as file-wide rather than
naming the hunk-overlap guard. Core COV005 logic (git-diff-aware compare,
hunk-overlap guard, no-old-blob handling) was APPROVED and left unchanged.
All three fixed in this round: `git merge main` re-pulled the current
ledger so this diff touches only T-0297's own block; `COV005` added to
`_KNOWN_GATE_RULES`; the design-decisions entry now states the actual
firing condition.
