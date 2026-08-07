## Done report

_load_diff (src/frob/gates/__init__.py) now returns a third signal,
diff_load_no_repo, distinguishing "root is not inside a git repository at
all" (repo_root() returns NotARepo) from "a real repo's working_diff
genuinely failed" (bad --base, detached HEAD -- both collapse to
GitError.GitFailed inside _merge_base/working_diff and were previously
indistinguishable).

coverage_gate gained a diff_load_no_repo parameter (default False, wired
through _GateInputs and run_gates' coverage job): COV002 and TODO001 only
fire the loud _diff_load_failed_violation when diff_load_failed is True
AND diff_load_no_repo is False. SCOPE001's check (_build_ticket_scoped_jobs)
was narrowed the same way. PRE001 was deliberately left unconditional on
diff_load_failed alone -- a no-ticket, no-repo root is still the B9 shape
PRE001 exists to catch (tests/test_gates.py::TestRunGates::
test_run_gates_blocks_prework_when_diff_load_fails_with_no_ticket, an
existing pinned test, still passes unmodified).

This fixes the tests/system/test_cli_check.py fixtures T-0705 flagged
(TestCheckCleanProject, TestCheckSkipFlags, etc. -- none of which call git
init) without touching PRE001's own protection.

tests/test_gates.py::TestGatesDegradeWithoutDiff::
test_diff_dependent_gates_block_loudly_on_failed_diff kept its ORIGINAL
name (not renamed) because T-0550's archived Done report
(tickets-archive.md:51628/51682) cites this exact pytest node id as
evidence -- COV003 flagged the rename as a broken evidence reference on
the first pass, so the test's SCENARIO was changed (git init + a real
commit + a bad --base, instead of no repo at all) while its name and
still-loud-COV002 assertion stayed intact. A new sibling test,
test_diff_dependent_gates_pass_quietly_on_a_genuinely_gitless_root, covers
the new genuinely-git-less-root behavior this ticket adds.

Measured: `uv run pytest tests/test_gates.py tests/system/test_cli_check.py
-p no:cacheprovider -q` -> all pass except
TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root,
which is a pre-existing xdist-worker-order flake unrelated to this change
(its own docstring documents the hazard: capsys/logging handler binding
order across workers) -- confirmed passing in isolation
(`pytest tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::
test_render_lint_gate_warns_not_errors_on_gitless_root -q` -> 1 passed) both
before and after this change.

`frob check --ticket T-0719 --only gates-fast`: clean on everything this
ticket's scope touches (gate:COV, gate:SCOPE both pass after `frob ack
coverage_gate` and scoping frob.lock/tests/test_gates.py in). Two
remaining FAILs (gate:DRIFT's DRIFT002 on src/frob/tickets/
_mutation_evidence.py, gate:TICK's TICK006 phantom-draft finding on
T-0711) are pre-existing repo-wide debt in files this ticket never
touches, present identically before this change.

No cuts: the ticket's own ask (distinguish COV002/SCOPE001/TODO001's
git-less-root case from a real repo's diff failure, without weakening
PRE001/T-0550's protection) is implemented as scoped.

### Changed
```
 tickets.md | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_dependent_gates_block_loudly_on_failed_diff` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestGatesDegradeWithoutDiff::test_diff_dependent_gates_pass_quietly_on_a_genuinely_gitless_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
