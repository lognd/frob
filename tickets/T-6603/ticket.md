---
id: T-6603
title: 'frob test reports NoRunner when a touched set contains test fixture data files
  (tests/fixtures/*.html): runner selection must ignore non-source fixtures or map
  them to the tests that reference them'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/testing/_runners.py
- src/frob/testing/_collect.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 1153
  new_length: 1153
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26, crunk T-0224): `frob test` on a
ticket whose touched set includes new tests/fixtures/*.html files exits
with NoRunner. Verified on dev c897d821a6: `_runners.py` returns
Err(NoRunner) whenever a language has selected tests but no
`[[test.runner]]` declares that language, and the touched-set language
classification treats a fixture .html under tests/ as a selected "html"
test file, so a data file with no runner refuses the whole run.

Deliver: files under a fixtures/ (or data/, __snapshots__/) directory
of the test tree, and any file whose suffix is not a test-source suffix
for a configured runner, are classified as fixture data, never as a
language with selected tests; a touched fixture selects the tests that
reference it by path (a git grep of the relative path inside test
sources), else contributes nothing; the run summary lists the fixture
files it mapped or skipped. Positive control: a touched set of one
.html fixture plus one test that reads it runs exactly that test; an
.html fixture nobody references runs nothing and exits 0 with a
"fixture data, no referencing test" line, not NoRunner.
