## Done report

Two independent layers, matching the ticket's plan.

Layer 1 (admission, src/frob/tickets/_leases.py): a new
`_looks_like_a_safe_git_argv_operand` predicate -- non-empty, no leading
`-`, matching a conservative allowlist `^[A-Za-z0-9._/-]+$` -- is applied
to both `branch` and `worktree` via `_lease_shape_is_safe`, checked in
BOTH parse paths that admit a `LeaseRecord`: `read_all_leases`'s per-file
parse loop and `_read_one_lease` (which `resolve_lease` calls). A record
that fails is dropped (never returned) and logged once per process per
file path via `_log_rejected_lease_once` (same pattern as T-0773's
`_stale_lease_logged`), so a long-lived daemon re-polling the same
peer-written evil file does not spam the log. Deliberately NOT full `git
check-ref-format` conformance -- documented inline: the allowlist exists
to make option-injection (leading `-`) structurally impossible, not to
validate every git ref-format rule; over-rejecting a merely-unusual but
legitimate ref would be worse than under-validating format details this
repo never actually shells out to `check-ref-format` to check anyway.
`branch="HEAD"` (T-0784's detached-HEAD sentinel) and absolute worktree
paths both pass the allowlist as-is, verified by test.

Layer 2 (argv, src/frob/serve/_daemon.py): `_merge_would_conflict`'s `git
merge-base` call now terminates options with `--` before its ref operands
(`git merge-base -- main branch`), verified directly against this repo's
git 2.34 baseline. `git merge-tree` (old-style, pre-`--write-tree`) does
NOT accept a `--` terminator on this git version -- verified directly,
`git merge-tree -- <a> <b> <c>` fails with a usage error -- so adding one
there would break every rebase-bot simulation rather than harden one; this
is documented inline with the verification note. `merge-tree`'s operands
are `merge_base` (git-computed) and `main_head` (self-resolved via
`rev-parse main`), never lease-sourced, plus `branch`, which is already
guarded by layer 1 before `_merge_would_conflict` ever sees it -- layer 1
alone is that call's defense, and the docstring says so explicitly rather
than implying `--` covers it.

Regression test (tests/test_serve_daemon.py::
TestPollRebaseBotLeaseInjectionGuard::
test_evil_lease_branch_never_reaches_git_argv): writes a lease file
directly to the shared leases directory (bypassing `record_lease`
entirely, simulating a peer worktree agent) with
`branch="--output=/tmp/x"`, spies on `frob.serve._daemon.run_argv`, runs
`poll_rebase_bot`, and asserts no captured argv call contains the payload
string, plus that a warning naming the rejected ticket id was logged.

Six more unit tests in tests/test_tickets_leases.py::
TestLeaseShapeValidation cover: a dash-prefixed `branch` dropped by
`read_all_leases` (with the once-per-process log assertion isolated into
its own test), a dash-prefixed `worktree` dropped the same way, a
legitimate branch name still admitted, the `branch="HEAD"` sentinel still
admitted, and `resolve_lease` surfacing an evil-branch lease as
`NoLeaseForTicket` (the same loud failure as no lease at all, via the
separate `_read_one_lease` code path).

Verification: ran the ticket's `--only` stage groups
(lint/static/gates-fast/gates-native/gates-security) scoped to T-0780,
all 0 errors; `uv run frob test --base main` (touched-set) returncode=0;
`uv run pytest tests/test_serve_daemon.py tests/test_tickets_leases.py
tests/system/test_spawn_budget.py -q` -- 33 tests collected, all passed
(green, no failures); `git diff main --diff-filter=D --stat` is empty.

Deviation from the literal acceptance wording: the acceptance text reads
"daemon merge-base/merge-tree invocations follow a -- terminator"
(plural). Only `merge-base` actually gets one -- `merge-tree` cannot, on
this repo's git 2.34 baseline, without breaking every simulation (verified
directly, not assumed). The security property the ticket cares about
(no git call ever receives an injected operand) still holds for
`merge-tree` via layer 1's admission-time rejection, proven by the
regression test above. This is disclosed here rather than silently
following the letter of the acceptance text over its actual intent.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_branch` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_drops_a_dash_prefixed_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_admits_a_legitimate_branch` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_detached_head_sentinel` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_resolve_lease_treats_an_evil_branch_as_no_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_rejection_is_logged_once_per_process` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollRebaseBotLeaseInjectionGuard::test_evil_lease_branch_never_reaches_git_argv` (pytest node id, verified passing when recorded)
