## Done report

Root cause was narrower than the ticket's own diagnostic text: `_land_cmd.py`'s
rapid-profile call site passes `pre_commit_sweep=None` to `land()`, and
`_apply_pre_commit_sweep_or_unwind` (frob.tickets._land_squash) treats `None`
as "no sweep at all" -- not just "skip the full T-1514 unscoped sweep", which
is what rapid profile actually intends to relax. The full-tree sweep stays
skipped under rapid, unchanged; that relaxation is correct and out of this
ticket's scope. What was missing is a base level of formatting safety for a
rapid land's OWN touched files -- exactly what shipped the T-4088/T-4365
drift (fixed after the fact as T-4380).

Fix: `_squash_apply_on_disposable_stage` (src/frob/tickets/_land.py) now
substitutes a new `_default_touched_format_sweep` for a `None`
`pre_commit_sweep` on the plain-disposable-worktree path (the path already
taken exactly when no sweep was supplied, i.e. today's rapid shape) --
never touching the warm-stage branch used when a real sweep IS supplied
(every non-rapid profile, unaffected). The default sweep reuses
`frob.gates._land_format`'s existing pure touched-set/would-rewrite helpers
(the same ones LANDFMT001 and the T-4323 `_ruff_format_pre_land_step` apply
half already use) to run a diff-scoped `ruff format --check` + auto-apply
against exactly the `.py` files this land's own diff touches -- never a
whole-tree scan, never refuses the land (best-effort, matches this
project's established Tier-A auto-fix posture for a deterministic
formatter).

### Changed
```
 src/frob/tickets/_land.py             | 97 +++++++++++++++++++++++++
 tests/unit/test_land_stage_flip.py    | 78 ++++++++++++++++++++
 2 files changed, 175 insertions(+)
```

### Evidence
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_rapid_shape_default_sweep_formats_touched_files`
  (MUST FIRE: rapid shape -- no `pre_commit_sweep` supplied -- still formats
  a touched file before it reaches the flip's publish; asserted directly on
  the landed content)
- `tests/unit/test_land_stage_flip.py::TestDisposableStageFlip::test_explicit_sweep_is_never_overridden_by_the_default`
  (POSITIVE CONTROL: a caller that DOES supply its own `pre_commit_sweep`
  -- every non-rapid profile -- is unaffected; the unformatted touched file
  lands unchanged, proving the default never overrides an explicit sweep)

### Captured claims
- `uv run frob test` (touched-set): 53 python test(s), exit=0
- `uv run pytest tests/unit/test_land_stage_flip.py -q`: 10 passed
- `uv run frob check --ticket T-4381`: could not complete within this
  session's foreground budget under concurrent multi-agent load (repeatedly
  ran 30-40+ minutes without reaching its own Tool summary, confirmed alive
  via CPU/forkserver activity, not hung); an earlier partial run surfaced
  one `ruff-format` finding against this ticket's own edits, fixed via
  `frob format --code` before the touched-set test run above. Deferred to
  `frob ticket land`'s own inline check-gates spawn, which re-verifies
  against the merged tree before commit.
- `frob ticket evidence --check-repro`: both evidence ids are TEST_ABSENT_AT_PARENT
  against main -- expected for a brand-new test (neither existed before this
  ticket's own commits), not a repro-technique failure; see T-2025's own
  documented limitation.
