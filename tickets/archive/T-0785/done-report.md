## Done report

## Done report

Changed:
src/frob/dup/_pipeline.py::_ERROR_EXIT_MARKER
src/frob/dup/_pipeline.py::_matching_close_paren
src/frob/dup/_pipeline.py::_normalize_error_channel
src/frob/dup/_pipeline.py::_r2_normalize
src/frob/dup/_pipeline.py::_r4_alignment
tests/test_dup.py::TestErrorChannelNormalization
tests/test_dup.py::TestErrorChannelDupPairing
tests/test_dup.py::TestErrorChannelNormalizationDoesNotOverFire

Normalization design: `_normalize_error_channel` canonicalizes three
error-exit shapes to one marker before token-level similarity comparison --
`return Err(...)` and `return None` both collapse to `return $err_exit`
(payload/enum-member tokens dropped, only the exit SHAPE is compared);
`return Ok(<expr>)` unwraps to `return <expr>` (same happy-path payload an
`Optional` function returns bare); a `raise ...` statement (argument run
bounded by the next depth-0 `_STMT_STARTERS` token) also collapses to
`return $err_exit`. Wired in at two points: (1) inside `_r2_normalize`
(runs first, before alpha-renaming), so every rung built on the R2-normalized
stream -- R2's own hash, R3, R4's winnow-fingerprint candidate discovery,
the DECKARD-style prefilter vector, R1.5's region kernel -- compares
error-signaling idioms as the same shape; (2) inside `_r4_alignment`
(applied to `state.body_tokens_by_ref`, RAW real-identifier text, right
before `_split_statements`), because R4's near-miss floor/alignment
deliberately does NOT go through R2's alpha-renaming (real identifier text
still has to line up for its per-statement exact-hash match) -- without
this second site the floor check for the motivating pair stayed on raw
`Err(...)`/`None` text and never saw the normalization at all. `R1` (exact
whole-body hash) and the cache-key digest (`_digest`) intentionally still
see fully raw, un-normalized tokens -- unaffected by design, since R1
exists to catch literal-identical text and changing its input would widen
its blast radius repo-wide in a way this ticket does not ask for.

Repo-wide dup-group delta: measured via `frob check --only static` (the
`frob-dup` gate) against this worktree's `main`-merged tip, with
`.frob/dup.db` cleared before each measurement (its verdict cache is keyed
by content digest, which the normalization does not change, so a stale
cache silently reuses pre-change verdicts and hides the real delta --
caught and corrected mid-ticket). BEFORE (code reverted via `git checkout
--`, patch saved and reapplied, no `git stash` used): 117 duplicate groups
(110 waived). AFTER (normalization in place): 117 duplicate groups (110
waived) -- delta = 0 new groups. The only line-level difference between the
two full `frob-dup` outputs is one PRE-EXISTING group (a fixture-writing
boilerplate pattern already shared by `TestR3LiteralAbstraction`/
`TestR3ElifDesugar`) growing from 2 to 4 members because my own two new
test classes' fixtures happen to match that same pre-existing boilerplate
shape -- not a new group, and not source code the normalization touched.
No new false pairs anywhere in the repo.

Deviation (disclosed, not silently dropped): the ticket's motivating case
asks for the literal current `frob.tickets._leases.git_common_dir` /
`frob.gates._exclude_hazard._git_common_dir` pair to register. Measured
directly (see `_r4_alignment` trace during implementation): those two
functions differ along TWO independent axes, not one -- the error-channel
shape this ticket is scoped to, AND an orthogonal control-flow difference
(`git_common_dir` merges both failure checks into one combined `if ... or
...:` since both branches map to the same `Err(LeaseError
.GitCommonDirUnavailable)`; `_git_common_dir` keeps them as two separate
`if`s because each logs a DIFFERENT debug message). With only the
error-channel axis normalized, the real current pair's near-miss floor
similarity is 0.444 (below the hardcoded `_R4_SIMILARITY_FLOOR = 0.6`) --
it does NOT register today. A fixture with the error-channel difference
isolated (both sides using the same combined-`if` structure, otherwise
matching the real functions' variable names/messages/logic) reaches 0.799
similarity and DOES register (rung `r4`) -- this is
`TestErrorChannelDupPairing`'s fixture, and it is what the ticket's own
literal acceptance criterion asks for ("two functions identical except one
returns Result and the other Optional-with-None"). Collapsing the
combined-vs-split-`if` divergence is a second, genuinely independent
normalization dimension (control-flow desugaring, not error-channel
shape) that is out of this ticket's scope; filed as a follow-up rather
than silently left unaddressed or force-fit into this ticket:
T-0801 "dup: normalize combined-vs-split early-return conditionals before
similarity compare (control-flow axis the real git-common-dir pair still
needs, T-0785 follow-up)".

Evidence:
tests/test_dup.py::TestErrorChannelNormalization::test_err_and_none_collapse_to_the_same_marker
tests/test_dup.py::TestErrorChannelNormalization::test_ok_unwraps_to_the_bare_payload
tests/test_dup.py::TestErrorChannelNormalization::test_raise_collapses_to_the_same_marker_as_err_and_none
tests/test_dup.py::TestErrorChannelNormalization::test_a_genuinely_different_return_value_is_not_collapsed
tests/test_dup.py::TestErrorChannelNormalization::test_nested_err_argument_parens_do_not_confuse_the_close_paren_scan
tests/test_dup.py::TestErrorChannelDupPairing::test_result_and_optional_git_common_dir_register_as_a_duplicate_group
tests/test_dup.py::TestErrorChannelNormalizationDoesNotOverFire::test_genuinely_different_logic_does_not_falsely_pair
(all 7 bound via `frob ticket evidence T-0785 ... --accepts 0`; observed
`uv run --frozen pytest tests/test_dup.py -q` -> 15 passed, all of
tests/test_dup.py including the pre-existing 8 tests unaffected)

Filed: T-0801 (control-flow-axis follow-up, see Deviation above).

Gates: `frob check --ticket T-0785 --only lint` clean (0/0). `--only
static` clean of anything my scope touched after `frob ticket sweep
T-0785` re-ran the stale pre-work sweep (PRE001 cleared); remaining static
errors (DOC001 on docs/audits/frob-blindspots-2026-07-23.md, TEST010 on
tests/test_perf_loop_invariant_effect_lock.py and
tests/system/test_spawn_budget.py, TICK006 on T-0766's Done report,
DOC004 on docs/guides/install.md) are pre-existing, outside
`src/frob/dup/**`/`tests/test_dup.py`, and unrelated to this change
(confirmed no `frob/dup` or `test_dup` hit in any FAIL-level line).
`--only gates-native` clean (exit 0). `--only gates-security` clean (exit
0). `frob test --base main` (foreground, ~7 min) surfaced ~25 pre-existing
failures repo-wide (doctor/system/strata self-model/CLI-check tests) with
zero mention of `frob.dup`/`test_dup.py` -- not investigated further as
out of this ticket's scope; noted here rather than silently omitted.
`git diff main --diff-filter=D --stat` empty (no unintended deletions).

### Changed
(no changed files detected)

### Evidence
- `tests/test_dup.py::TestErrorChannelNormalization::test_err_and_none_collapse_to_the_same_marker` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestErrorChannelNormalization::test_ok_unwraps_to_the_bare_payload` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestErrorChannelNormalization::test_raise_collapses_to_the_same_marker_as_err_and_none` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestErrorChannelNormalization::test_a_genuinely_different_return_value_is_not_collapsed` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestErrorChannelNormalization::test_nested_err_argument_parens_do_not_confuse_the_close_paren_scan` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestErrorChannelDupPairing::test_result_and_optional_git_common_dir_register_as_a_duplicate_group` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestErrorChannelNormalizationDoesNotOverFire::test_genuinely_different_logic_does_not_falsely_pair` (pytest node id, verified passing when recorded)
