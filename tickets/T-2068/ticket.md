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
- text: Operator-side reproduction (2026-08-10), stronger evidence than this ticket's
  evidence: []
- text: 'original static reading: `uv run pytest tests/unit/test_app_style.py -q -p'
  evidence: []
- text: 'no:xdist` failed with `error: unrecognized arguments: -n --dist=loadgroup`'
  evidence: []
- text: even though `-p no:xdist` was passed explicitly on the CLI -- pyproject.toml's
  evidence: []
- text: addopts still injected -n auto/--dist=loadgroup, confirming this ticket's
  evidence: []
- text: root-cause claim end to end. `-o addopts=""` instead worked (15 passed).
  evidence: []
- text: 'NOTE: T-2086 (landed f843ad7ed5ffb32fac8ab304d42fe2f0a5af55ca, successor
    to'
  evidence: []
- text: T-2031/T-draft-4aa27f0c) already fixes this exact addopts-reinjection hole
  evidence: []
- text: in _retry_after_worker_crash via _neutralized_addopts/-o addopts=<stripped>.
  evidence: []
- text: This ticket may now be a duplicate of already-landed work; flagging rather
  evidence: []
- text: than dropping (see T-1968-adjacent caution on unilateral drops) -- worth a
  evidence: []
- text: coordinator pass to confirm and drop if fully subsumed.
  evidence: []
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
