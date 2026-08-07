## Done report

Re-verified the 10 stale ticket-id citations T-1486 originally flagged
against the CURRENT tree rather than assume the ticket's stored list was
still accurate:

- Seven of the ten (docs/audits/README.md, docs/audits/perf.md,
  docs/modules/dup.md, docs/modules/serve.md, docs/modules/tickets.md,
  docs/strata/host.md's T-draft entry) no longer contain the flagged
  string at all -- already fixed by unrelated intervening work between
  T-1486's filing and this ticket being picked up. Nothing to change.
- The remaining three (docs/modules/gates.md's T-0104/T-draft-4e98abb1/
  T-draft-05d8f716, docs/strata/host.md's T-9999) are all inline-code-span
  examples illustrating the id SYNTAX itself (`` `Filed: T-0104` ``,
  `` `waive ... ticket "T-9999";` ``) -- DOC011's own scan
  (`_doc011_scan_doc`) already blanks fenced/inline code spans before
  matching, the same DOC008 convention, so these were never real
  findings; confirmed by re-reading the raw markdown around each line.

`uv run frob check --only docanchor` (unscoped) reports 0 DOC011 findings
against the current tree, both before and after the severity promotion
below -- the count really is provably zero, not just absent from this
ticket's own scoped view.

Promoted DOC011 from WARN to ERROR in
src/frob/gates/_doclink_docanchor.py::_doc011_violation, updated its
docstring to record the T-1542 investigation outcome (why all 10 turned
out to be non-issues, not fixes), and updated docs/modules/gates.md's
rule-catalog row to match. No test assertions needed updating --
tests/unit/gates/test_doc011.py checks rule id and message content, not
severity.

Verified with:
- `uv run pytest tests/unit/gates/test_doc011.py -p no:cacheprovider -q`
  -- 6 passed.
- `uv run frob check --only docanchor` (unscoped, FROB_NO_GATE_CACHE=1)
  -- 0 errors, 0 warnings, confirming the promotion introduces no new
  findings.
- `uv run frob check --only docanchor --only docblocks --only doclink
  --ticket T-1542` -- 0 errors, 4 pre-existing unrelated DOC006 warnings
  in tickets.md.
- `uv run frob check --land-parity` -- clean, 0 unscoped errors.

Added tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::
test_unknown_ticket_id_fires_at_error_severity (scope extended with
--reason) after `frob ticket close` refused on BUG002: this is the real
fail-at-parent/pass-at-fix test for the severity promotion -- it asserts
Severity.ERROR on every DOC011 finding, which fails against the
pre-T-1542 parent commit (severity was WARN there) and passes here. The
earlier two evidence ids only proved DOC011 still fires/doesn't-fire
correctly, not that its severity actually changed.

### Changed
```
 docs/modules/gates.md                |  2 +-
 rapid-debt.jsonl                     |  2 +
 src/frob/gates/_doclink_docanchor.py | 27 +++++++-----
 tests/unit/gates/test_doc011.py      | 17 ++++++++
 tickets.md                           | 81 +++++++++++++++++++++++++++++++++++-
 5 files changed, 117 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_unknown_ticket_id_fires_at_error_severity` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_known_active_ticket_id_passes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
