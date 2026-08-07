## Done report

Changed:
- tests/fixtures/dup_cross_lang/src/mod_a.py (new) -- Python accumulator-with-clamp
  (`compute_total`), same shape as tests/fixtures/dup_smart/src/mod_a.py's existing
  pair.
- tests/fixtures/dup_cross_lang/src/mod_b.ts (new) -- the same logic in TypeScript
  (`computeTotal`).
- tests/test_dup_cross_lang.py (new) -- runs both fixture symbols through the REAL
  `build_graph` -> `find_clones` pipeline (real `frob.lang` parse of both grammars,
  real `frob_core` bucketing/verification, no hand-built symbol records).

Finding: this is a documented NEGATIVE result, per the ticket's own instruction
("if vocabulary does not align, that is the finding -- document and file rather
than force"). Both symbols parse and fingerprint successfully (measured:
`stats.fingerprinted >= 2`), but `find_clones` reports zero clone groups for the
pair at every threshold tested (0.9, 0.7, 0.5, 0.3, 0.1) -- measured directly with
a scratch script before writing the test, then re-confirmed as the actual
`pytest` assertions. Root cause, read from `src/frob/dup/_pipeline.py`: R1
(`_r1_hash`) and R2 (`_r2_hash`/`_r2_normalize`) bucket candidates on literal
`body_tokens` -- R2 alpha-renames identifier-shaped tokens but passes every
keyword/punctuation token through unchanged, and R3 (`_r3_fingerprint`) runs over
the R2-normalized stream. Python's `def ... for item in items: ... if ...:` and
TypeScript's `function ... { for (const item of items) { if (...) { } } }` share
no token vocabulary once keywords/punctuation count, so R1/R2 buckets never
collide across the pair and `candidate_pairs` (frob_core) never surfaces it to R4
tree-edit-distance verification or R5 -- lowering the threshold cannot help
because the miss happens before any similarity comparison runs. This confirms
docs/modules/dup-sota-survey.md item 13's flagged risk exactly.

Filed: T-0334 (mints a real T-#### id once this worktree lands on
main -- `frob ticket new` on an off-default branch), title "frob.lang: give
cross-grammar node vocabulary so dup R1-R3 bucket structurally, not lexically",
scope `src/frob/lang/**` (out of T-0198's scope, so not touched here).

Evidence: recorded via `frob ticket evidence T-0198 <node-id>...` (both
resolved against a fresh `pytest --collect-only` pass; T-0519 deduped the
6x-repeated first line down to one entry -- see T-0519's Done report):
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_languages_parse_into_the_snapshot
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_symbols_are_individually_fingerprinted

All 7 (pre-dedup) pass: `uv run pytest tests/test_dup_cross_lang.py -v` -> "7 passed in 0.99s".

Gates: `uv run frob check --ticket T-0198` -> `gates 0 errors, 11 warnings, 202
waived` (clean; the pre-existing warnings/waivers are unrelated repo-wide debt,
not introduced by this ticket). `git diff main --diff-filter=D --stat` is empty
(deletion-filter land rule, section 9 of the playbook). `make coverage` (`pytest
--cov=src/frob --cov-branch --cov-report=xml -q` + `frob check
--stamp-coverage`) ran in the foreground to completion, exit 0, full suite green.

Disclosed gap (NOT fixed, NOT self-expanded): `uv run frob test --base main`
fails with `NoRunner: A language has selected tests but no [[test.runner]]` --
the new `tests/fixtures/dup_cross_lang/src/mod_b.ts` fixture is picked up by
touched-set selection as a "typescript" file, and `frob.toml` declares no
`[[test.runner]]` entry with `language = "typescript"` (only python/rust/strata
are configured). `frob.toml` is not in T-0198's declared scope
(`tickets.md`, `tests/**`, `src/frob/dup/**`), so this was not touched here.
The Python side of `frob test --base main` selects and passes cleanly
(`tests/test_dup_cross_lang.py` + the `.py` fixture, exit 0) before the
typescript-runner gap aborts the overall run. This is a real, disclosed
pre-existing gap, not silently worked around -- a coordinator/reviewer decision
is needed on whether to add a `[[test.runner]]` typescript entry (a separate,
`frob.toml`-scoped ticket) or exempt `tests/fixtures/**` from touched-set
language-runner requirements.

Not closed: leaving T-0198 for the reviewer/coordinator per the playbook's
review-gated flow (section 11.4) and per this dispatch's explicit instruction
not to close.
