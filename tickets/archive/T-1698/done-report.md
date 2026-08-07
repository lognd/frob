## Done report

Caught live: a three-agent wave deadlocked. Agent B landed T-1592, then
every subsequent land in the repo -- from any agent -- refused with
DirtyMain. Two agents burned roughly 25 minutes each retrying and
reporting, and neither could see the cause.

The cause was one uncommitted line. `record_rapid_debt` writes
`rapid-debt.jsonl`, which is tracked by design, and T-1684's
`spawn_deferred_post_land_sweep` calls it AFTER the land commit is sealed
(the record names that commit). Nothing then committed it, so root stayed
permanently dirty and `_refuse_if_main_dirty` -- correctly -- refused
every land behind it. Same class `_write_release_bump` already solved for
pyproject.toml / CHANGELOG.md / .frob-release.json: a land-owned file the
land writes and must therefore commit. The rapid debt record was added
without joining that discipline.

`_commit_rapid_debt` gives the line its own follow-up commit, staging
that ONE path. Deliberately not `git add -A`: concurrent lands race on
this same root, and a blanket add would swallow another agent's in-flight
work into an unrelated commit. Best-effort so it can never fail a land
that already succeeded, but logged at ERROR, because the resulting dirty
root is invisible in the DirtyMain error every other agent then hits.

Second, separable defect, and the one that made this cost 50 agent-
minutes instead of 2: the refusal did not name the offending paths. Both
blocked agents reported the same "root has uncommitted changes" with no
way to learn it was a single one-line file, and one recommended I inspect
it by hand. `describe_root_dirt` now names them, capped with an explicit
(+N more) so a truncated list cannot hide its own truncation, and it
decides by the SAME `.frob/`-ignoring rule `_porcelain_dirty` uses, so
what a refusal names can never disagree with what made it refuse. This
was verified in the field before it landed: agent A's third retry already
carried the improved message and listed the exact files. An error that
does not name its own cause is a structural defect in a tool whose entire
job is enforcement.

Kept honest under gate pressure rather than by waiving:
- `_land_git_ops` was already near ARCH102's export-cluster threshold, so
  the two new helpers collapsed into one public `describe_root_dirt` with
  private internals rather than being waived through.
- The regression tests use a real git repo and assert the ACTUAL
  invariant -- "root is clean after the debt write", "another agent's
  dirty file is still dirty afterwards" -- not that a commit helper was
  called. A mock would have proved nothing about the thing that broke.

One waiver, narrow and pointed: WIRE001 on the module-local test helper
`_seed_repo`. WIRE001 asks for a non-test caller, which a test helper by
construction cannot have. That is exactly the false-positive class T-1558
is open to fix at the gate, and the waiver names it as follow_up.
Widening the gate from inside this ticket would land that fix without its
own regression coverage.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_leaves_the_repo_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_stages_only_the_debt_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_a_real_dirty_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_truncation_declares_itself` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 787 warning(s), 720 waived
- error-findings: none (measured, zero errors)
