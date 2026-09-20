## Done report

Changed: .github/workflows/ci.yml (macOS "Test (macos, timed with stack-dump-on-hang)" step)

Root cause (reproduced locally, not assumed): `$!` after backgrounding
`uv run pytest -q > >(tee ...) 2>&1 &` captures `uv`'s OWN pid, not the
real pytest/python process's pid -- `uv run` forks and supervises a real
child process rather than exec'ing into it. Measured directly: backgrounding
`uv run python -c '...'` and comparing `$!` to the child python's own pid
(via `ps --ppid $!`) shows they differ. So every `kill -ABRT "$pid"` in the
old step was aborting the `uv` binary itself, which has no
`PYTHONFAULTHANDLER` of its own -- confirmed by reproducing the exact
symptom locally: `uv` dies with "Aborted (core dumped)"/exit 134 and the
tee'd log gets nothing, precisely matching the incident (no stack, exit
134, no suite-result line).

Fix: background the already-synced venv's own interpreter directly
(`.venv/bin/python -m pytest`, no `uv run` supervisor in between) so `$!`
is the real process's pid. Verified end-to-end with a deliberately hung
script under the step's own exact background+watcher+ABRT-then-KILL shape
(short budget locally): the direct-interpreter form produces a full
faulthandler stack trace in the tee'd log; the unmodified `uv run` form
(also tested) produces nothing, reproducing the bug precisely. Also
verified the normal (non-hung) completion path still reports the real
pytest exit status unchanged.

Also added (acceptance [3]): the step now emits an
`::notice::macOS Test step finished in Ns against a 2400s budget (Ms
margin)` line on every completion, not only a timeout -- the previous run
finishing in ~39 of 40 budgeted minutes was a near-miss nobody could see
until it became this failure; this makes that margin visible going
forward.

Order followed per the ticket: the dump was fixed and proven first
(above). Not touching the budget -- no evidence yet exists (this run
produced no stack) that says whether the underlying cause was a slow
suite, a genuine hang, or an undersized budget; that decision is now
possible on the NEXT occurrence, with a real stack to read, per the
ticket's own explicit instruction not to raise the budget as a guess.

Evidence:
tests/test_ci_workflow_timeout.py::TestMacosTestStepSignalsTheRealInterpreter::test_macos_step_backgrounds_the_interpreter_directly_not_uv_run
tests/test_ci_workflow_timeout.py::TestMacosTestStepSignalsTheRealInterpreter::test_macos_step_reports_its_own_margin_on_completion
tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_macos_test_step_no_reruns_flakes

Two new locked-in tests (this diff's own additions to
tests/test_ci_workflow_timeout.py, existing precedent in this file for
testing ci.yml's parsed structure) confirmed by hand to fail against the
pre-fix content (`uv run pytest` on the backgrounding line) and pass
against the fix; a pre-existing sibling test in test_ci_workflow_matrix.py
had a stale literal-string assertion the invocation-shape change broke,
fixed to check invocation-shape-agnostically for its own actual concern
(no --reruns flag). Beyond that, this is a GitHub Actions workflow YAML
with no Python call-graph surface most of its own logic can bind evidence
to -- the primary verification is the local reproduction described above
(both the failure mode and the fix, each demonstrated against the step's
own exact shell shape: background+watcher+ABRT-then-KILL) plus a valid
`python3 -c "import yaml; yaml.safe_load(...)"` parse of the edited
ci.yml and a `bash -n` syntax check of the extracted `run:` block.

Filed: none

Gates: `frob check --ticket T-4274 --no-cache` clean of every finding
against .github/workflows/ci.yml (zero mentions of ci.yml in the full
output); the 10 remaining repo-wide errors (gate:COV, gate:LARGE) are
pre-existing debt in unrelated files (src/frob/serve/_daemon.py,
src/frob/gates/_tdd_order.py, tickets/T-4178's stale evidence cache) not
touched by this diff.

### Changed
```
 tickets/T-4274/done-report.md | 66 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-4274/ticket.md      | 31 +++++++++++++++++---
 2 files changed, 93 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_timeout.py::TestMacosTestStepSignalsTheRealInterpreter::test_macos_step_backgrounds_the_interpreter_directly_not_uv_run` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_timeout.py::TestMacosTestStepSignalsTheRealInterpreter::test_macos_step_reports_its_own_margin_on_completion` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_macos_test_step_no_reruns_flakes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 4633 warning(s), 956 waived
- error-findings: COV003@tests/test_excludes.py, COV007@src/frob/gates/_tdd_order.py, LARGE001@src/frob/serve/_daemon.py, lock-order-cycle@src/frob/serve/_daemon.py
