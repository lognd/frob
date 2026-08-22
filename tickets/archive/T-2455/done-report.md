## Done report

`related_tickets`' duplicate-title detector uses `difflib.SequenceMatcher.
ratio()` on raw title text -- a character-level metric with no notion of
words. Two short, genuinely unrelated single-word titles ("holder"/
"collider") scored 0.714, above the old 0.6 threshold, and the second
`frob ticket new` call in the pre-existing test
tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_
scope_colliding_with_other_in_progress_lease refused as an unacknowledged
duplicate before the test's own scope-collision assertion (T-1880) ever
ran.

Fix: raised _RELATED_TICKET_SIMILARITY_THRESHOLD from 0.6 to 0.8 --
clears the measured false positive (0.714) with margin below the real
near-duplicate precedent (T-1866/T-1986's reworded title, 0.907).
Documented the tradeoff and named the right longer-term fix (a
token/word-level metric, not another threshold chase) directly in the
constant's comment.

Regression test added directly against `related_tickets` (not a full
new+start replica of the pre-existing test, which frob-dup's DUP002
correctly flagged as a 100% duplicate block).

Evidence note: the new regression test was authored after the fix
commit, so no pre-fix ancestor commit in this ticket's own history
contains it -- `--check-repro`'s merge-base-based ancestor resolution
cannot produce a real verdict for it (T-2025's own documented
limitation, encountered pre-land here rather than post-land). Verified
manually instead: reverted the threshold to 0.6 in the worktree,
reran the test, confirmed the exact AssertionError this ticket
describes, then restored 0.8 and reconfirmed green. Recorded via
`--designate-repro-force` with that verification transcript as the
reason (visible on the evidence entry).

### Changed
```
 rapid-debt.jsonl                      |  2 ++
 src/frob/app/ticket_runner/_new.py    | 27 ++++++++++++++++---
 tests/unit/test_app_runners_batch7.py | 30 +++++++++++++++++++++
 tickets/T-2455/done-report.md         | 51 +++++++++++++++++++++++++++++++++++
 tickets/T-2455/ticket.md              | 29 +++++++++++++++++---
 5 files changed, 132 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_short_dissimilar_titles_are_not_flagged_as_related` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_scope_colliding_with_other_in_progress_lease` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
