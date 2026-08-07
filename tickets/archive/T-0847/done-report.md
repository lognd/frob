## Done report

Fixed `_do_wip_commit` (src/frob/tickets/_land.py) to re-check staged state
after `git add -A` via `git diff --cached --quiet` before running `git
commit`. If the stage is empty (a normalization-only status line caused
`_porcelain_dirty` to see dirt, but renormalization during `add -A` restored
the identical committed blob), the function now returns `Ok(False)`
(nothing to snapshot) instead of proceeding to a `git commit` that would
exit 1 "nothing to commit" with no stderr and get misreported as
`LandError.GitFailed`.

Added `TestWipCommitNormalizationOnlyDirty` reproducing the exact fixture
from the ticket: a worktree with `core.autocrlf=true`, a committed LF file,
then the working-tree copy rewritten with CRLF endings (the WSL phantom-
dirty symptom) -- `git status --porcelain` reports it dirty, but after the
fix `land(..., dry_run=False)` succeeds with `wip_committed is False` and no
wip-snapshot commit is created.

Hand-verified mutant kill: removed the new `git diff --cached --quiet`
re-check block (add -A + straight to commit, old behavior) and reran the
new test -- it failed exactly as the ticket describes: `git commit` exited
1 with no stderr, logged as "land: ... wip commit failed: ... exit 1: (no
stderr)", surfaced as `LandError.GitFailed`. Restored the fix afterward and
reconfirmed the full `tests/test_ticket_land.py` suite passes (102 passed).

### Changed
```
 docs/modules/gates.md                          |   1 +
 src/frob/app/ticket_runner.py                  | 156 +++++++++----
 src/frob/gates/__init__.py                     |  23 ++
 src/frob/tickets/__init__.py                   |  12 +-
 src/frob/tickets/_land.py                      |  22 +-
 src/frob/tickets/_models.py                    |  45 +++-
 tests/test_evidence_integrity.py               |  51 ++++-
 tests/test_ticket_land.py                      |  40 ++++
 tests/unit/test_ticket_runner_gate_findings.py |  99 +++++++-
 tickets.md                                     | 306 ++++++++++++++++++++++++-
 10 files changed, 700 insertions(+), 55 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1238 warning(s), 222 waived
- error-findings: none (measured, zero errors)
