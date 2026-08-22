## Done report

Deliberate, reviewed SELFAUDIT001 fix, deferred from T-2323 to keep that
ticket's own scope narrow.

design/frob.strata: added tests/unit/verify/test_watermark.py to the
testsuite node's may "exec" via-list (subprocess.run calls in
_init_git_repo_with_commits, a real-git tmp-repo test fixture -- git
init/add/commit/rev-parse against an isolated tmp_path, not production
repo mutation) and may "env.read" via-list (os.environ read at the same
fixture, merging test env vars for the git commit). Both reviewed:
genuine, needed test-infrastructure effects on an isolated tmp fixture,
declared rather than restructured, same posture as every other
git-fixture test file already in these via-lists.

docs/design/registry/capability-via-ratchet.lock.json: bumped
testsuite::exec 176->177 and testsuite::env.read 4->5, each directly
attributable to this ticket's own two new via-list entries (one site
each, confirmed via a before/after `frob check --only sys` measurement
against unmodified main's design/frob.strata vs this worktree's).

A pre-existing, unrelated SYS003 finding (undeclared cross-component
import testsuite -> verify) was observed on this file during
verification -- confirmed present against UNMODIFIED main's
design/frob.strata too (same before/after check), not introduced by
this change and not this ticket's scope.

Verified: tests/unit/verify/test_watermark.py -- 18 passed (full file).
`frob check --only sys`: zero SYS111 findings for testsuite::exec/
env.read, zero undeclared-capability-effect warnings for
test_watermark.py (was 5: 4 exec + 1 env.read).

### Changed
```
 design/frob.strata                                    |  4 ++--
 docs/design/registry/capability-via-ratchet.lock.json | 12 ++++++------
 tickets/T-2340/ticket.md                              |  4 +++-
 3 files changed, 11 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2340/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2340, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
