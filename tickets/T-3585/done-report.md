## Done report

Pulled the traceback from macos-latest job 99467133723 in run
33385515507 (gh api repos/.../actions/jobs/99467133723/logs). Root
cause: the before/after diff was ONE path,
.git/objects/maintenance.lock -- git's own background maintenance/gc
daemon creates and removes this lock file at unpredictable moments
while a repo sits on disk, entirely independent of clean()
(dry_run=True never touches .git/ at all). It raced the test's two
rglob() scans on that specific macOS runner.

Fix: exclude that one git-internal lock path from both snapshots via a
shared _snapshot_ignoring_git_maintenance helper, rather than
BUG002-waiving the whole test -- this is a genuine, fixable test
robustness gap (an untracked git-internal transient file legitimately
appearing between two scans), not an unfixable macOS-only defect.

Evidence:
- uv run pytest -p no:xdist tests/test_clean.py::
  test_clean_dry_run_removes_nothing: 1 passed
- uv run pytest -p no:xdist tests/test_clean.py: 15 passed (no
  regression to sibling clean tests)
- uv run ruff check tests/test_clean.py: clean

Filed: none

Gates: frob:no-behavior-change (test-filter-only fix, clean() itself
unchanged)

### Changed
```
 tests/test_clean.py      | 21 +++++++++++++++++++--
 tickets/T-3585/ticket.md | 13 ++++++++++++-
 2 files changed, 31 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_clean.py::test_clean_dry_run_removes_nothing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 26 error(s), 4111 warning(s), 891 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3585, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
