---
id: T-2068
title: xdist retry serial fix does not neutralise pyproject addopts -n auto
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_coverage_refresh.py
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Operator-side reproduction (2026-08-10), stronger evidence than this ticket''s
    original static reading: uv run pytest tests/unit/test_app_style.py -q -p no:xdist
    failed with ''unrecognized arguments: -n --dist=loadgroup'' even with -p no:xdist
    passed explicitly on the CLI -- pyproject.toml addopts still injected -n auto/--dist=loadgroup,
    confirming this ticket''s root-cause claim end to end; -o addopts="" instead worked
    (15 passed). NOTE: T-2086 (landed f843ad7ed5ffb32fac8ab304d42fe2f0a5af55ca, successor
    to T-2031/T-draft-4aa27f0c) already fixes this exact addopts-reinjection hole
    via _neutralized_addopts/-o addopts=<stripped>; this ticket may be a duplicate
    of already-landed work -- flagging for a coordinator pass rather than dropping
    it unilaterally.'
  evidence: []
- text: 'MEASURED ON MAIN AFTER T-2086 LANDED (f843ad7ed): this ticket is NOT redundant
    with T-2086. T-2086 fixed frob coverage internal xdist retry path (_strip_xdist_tokens
    in _coverage_refresh.py), but the OPERATOR-FACING surface still fails identically:
    `uv run pytest tests/unit/test_app_style.py -q -p no:xdist` on main at f843ad7ed
    gives `pytest: error: unrecognized arguments: -n --dist=loadgroup`, because pyproject.toml
    addopts injects `-n auto --dist=loadgroup` and `-p no:xdist` removes the plugin
    that would parse them. Workaround that works: `-o addopts=""`. Given that every
    agent brief tells agents to run scoped pytest subsets, this costs a wasted cycle
    per agent that reaches for the documented -p no:xdist flag. Acceptance: running
    pytest with -p no:xdist on any subset succeeds without a manual -o addopts override.'
  evidence: []
acceptance_amendments:
- op: remove
  index: 11
  old_text: coordinator pass to confirm and drop if fully subsumed.
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 10
  old_text: than dropping (see T-1968-adjacent caution on unilateral drops) -- worth
    a
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 9
  old_text: This ticket may now be a duplicate of already-landed work; flagging rather
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 8
  old_text: in _retry_after_worker_crash via _neutralized_addopts/-o addopts=<stripped>.
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 7
  old_text: T-2031/T-draft-4aa27f0c) already fixes this exact addopts-reinjection
    hole
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 6
  old_text: 'NOTE: T-2086 (landed f843ad7ed5ffb32fac8ab304d42fe2f0a5af55ca, successor
    to'
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 5
  old_text: root-cause claim end to end. `-o addopts=""` instead worked (15 passed).
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 4
  old_text: addopts still injected -n auto/--dist=loadgroup, confirming this ticket's
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 3
  old_text: even though `-p no:xdist` was passed explicitly on the CLI -- pyproject.toml's
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 2
  old_text: 'no:xdist` failed with `error: unrecognized arguments: -n --dist=loadgroup`'
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 1
  old_text: 'original static reading: `uv run pytest tests/unit/test_app_style.py
    -q -p'
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 0
  old_text: Operator-side reproduction (2026-08-10), stronger evidence than this ticket's
  new_text: null
  reason: 'cleanup: previous --criterion-file call split one note into per-line fragments
    due to no blank-line separators'
  actor: logan
  at: '2026-08-10'
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2032's `_strip_worker_count_flag` strips an explicit `-n`/`--numprocesses`
token from the argv `native_coverage_refresh` builds itself before
appending `-p no:xdist` for the serial retry. That closes the hole for the
EXPLICIT `-n <count>` this module appends in `_pytest_argv` (T-1672,
`_coverage_refresh.py:491-493`).

It does NOT close the hole for `pyproject.toml:171`'s
`addopts = "-q -n auto --dist=loadgroup --timeout=120 --timeout-method=thread"`.
pytest merges `addopts` into the effective command line regardless of what
explicit argv the caller passes -- `_strip_worker_count_flag` only sees and
can only remove tokens from the EXPLICIT argv list this module built, never
`addopts`' own `-n auto`. So a retry that hits this path with NO explicit
`-n` appended (the `worker_count is None` branch already documented at
`_coverage_refresh.py:476-483`: non-Linux, or memory could not be measured,
or `FROB_COVERAGE_MAX_WORKERS=0`) still carries `-n auto` in from `addopts`,
plus the retry's own `-p no:xdist` -- reproducing exactly the T-2032 bug
(`-p no:xdist` disables the xdist plugin, so pytest no longer recognises
`-n` at all and exits with usage-error code 4, collecting nothing) via a
path T-2032's fix does not cover.

Not reproduced/measured in this ticket (out of scope for T-2032's own file);
filed on report from a scope review of `_coverage_refresh.py`. Needs
verification (does the `worker_count is None` branch actually get hit in
practice, and does the retry then genuinely fail) plus a fix -- likely
passing `-p no:cacheprovider`-style `--override-ini="addopts="` on the
retry argv, or appending `-n 0`/`-p no:xdist` in an order proven to win
over addopts, whichever the pytest-xdist docs and a direct repro confirm.
