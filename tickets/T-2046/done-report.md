## Done report

Widened `_commit_orphaned_new_ticket_dir_only_drift` (src/frob/tickets/_land.py)
from a SOLE-dirty-path match to an ALL-qualifying-dirty-paths match: every
dirty path (ignoring .frob/) must independently be an untracked, cleanly-
parsing tickets/T-####/ directory whose only entry is ticket.md and whose
parsed id matches the directory name. If ANY dirty path fails, nothing is
committed -- all-or-nothing, matching the ticket's explicit "do not
partially heal" requirement.

Repro technique used (playbook 7b): committed the three new tests alone
first (7533a2037), ran them, confirmed
TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
FAILED against the still-SOLE-only guard (assert False is True), then
committed the fix separately (04584ee90) and designated that same node id
as repro against 7533a2037 -- `frob ticket evidence --check-repro` reports
FAILED_AT_PARENT, a genuine repro.

Acceptance criterion 4 (report whether the two precedent guards in
_land_git_ops.py have the same class-vs-instance mismatch): checked both.
`_restore_lock_version_only_drift` and `_commit_rapid_debt_only_drift`
each guard exactly ONE specific named file (uv.lock, rapid-debt.jsonl
respectively) -- for those, "this file and nothing else" is the correct
shape; there is no class of paths to generalize over, so SOLE is genuinely
correct for both. Only the T-2026 guard matched a CLASS (any orphaned
ticket dir), which is what made SOLE wrong there specifically.

Verification: `pytest tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py`
-- 12 passed (was 9 before this ticket; the 3 new tests are the repro
class). `frob check --land-parity` (run twice under heavy land
contention; first attempt could not evaluate, second succeeded): reports
exactly 2 unscoped errors, both F401 in tests/test_gates_fmt_directives.py
and tests/unit/test_tickets_evidence_only_scope.py -- confirmed via
`git diff main --stat` on those two files that this worktree carries NO
changes to either; they are pre-existing repo-wide floor, unrelated to
this ticket's change.

gate:ARCH's ARCH001 on `_commit_orphaned_new_ticket_dir_only_drift`
(120 lines, threshold 60) is NOT a new violation this ticket introduces:
at this ticket's own base commit (56d21d893) the same function was
already 98 lines, already over the 60-line threshold, unwaived. This
ticket's all-or-nothing multi-path loop grew it further but did not cross
a compliant-to-noncompliant line; decomposing it is a separate
refactor outside T-2046's declared scope and not attempted here.

### Changed
```
 src/frob/tickets/_land.py                          | 159 ++++++++++++---------
 .../test_land_dirty_main_orphaned_ticket_t2026.py  |  71 +++++++++
 tickets/T-2046/ticket.md                           |  54 ++++++-
 3 files changed, 216 insertions(+), 68 deletions(-)
```

### Evidence
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, F401@/home/logan/projects/frob/.claude/worktrees/t2046-t2048/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2046-t2048/tests/unit/test_tickets_evidence_only_scope.py, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2046, SELFAUDIT001@design
