## Done report

Docs-only ticket: T-1364 asked to "consider" an explicit partial-stamp
marker for coverage gates as a T-1363 follow-up, not necessarily build it.

Decision recorded in docs/modules/gates.md, alongside T-1363's own
documented fixes: keep T-1363's "never promote a failed/partial run's
data" design as-is. It is sufficient for every realistic case reached in
practice -- a failed run leaves the prior good stamp untouched, and
TEST006's `_test006_missing` already discloses a genuinely-missing stamp
as a real violation, including the bootstrap case (no stamp has ever
existed and the very first run fails), which reads as "no data" rather
than a false clean. Building the explicit `"partial": true` marker plus
new TEST005/TEST006 disclosure wording would add real complexity (a new
stamp field, new gate wording, new tests) for a scenario that has not
occurred: T-1363's incident was specifically about a bad partial run
overwriting good data, which T-1363 already fixed by refusing the
promotion outright.

No code changed in src/frob/gates/_coverage.py or src/frob/gates/__init__.py
(the ticket's declared scope) -- there is nothing to fix there when the
decision is "keep the current design." Scope was extended by one file,
docs/modules/gates.md, to record the decision (the only place T-1363's own
parallel decisions already live), via `frob ticket scope T-1364 --add`.

Revisit criterion documented inline: a future incident where losing an
entire partial run's signal (rather than falling back to the prior stamp)
is itself the worse outcome -- e.g. a long stretch where every `make
coverage` attempt fails and TEST005/006 keep reporting against an
increasingly stale prior stamp with no partial-data signal ever surfaced.

Evidence: docs-only ticket with no pytest surface of its own (playbook
sec 5) -- bound to the existing CLI-dispatch integration test per the
T-0167 precedent, tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches, verified passing (1 passed).

### Changed
```
 tickets.md | 62 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 61 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 771 warning(s), 693 waived
- error-findings: none (measured, zero errors)
