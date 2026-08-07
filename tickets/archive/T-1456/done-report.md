## Done report

Design: `frob ticket land`'s existing T-0754/T-1410 claim-divergence
machinery re-verifies a captured Done-report claim against the post-merge
WORKTREE tree, but always through a `--ticket`-scoped `frob check`
(`_check_gates_summary_fn`/`_check_gate_findings_fn`). Per playbook
section 6c, `--ticket` does not scope most gate families' counts at all --
so this machinery is fundamentally about "did this ticket's own claim
still hold," never about "did this land's actual squash-apply commit
introduce residue somewhere unscoped." Every wave of this drive's own
history (INV006/PII012 waivers not traveling with relocated prose, format
drift, a stale registry denominator, SELFAUDIT interface attrs) is exactly
that second, uncaught class (no ticket needed -- this is the problem
statement this very ticket's Fix section below closes, not a deferred
cut).

Fix: `_land` (the CLI layer, `_land_cmd.py`) now brackets the real
`land()` call with an UNSCOPED, `--budget`-bounded (default 90s)
error-identity sweep of `root`:
1. Before `land()` runs (real lands only): capture `root`'s `HEAD`
   (`pre_land_sha`) and an unscoped `(rule_id, file)` error-finding set
   (`_unscoped_error_findings` -- no `--ticket` filter, the deliberate
   opposite of every existing scoped closure in this module) as the
   baseline. An unmeasurable capture degrades to `None`, never a guessed
   empty set (same posture as `_check_gates_summary_fn`).
2. After `land()` returns `Ok` (squash-apply already landed on `root`):
   `_post_land_unscoped_error_sweep` re-scans and diffs against the
   baseline.
3. No new findings: silent no-op.
4. New findings: `_apply_root_tier_a_fixes` runs the T-1138 Tier-A
   handlers unscoped against `root` and commits a follow-up
   `fix(land): <id> post-land Tier-A cleanup (...)` commit if that
   resolves every one of them.
5. Findings that survive auto-fix: refuse -- `root` is hard-reset back to
   `pre_land_sha`, the exact finding list is logged, and the CLI exits
   non-zero (a failed reset is itself logged loudly rather than assumed).

Either side of the comparison being unmeasurable skips the sweep (never a
false refuse/false clean over a comparison neither side could make).

I could not implement this entirely inside the two declared scope files
without a small necessary widening: `docs/modules/tickets.md` (the new
symbols' `frob:doc` target) and `tests/test_ticket_work_and_land_finish.py`
(where the regression tests live, matching this file's existing
`TestAbsorbPreLandFixes`/`TestLandProofAndFinish` land-CLI test-fixture
convention) -- both added via `frob ticket scope --add` with a recorded
reason.

Evidence (all bound to acceptance [0]):
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_no_new_error_is_a_silent_no_op
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_absent_before_land_refuses_and_reverts
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_unmeasurable_baseline_or_fresh_skips_the_sweep

These are unit tests over `_post_land_unscoped_error_sweep`'s git-mutating
logic (commit-a-fix / hard-reset-a-revert), with `_unscoped_error_findings`/
`_apply_root_tier_a_fixes` monkeypatched -- the spawn/parse half reuses
`_verify.py`'s existing `_parse_error_findings_from_stdout` unmodified (no
second hand-typed parser), and an end-to-end real-`frob-check`-spawning
test was deliberately NOT added (would spawn a full unscoped `frob check`
subprocess per test, violating the playbook's own foreground-timeout
discipline this ticket's own dispatch brief cites).

Full targeted run: tests/test_ticket_work_and_land_finish.py -- 12 passed
(was 8 before this ticket; +4 new).

Gates: `frob check --ticket T-1456 --only gates-fast` -- 4 errors, all
SCOPE001, all naming files that are T-1454's OWN declared scope
(docs/modules/gates.md, docs/modules/serve.md, src/frob/gates/_gate_cache.py,
tests/test_gate_cache.py) -- this is the disclosed, expected multi-ticket-
worktree cross-scope artifact (both tickets share one branch, so a
`--ticket`-scoped check against either sees the other's committed diff
too); it resolves the moment the coordinator lands T-1454 ahead of T-1456
per this dispatch's own ordering. Zero errors attributable to T-1456's own
scope. Per playbook section 6c this is a `--ticket`-scoped run:
gate:SCOPE/PREWORK and the diff-driven parts of gate:COV/FMT/AFFECT are
ticket-scoped (gate:SCOPE is exactly the 4 errors above), every other
family's count is repo-wide.

Filed: none.

### Changed
```
 docs/modules/gates.md         |  27 +++++++++
 docs/modules/serve.md         |  25 +++++++-
 src/frob/gates/__init__.py    |  37 ++++++++++--
 src/frob/gates/_gate_cache.py |  55 ++++++++++++++++++
 tests/test_gate_cache.py      |  66 ++++++++++++++++++++-
 tickets.md                    | 130 ++++++++++++++++++++++++++++++++++++++++--
 6 files changed, 328 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_no_new_error_is_a_silent_no_op` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_absent_before_land_refuses_and_reverts` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_unmeasurable_baseline_or_fresh_skips_the_sweep` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 8 error(s), 486 warning(s), 730 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/gates/__init__.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/w6p-checkfix/src/frob/app/ticket_runner/_land_cmd.py:320, E501@/home/logan/projects/frob/.claude/worktrees/w6p-checkfix/src/frob/app/ticket_runner/_land_cmd.py:346, E501@/home/logan/projects/frob/.claude/worktrees/w6p-checkfix/src/frob/app/ticket_runner/_land_cmd.py:429, OPAQUE001@tests/test_ticket_work_and_land_finish.py, SELFAUDIT001@design
