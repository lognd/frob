## Done report

T-1559: land/close guard for orphaned frob:waive follow_up directives.

Changed:
- src/frob/tickets/_live_tracker.py: extended `_WAIVER_TICKET_PATTERN`
  (the `git grep -E` pattern `_waiver_pattern`/`live_tracker_citations`
  already use) with a third alternation matching a `follow_up="T-####"`
  waiver attribute, alongside the existing `ticket=`/`ticket "..."`
  alternatives. No new function, no new call site: `live_tracker_
  citations` is already wired unconditionally into both `frob ticket
  close` (`_done_transition_guard`, frob/tickets/_evidence.py) and `frob
  ticket land` (`_check_live_tracker_citations`, frob/tickets/_land.py),
  so this single pattern change closes the gap at both close-time and
  land-time for free.
- tests/test_tickets_live_tracker.py: new
  test_finds_comment_waiver_follow_up_attribute, mirroring the existing
  test_finds_comment_waiver_ticket_attribute test for the follow_up=
  case.
- docs/modules/tickets.md: extended the existing "Live-tracker citation
  preflight (T-0854)" section with the follow_up= binding and the
  2026-08-05 T-1490/T-1488 incident this ticket fixes.

Approach vs. acceptance criteria: acceptance[0] offers an explicit OR
("the close refuses ... OR a Tier-A auto-fix rebinds them") -- this
increment implements the REFUSE half only (reusing the existing,
already-battle-tested T-0854 refusal path and its message format, which
already names each citation's file:line and the remedy). An auto-migrate
Tier-A path is NOT implemented: it would need to invent or select a
successor ticket id, which this guard has no principled way to do
automatically, so refusal (forcing a human/agent decision) is the
correct default per the ticket's own OR clause.

Evidence: 1 pytest node id bound via the ticket evidence CLI (also bound
to both acceptance criteria via --accepts 0 --accepts 1), observed
passing (18 passed total in the file, including this one) under a
targeted pytest run of tests/test_tickets_live_tracker.py.

Gates: a repo-wide (not --ticket-scoped) run of invariant/prework/wire/
test/coverage stage groups shows zero findings naming _live_tracker.py
or the new test. gate:COV/TEST/WIRE/INV all pass clean; the lone
unwaived finding in that run (gate:PRE, PRE001) fires because the
invocation itself carried no --ticket flag on a non-T-####-named branch
-- a measurement artifact of the ad-hoc check command, not a finding
about any file this ticket touched.

Filed: none -- no out-of-scope work discovered.

### Changed
```
 docs/modules/tickets.md                            | 159 +++++++-
 src/frob/_cli_parsers/_ticket/_progress.py         |  18 +
 src/frob/app/_config_external.py                   |   2 +
 src/frob/app/config.py                             |   6 +
 src/frob/app/ticket_runner/_land_cmd.py            |  78 +++-
 src/frob/scaffold/data/shared/cpp/frob.toml.j2     |   8 +
 src/frob/scaffold/data/shared/python/frob.toml.j2  |   8 +
 .../data/types/pybind11-library/frob.toml.j2       |   8 +
 .../scaffold/data/types/pyo3-library/frob.toml.j2  |   8 +
 .../scaffold/data/types/python-tool/frob.toml.j2   |   8 +
 src/frob/scaffold/data/types/web-app/frob.toml.j2  |   8 +
 src/frob/tickets/_land.py                          | 101 ++++-
 src/frob/tickets/_live_tracker.py                  |  43 +-
 src/frob/tickets/_mutation_sweep_queue.py          | 399 ++++++++++++++++++
 src/frob/tickets/_profile.py                       | 354 ++++++++++++++++
 tests/test_tickets_live_tracker.py                 |  16 +
 tests/unit/test_mutation_sweep_queue.py            | 179 +++++++++
 tests/unit/test_profile.py                         | 123 ++++++
 tests/unit/test_scaffold_project.py                |  19 +
 tickets.md                                         | 446 ++++++++++++++++++++-
 20 files changed, 1938 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_comment_waiver_follow_up_attribute` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 567 warning(s), 787 waived
- error-findings: none (measured, zero errors)
