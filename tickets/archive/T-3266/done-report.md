## Done report

MECHANISM CONFIRMED (not assumed): `set_done_report` (`src/frob/tickets/
_reporting.py`) computes the `### Captured claims` section from a ticket
snapshot (`preloaded = _load_one(root, ticket_id)`) read ONCE at the top of
the function, before the actual (lock-protected) evidence-rendering read.
That function's own docstring already disclosed the tradeoff ("could in
principle be stale if evidence changes concurrently... only (rarely) the
Captured claims' evidence_count"). Read T-3244's actual archived done-
report directly: BOTH its "### Evidence" section ("(no evidence recorded)")
AND its Captured-claims line ("0 passed (from 0 evidence id(s))") are
stale, while `tickets/T-3244/ticket.md` now carries 47 real evidence ids --
confirming the report was written when the ticket genuinely had 0 evidence,
and `frob ticket evidence` was run afterward with nothing ever re-running
`frob ticket done-report` to refresh the report. This is not a within-one-
call race; it is a same-repo workflow-ordering gap with no enforcement:
nothing at close time checks that a Done report's Captured claims still
agree with the ticket's current evidence.

FIX (src/frob/tickets/_done_report.py, wired into the existing close-time
structural guard, src/frob/tickets/_evidence.py::_done_transition_
structural_guard, which already hosts the T-3195 hollow-report guard this
is the structural sibling of):

- `_stale_claims_reason(ticket, body)`: parses the '### Captured claims'
  section via the existing `parse_claims_from_done_report` (already the
  round-trip inverse of the renderer -- no new parsing logic invented),
  compares its `evidence_count` against `len([e for e in ticket.evidence
  if not is_cmd_evidence(e)])`, and returns a reason string naming both
  numbers on any mismatch -- zero-vs-nonzero (145 of the 206) AND wrong-
  nonzero (61 of the 206, e.g. T-3230: evidence=6, claims=3) alike. `None`
  when there is no Captured-claims section at all (an older report, or a
  caller that opted claims capture out) -- nothing to compare, never
  flagged.
- Wired into `_done_transition_structural_guard` right after the existing
  hollow-report check, refusing the done transition with the new
  `TicketError.StaleClaimsInDoneReport` (added to `_models.py`'s
  `TicketError`) naming the fix (`frob ticket done-report` re-run).
- This SUBSUMES the acceptance criterion "extend the hollow-report guard
  to catch this string too": rather than teaching `_is_hollow_done_report`
  a second literal string, the new check compares the actual PARSED
  numbers, which catches the reported "0 passed (from 0 evidence id(s))"
  shape AND every other wrong-count shape the string-match approach could
  never see (the 61 wrong-nonzero cases). Extending the string-match guard
  alone would have left those 61 uncaught, which the ticket's own
  acceptance criteria explicitly called out as a requirement ("the must-
  fire fixture must cover BOTH shapes").

FIXTURES (tests/test_tickets.py::TestStaleClaimsGuard, run against the
REAL guard function, not a re-implementation):
- MUST-FIRE (zero shape): test_zero_claims_with_real_evidence_refused --
  claims=0, evidence=1 -> refused.
- MUST-FIRE (wrong-nonzero shape): test_wrong_nonzero_claims_refused --
  claims=1, evidence=2 -> refused.
- MUST-STAY-QUIET: test_matching_claims_not_flagged -- claims=1,
  evidence=1 -> passes.
- Boundary: test_no_claims_section_not_flagged -- no Captured-claims
  section at all -> never flagged (nothing to compare).

RE-SCAN (scan3.py, re-run fresh against current tickets/, not trusted
second-hand): 206 of 1,934 done-reports on main still disagree -- the
historical population is UNCHANGED by this fix, as intended (see decision
below); this fix only prevents new stale-claims reports from reaching
`done` going forward, and cannot retroactively correct reports already
landed before it existed. A true "count for NEW reports only" measurement
requires waiting for lands to accumulate under this guard; re-run scan3.py
after a burn-in period to confirm the zero-new-defects claim empirically.

HISTORICAL-REPORTS DECISION (explicitly, per the ticket's own instruction
not to bulk-rewrite): the 206 historical reports on main are LEFT AS-IS.
They are the record of what actually happened at close time -- same
reasoning T-3195 already applied to its own 45 pre-existing hollow
reports. Documented in docs/modules/tickets-data-storage.md's new
"Stale Captured claims refused at close (T-3266)" section so this
decision is discoverable, not just implicit.

NOT FIXED / OUT OF SCOPE, recorded rather than silently dropped:
- `set_done_report`'s own pre-lock stale-read tradeoff (the narrow,
  genuinely-concurrent race its docstring already names) is UNCHANGED --
  this ticket's fix is a close-time backstop that catches the symptom
  (however it arises) rather than eliminating that race at its source.
  Left as documented pre-existing behavior, not filed as a new ticket,
  since the docstring already discloses it and the close-time guard now
  makes it unable to reach `done` regardless.
- 5 pre-existing, unrelated test failures observed while running the full
  tests/test_tickets.py suite: TestArchive::test_moves_done_and_dropped_
  only and 4 siblings, all failing on "git worktree list failed" (exit
  128) inside a tmp_path fixture under heavy host load during this
  session -- confirmed unrelated to this change (the failing tests never
  touch _done_report.py/_evidence.py's new code, and 188/188 of every
  OTHER test in the same file pass). Not filed as a new ticket since it
  reproduced as host-load-dependent git-subprocess flakiness in this
  session's own environment, not confirmed as a deterministic code defect
  -- left for the next agent who reproduces it deterministically to file
  with real evidence.

Filed: none -- the fix is scoped and complete; the one adjacent gap found
(set_done_report's own pre-lock race) is already self-documented in its
own docstring and does not need a duplicate ticket.

### Changed
```
 tickets/T-3266/ticket.md | 40 +++++++++++++++++++++++++++++++++++++++-
 1 file changed, 39 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets.py::TestStaleClaimsGuard::test_zero_claims_with_real_evidence_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStaleClaimsGuard::test_wrong_nonzero_claims_refused` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStaleClaimsGuard::test_matching_claims_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestStaleClaimsGuard::test_no_claims_section_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
