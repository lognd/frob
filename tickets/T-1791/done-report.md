## Done report

T-1791 wires frob.verify._quarantine.raise_quarantine into the batch-
verification driver, which existed (T-1693) but was never called.

The call site is _raise_quarantine_for_red_batch, invoked from
_file_regression_ticket -- the shared "a red batch verification came
back" seam BOTH T-1684's per-land deferred sweep and T-1688's
coalescing worker call through, so wiring the raise at this one call
site covers both drivers without a second integration point (T-1688's
own docstring names _file_regression_ticket as its filer).

batch_commit_shas comes from the current verify queue (frob.verify.
queue_status) -- the exact set of lands the red result could have been
caused by. Each QuarantinedFinding reuses the SAME Attribution mapping
_file_regression_ticket already computes for its own ticket body (one
attribute_batch call, not two) -- _partition_findings_by_attribution's
signature changed to accept that mapping as a parameter rather than
recomputing it.

Quarantine raises even when every pair in the batch already attributes
to a still-open ticket and no NEW regression ticket gets filed: the
breaker's question is "did the tree go red", not "did filing produce a
new ticket" -- conflating the two would let an all-already-tracked red
batch slip past the breaker with deferred landing still enabled.

An empty/unreadable verify queue skips the raise (logged at WARNING,
nothing to name as the raising batch); a raise_quarantine failure is
logged at ERROR and swallowed -- the regression ticket this function
files is still the durable record, and a caller filing a real
regression must never be blocked by the quarantine flag failing to
persist.

_raise_quarantine_for_red_batch was split (ARCH001, 67 vs 60 lines)
into itself plus _quarantined_findings_from_attributions.

Disclosed out-of-scope finding: two tests/unit/test_rapid_sweep.py::
TestDescribeRootDirt tests fail against the current describe_root_dirt
output shape on a clean worktree at main tip, unrelated to this
ticket's own change (src/frob/tickets/_land_git_ops.py is not in
scope). Filed as T-1821 (draft id; renumbers at land) rather than
fixed here.

frob check --ticket T-1791: 0 errors.
frob check --land-parity: clean, 0 unscoped errors.

### Changed
```
 docs/modules/tickets.md                    |  35 ++++++--
 src/frob/app/ticket_runner/_rapid_sweep.py | 131 +++++++++++++++++++++++++--
 tests/unit/test_rapid_sweep.py             | 140 ++++++++++++++++++++++++++++-
 tickets/T-1791/ticket.md                   |  41 ++++++++-
 tickets/T-1821/ticket.md         |  23 +++++
 5 files changed, 351 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_empty_queue_logs_and_skips_the_raise` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raised_even_when_every_pair_already_has_an_open_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raise_failure_is_logged_not_raised` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 907 warning(s), 733 waived
- error-findings: none (measured, zero errors)
