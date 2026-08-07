## Done report

The T-0575 reviewer found: evaluate_gate promoted a quarantined test back
to green purely on quarantine_ticket being set, never re-checking is_flaky,
and quarantine_alarms only fires while is_flaky is true. A quarantined test
whose recent history has regressed to all-fail is by definition not flaky
anymore (is_flaky's own rule excludes all-fail), so it silently fell out of
both checks: gate-green forever, alarm never fires -- a live quarantine
masking a permanent regression with no signal anywhere.

Chosen semantics (both surfaces fixed, kept as two distinct signals since
they call for different responses):

- New `is_hard_regression(entry)`: bounded history has at least 3 recorded
  runs (one above the flake minimum, so the run right after quarantine
  can't misfire) and every one is a fail.
- `evaluate_gate` now excludes any quarantined node id flagged by
  `is_hard_regression` from the "excused" set before checking
  `failing_node_ids <= excused` -- a hard-regressed quarantined failure
  keeps the run red even with `quarantine_ticket` still set.
- New `hard_regression_alarms(entries)`: pure, no root/ticket lookup,
  returns every currently-quarantined node id that is_hard_regression flags
  -- deliberately NOT merged into `quarantine_alarms` (the expiry alarm),
  since a closed-ticket-still-flaky alarm calls for "re-triage the ticket"
  while a hard-regression alarm calls for "the fix was never applied at
  all, revisit the quarantine entirely".

docs/modules/testing.md's Flake quarantine section (semantics + public API
listing) updated to document is_hard_regression, hard_regression_alarms,
and evaluate_gate's revised exclusion rule.

Left out of scope, filed as a follow-up (a lost draft (its scope is covered by T-0635), minted off
main so will get a real T-#### id once merged): `frob.testing.__init__`
does not yet re-export `is_hard_regression`/`hard_regression_alarms`, and
no CLI path (`frob test`) calls `hard_regression_alarms`/`evaluate_gate`
automatically yet -- same pre-existing gap `track_python_stability` already
had, noted in the module's own "known limitation" paragraph.

Also out of scope, left for land: gate:REL (REL001, public API bump)
fires because this change adds public symbols; per this repo's own commit
history (chore(release) commits are consistently a separate land-time
step, not part of an implementer's own commit) the version bump belongs
to the coordinator at land, not this ticket's declared scope
(pyproject.toml is not in T-0636's scope).

### Changed
```
 docs/modules/testing.md              |   49 +-
 src/frob/testing/_stability.py       |   85 ++-
 tests/unit/testing/test_stability.py |   67 +-
 tickets.md                           | 1401 +++++++++++++++++++++++++++++++++-
 4 files changed, 1587 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/testing/test_stability.py::TestHardRegression::test_past_thresh` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestHardRegression::test_under_thresh` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestHardRegression::test_mixed` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestAlarms::test_hard_alarm` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestAlarms::test_hard_no_alarm_flaky` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestGate::test_hard_regress_fails` (pytest node id, verified passing when recorded)
