+++
id = "01M3DG64EBREVXRQER8DSYX0M9"
title = "frob test reports NoRunner when a touched set contains test fixture data files (tests/fixtures/*.html): runner selection must ignore non-source fixtures or map them to the tests that reference them"
type = "bug"
category = "todo"
priority = "low"
points = 2
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:56Z"
aliases = ["T-6603"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/testing/_runners.py", "src/frob/testing/_collect.py", "docs/modules/testing.md", "docs/design/testing.md"]
+++

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
