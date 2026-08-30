## Done report

Root cause (bucket D, T-3488): git grep -E patterns in
src/frob/tickets/_live_tracker.py and src/frob/gates/_wire.py used \b
(word boundary) and \s (whitespace), both GNU regex extensions that are
not part of POSIX ERE. git grep -E on macOS links a regex backend that
does not honor them -- the compile does not error, the pattern simply
never matches -- producing exactly the observed "assert 0 == N" /
"assert not True" shape across 13 tests.

Fix: replaced \b with an explicit "(^|[^A-Za-z0-9_.-])"/"([^A-Za-z0-9_]|$)"
boundary pair (_LEFT/_RIGHT, _live_tracker.py already had _LEFT for the
same reason pre-T-3496; only _RIGHT was missing) and replaced \s with
[ \t] (not [[:space:]], since _drop_escaped_mentions's own docstring
confirms these SAME pattern strings are also re.compile()'d by Python's
re module, which does not understand POSIX [[:space:]] bracket-class
syntax -- a first attempt using [[:space:]] passed git grep fine but
broke the Python re side with 4 new failures, caught by the 3x local
run before landing). _wire.py's _base_name_match_paths got the same
_RIGHT-shaped fix for its own trailing \b.

Scope: added src/frob/tickets/_live_tracker.py and src/frob/gates/_wire.py
(the ticket's original scope was test-only; the fix required the
production regex patterns, reason recorded via `frob ticket scope --add`).

Evidence: tests/test_tickets_live_tracker.py (all) + tests/test_gates.py::
TestWireGate run 3x with -p no:xdist -- 61/61 pass all 3 runs.
`uv run frob test --base main` exceeded the 500s budget (exit 143);
relied on the scoped node-id runs per the verification-budget rule.

### Changed
```
 tickets/T-3496/ticket.md | 25 ++++++++++++++++++++++++-
 1 file changed, 24 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_deferred_disposition` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_registry_tracked_by_disposition` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_finds_strata_waiver_ticket_clause` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestTransitionRefusesOnLiveTrackerCitation::test_close_refused_when_registry_cites_this_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_public_function_with_no_caller_is_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
