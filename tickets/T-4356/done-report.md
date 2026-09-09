## Done report

VERDICT: intermittent, not deterministic. Ran the test 73 times locally
without reproducing the failure: 15 unloaded, 15 under all-core `yes`
CPU saturation, 8 concurrent duplicate invocations under the same
saturation, then 20 more concurrent duplicates under 24-way
oversubscribed load (12 cores). 0/73 failures. This matches the
ticket's own priors: the test passed on the immediately preceding CI
run of nearly the same tree, and T-3699 already records an
unreachable-daemon flake of the same shape on another platform.

ROOT CAUSE HYPOTHESIS (test-only, in scope): `send_request` in
src/frob/serve/_socketd.py defaults its socket timeout to 10s. The
test's own `_JOIN_BUDGET_S` is 20s and its adjoining comment (T-1635)
already documents that under `pytest-xdist -n auto` full-suite
contention this daemon's own thread/child scheduling can be delayed
well past what an unloaded box would need. The test called
`send_request(root, "frob_shutdown")` with the library default (10s),
a budget the test itself never chose and that is shorter than the 20s
of load-slack the test grants everywhere else. Under real CI
contention (13,860 collected tests, many workers), a daemon that is
merely slow to accept/answer -- not dead -- could exceed that 10s
window and be misreported as Unreachable, exactly the observed
failure shape (`Err(DaemonError.Unreachable).is_ok` is False) with no
code change and no reproducibility locally.

FIX (test-only, matches scope): pass `timeout_s=_JOIN_BUDGET_S` to
`send_request` so the RPC's own wait is aligned with the budget the
test already tolerates, instead of an unrelated hardcoded default.
This is not a retry -- it is correcting a budget mismatch within a
single attempt, consistent with T-3777's standing decision against
papering over flakes with reruns.

DIAGNOSTIC MESSAGE: the `assert response.is_ok` immediately after the
RPC previously carried no message at all, so a failure there rendered
identically to (and was easily confused with) the reap-budget
assertions later in the same test. It now reports elapsed time, the
specific DaemonError variant, and states explicitly that this failure
means the daemon could not be reached/answered -- not that shutdown-
and-reap behavior itself is broken.

PROOF STANDARD: 73 local passes (unloaded plus load-induced) is not
sufficient proof this specific interleaving can never occur -- only
that it is rare and load-dependent, consistent with the flake theory,
and that the identified budget-mismatch is a real, fixable
contributor. Proof this fully clears CI requires several consecutive
GREEN linux CI runs; I would want at least 3-5 consecutive full-suite
green runs before calling this closed off any single run, since a
single green run already burned trust today per the brief's own note
on the Windows retraction.

Changed:
tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget

Evidence:
tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget (frob ticket evidence)

Filed: none

Gates: frob check --ticket T-4356 clean across gates-fast/gates-native/gates-security/lint/static (0 errors; gates-fast required a `frob ticket sweep T-4356` pre-work-sweep re-run first, done above)

### Changed
```
 tests/test_serve_socket.py | 24 ++++++++++++++++++++++--
 tickets/T-4356/ticket.md   |  2 ++
 2 files changed, 24 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4730 warning(s), 956 waived
- error-findings: none (measured, zero errors)
