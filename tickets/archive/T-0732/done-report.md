## Done report

Delivered part (1) only: a shared CARGO_TARGET_DIR keyed per clone via
`git rev-parse --git-common-dir` (the one .git dir every worktree of a
clone shares), stored inside .git itself so no worktree's git status ever
sees it. Concurrency is cargo's own target-dir file lock, observed
directly serializing two real concurrent `make core` runs against the
same shared cache with no corruption. Measured with `time` across four
scratch worktrees (git worktree add /tmp/..., removed after measuring):
cold/empty-cache fresh worktree 30.4s, fresh worktree with a warm shared
cache 11.4s (only frob-core/strata-core themselves recompile against
their own worktree-local absolute path; every dependency crate is
reused), same-worktree steady-state re-run 1.1s (T-0340's existing
no-op case, unaffected). This is a ~2.7x cut for every worktree after the
first, but does not reach the <10s stretch target because the two path
crates recompile per worktree (cargo keys build output by absolute
source path) -- disclosed honestly in docs/guides/install.md rather than
rounded up. Part (2) (frob scaffold pool N, pre-warmed leased worktrees)
was not attempted -- filed as T-draft-77412664 per the ticket's own
"stretch, file a follow-up" instruction (grep-verified present in
tickets.md as `<!-- ticket:T-draft-77412664 -->` after this restore, per
the corrected 10b recipe -- an earlier round's T-draft-aaf3b076 mention
was prose-only, wiped by the `git checkout main -- tickets.md` restore
before it was ever committed; caught by reviewer, refiled and committed
immediately here instead of just noted in prose).

### Changed
```
 Makefile               | 32 ++++++++++++++++++--
 docs/guides/install.md | 66 +++++++++++++++++++++++++++++++++++++----
 tickets.md             | 80 ++++++++++++++++++++++++++++++++++++++++++++++++--
 3 files changed, 167 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present` (pytest node id, verified passing when recorded)
