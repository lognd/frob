## Done report

### Changed

- tests/test_ticket_leases.py::_run_with_bound (new helper): bounds a
  guarded call on a daemon thread with an asserted join(timeout) so a
  regression fails fast instead of hanging the test process.
- tests/test_ticket_leases.py::_expect_system_exit (new helper): thread-
  safe equivalent of `pytest.raises(SystemExit)` for use inside
  `_run_with_bound`'s target.
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger:
  wrapped the guarded `ticket_run` call in `_run_with_bound` (10s) and
  added a per-repo `frob.toml` `[tickets] land_wait_timeout_s = 1`
  override.
- tests/test_ticket_leases.py::TestDispatchLandGuard.test_refuses_mutating_verb_while_land_in_progress:
  same treatment.
- tests/test_ticket_leases.py::TestDispatchLandGuard.test_refused_verb_never_writes_the_ticket_file_at_all:
  same treatment.

### Root cause (measured, not the ticket's original hypothesis)

Instrumented `refuse_if_land_in_progress` (src/frob/tickets/_leases.py:1745)
directly rather than guessing. None of the ticket's three candidate
hypotheses held:

- `_land_flock_probe` correctly detects the held lock every poll (verified
  via the WARNING log line naming the correct pid/ticket_id each time).
- `_scan_for_live_land_process` correctly excludes `self_pid` and never
  matched the test's own process as a false landing process.
- The deadline arithmetic in the poll loop (`_resolve_land_wait_budget` /
  `deadline = monotonic() + remaining_budget`) is correct: it does reach
  and honor its deadline (confirmed by instrumenting a bare invocation --
  see below).

The actual defect is a test-authoring gap against T-1961/T-2023's own
(intentional, documented) redesign. T-1619 originally refused
IMMEDIATELY; T-1961/T-2023 changed the default to a BOUNDED WAIT
(`_LAND_WAIT_TIMEOUT_S = 330.0`, or `frob.toml`'s `land_wait_timeout_s`
override) before refusing -- "wait, the in-flight land is probably almost
done" rather than failing on the first probe. All three broken tests
simulate "a land is in progress" by holding `land.lock` IN-PROCESS
(`_land_lock(repo, ...)` as a context manager, or a raw `fcntl.flock`)
for the ENTIRE duration of their own assertion, and none of them override
`land_wait_timeout_s`. Because the lock is held by the very call stack
that is waiting on it, the exit condition (the lock coming free) is
correctly never observed until the caller's OWN `with` block exits --
which happens only after the guarded call returns -- so the loop
correctly, deliberately waits out its full ~330s default budget before
finally refusing. One sibling test in the same class
(`test_refuses_while_land_lock_held`) already avoids this by passing
`wait_timeout_s=0` explicitly; the three broken tests call through
higher-level entry points (`ticket_run`, `_refuse_if_land_in_progress_for_dispatch`)
that have no way to pass that override, so their only lever is a
per-repo `frob.toml` config (the same mechanism `_load_land_wait_timeout_s`
already documents as existing for exactly this purpose).

Direct evidence of a bare, un-bounded invocation running for its full
budget (captured before any fix, `pytest --timeout=140` killing it
mid-sleep at t=140.87s, still inside the poll loop and still correctly
warning "waiting for in-flight land to finish (up to 330s more)"):

  src/frob/tickets/_leases.py:1812: Failed
  E    Failed: Timeout (>140.0s) from pytest-timeout.

This repo's default `addopts` DOES carry a `--timeout=120` safety net
(pyproject.toml), so under a normal default `pytest` invocation these
three tests would each fail after ~120s rather than hang literally
forever -- but the repo's own documented workaround for the unrelated
`-n0`/xdist incompatibility (`-o addopts=""`, cited in the dispatch brief
itself) strips that safety net along with the xdist flags, which is
almost certainly how these were first observed as a true unbounded hang
rather than a slow ~120-330s failure.

### Is this related to the >500s `frob ticket doable` hang (T-2089)?

Plausible but NOT confirmed, and I did not stretch to connect them. The
dispatch-path call site (`_refuse_if_land_in_progress_for_dispatch`,
app/ticket_runner/__init__.py:494) uses the SAME production default
(no override reachable from the CLI), so any genuine, concurrently
running `frob ticket land` WOULD make every other mutating verb wait up
to ~330s before refusing (by design, not a bug) -- 330s + T-2089's
measured 207.5s sweep revalidation would exceed 500s. But `doable` is
listed among the read-only verbs I'd expect to be dispatch-guard-exempt,
and I did not instrument that specific run, so this is a hypothesis, not
a finding I am asserting as fact. Worth a coordinator follow-up
specifically measuring whether `doable` actually goes through
`_refuse_if_land_in_progress_for_dispatch` or is in
`_LAND_SAFE_READ_ONLY_VERBS`.

### Guard NOT weakened

The three fixed tests, plus the three pre-existing passing siblings in
the same two classes (`test_refuses_while_land_lock_held`,
`test_land_verb_itself_is_exempt`, `test_read_only_verb_runs_while_land_in_progress`),
all still pass (12/12 in the two classes) -- the guard still waits, then
still refuses, when a land is genuinely in flight. No production code in
src/frob/tickets/_leases.py was touched; only test fixtures changed.

### Evidence

- tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger
  -- bound to acceptance[0], designated repro (FAILED_AT_PARENT at
  c2d779f72bcdf8935dd612dcc7cb383da5ee7dd9, the test-only commit)
- tests/test_ticket_leases.py::TestDispatchLandGuard.test_refuses_mutating_verb_while_land_in_progress
  -- bound to acceptance[1] (also independently confirmed FAILED_AT_PARENT
  at the same base)
- tests/test_ticket_leases.py::TestDispatchLandGuard.test_refused_verb_never_writes_the_ticket_file_at_all
  -- bound to acceptance[1] (also independently confirmed FAILED_AT_PARENT
  at the same base)
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_refuses_while_land_lock_held,
  tests/test_ticket_leases.py::TestDispatchLandGuard.test_land_verb_itself_is_exempt,
  tests/test_ticket_leases.py::TestDispatchLandGuard.test_read_only_verb_runs_while_land_in_progress
  -- bound to acceptance[2] (guard-not-weakened), all pre-existing and
  still passing unchanged

Measured commands (all output read in full, not piped through tail/grep):
  uv run pytest -o addopts="" tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all -q
    -> pre-fix: 3 failed in 31.11s (bounded, fast, clean AssertionErrors)
    -> post-fix: 3 passed in 3.63s
  uv run pytest -o addopts="" tests/test_ticket_leases.py::TestRefuseIfLandInProgress tests/test_ticket_leases.py::TestDispatchLandGuard -q
    -> 12 passed in 4.60s
  uv run pytest -o addopts="" tests/test_ticket_leases.py -q
    -> 126 passed, 4 failed -- the 4 failures reproduce IDENTICALLY at
       HEAD~2 (before any T-2093 change), pre-existing T-2079 residue
       (an `anchor` dispatch verb + ownership guard not accounted for by
       this file's own test coverage), unrelated to this ticket. Filed
       as T-2103.
  uv run frob check --only test --ticket T-2093 -> gate:TEST 0 errors,
    25 warnings (repo-wide, pre-existing), 4 waived
  uv run frob check --land-parity -> clean, 0 unscoped errors (re-run
    after merging main to pick up 4 concurrently-landed tickets)
  git diff main --diff-filter=D --stat -> empty after the post-merge
    re-check (was non-empty before merging main; resolved by `git merge
    main`, no conflicts)

### Filed

T-2103 (renumbers at land): 4 pre-existing test failures in
tests/test_ticket_leases.py caused by T-2079's new `anchor` verb and
ownership guard not being accounted for by this file's own dispatch-
table-enumeration sentinel test and lease/steal fixtures. Out of scope
for T-2093; not touched here.

### Gates

frob check --only test --ticket T-2093: clean (0 errors)
frob check --land-parity: clean (0 unscoped errors, re-measured after
merging main)

### Changed
```
 tests/test_ticket_leases.py        | 131 +++++++++++++++++++++++++++++++------
 tickets/T-2093/ticket.md           |  46 +++++++++++--
 tickets/T-2103/ticket.md |  57 ++++++++++++++++
 3 files changed, 208 insertions(+), 26 deletions(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_land_verb_itself_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_read_only_verb_runs_while_land_in_progress` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2093
