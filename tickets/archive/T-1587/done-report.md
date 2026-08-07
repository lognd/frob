## Done report

frob:no-behavior-change reason="the production fix (load_all/load_archive splicing, write_ticket splitting, set_done_report returning the merged ticket, v2 index cache keying) already landed on main via commit f08541dc (2026-08-05), BEFORE this ticket's branch point -- this ticket's own diff touches zero production code, only adds the TestV2FullLifecycleDoneReport integration test (T-1587's own suggested follow-up) and a docs/design/ledger-v2.md note. BUG002's designated-repro test correctly PASSES at the parent commit because the fix was already there; this claim asks BUG002 to require exactly that (pass at parent) instead of expecting a fail-then-pass delta that does not exist for a ticket whose only content is test/doc coverage of an already-shipped fix."

The code fix itself was already present on main (commit f08541dc, dated
2026-08-05, committed directly rather than through a ticket land) --
`load_all`/`load_archive` splice `done-report.md` back into `Ticket.body`
via `_merge_sibling_done_report`, `write_ticket`'s v2 branch splits it
back out via `_split_done_report` so a load-modify-write round trip never
duplicates the section, `set_done_report` (`_reporting.py`'s
`_store_done_report`) returns the merged ticket matching the next load,
and the v2 index cache keys on sibling `done-report.md` mtimes
(`_v2_cache_key_paths`) so a report write invalidates the cache. This
ticket's own record (state=queued, undispatched 48h) never reflected
that the fix had landed.

Verified the existing fix is complete and correct, then added the
ticket's own suggested follow-up:

Changed:
- tests/unit/test_ticket_store.py: `TestV2FullLifecycleDoneReport` -- a
  genuine end-to-end integration test (`new_ticket` -> `transition` to
  planned/in-progress -> `add_evidence` -> `set_done_report` ->
  `transition(..., DONE)`) against a real v2 repo, asserting the DONE
  transition does NOT refuse (the exact field incident: `frob ticket
  close` refusing a report written seconds earlier), and that a fresh
  `load_all` afterward still carries the report. The ticket's own body
  named this explicitly: "the unit layer missed this because each half
  was individually correct" -- write and read were each tested in
  isolation before, never chained.
- docs/design/ledger-v2.md: a short "on-disk split, in-memory canonical"
  note under the existing `done-report.md` bullet, naming the T-1587 fix
  and the two functions (`_merge_sibling_done_report`/`write_ticket`'s
  split-back-out) that keep the split from ever surfacing to a consumer.

Filed: T-1735 (SYS108 missing from _KNOWN_GATE_RULES,
self-model node count drift 23 vs 22) -- discovered running `frob test
--base main` after merging main into this worktree; confirmed via direct
test invocation that neither failure touches this ticket's scope
(`src/frob/strata/_selfconform.py`/`frob.gates._rule_id_scan`, unrelated
to `_store.py`/`_reporting.py`). Grepped `frob ticket list` for
"SYS108"/"self-model"/"selfconform" first; no duplicate found.

Evidence: tests/unit/test_ticket_store.py::TestSetDoneReport::test_v2_mode_writes_done_report_md_not_body, tests/unit/test_ticket_store.py::TestV2FullLifecycleDoneReport::test_close_does_not_refuse_recent_report, tests/unit/test_ticket_store.py::TestSetDoneReport::test_second_call_replaces_first_report, tests/unit/test_ticket_store.py::TestSetDoneReport::test_caller_never_touches_markdown, tests/unit/test_ticket_store.py::TestSetDoneReport::test_unknown_ticket_is_not_found

Gates: `frob check --ticket T-1587` clean (gate-summary 0 errors) after
merging main to the true current tip (this worktree's branch had NOT
re-merged main since the T-1672 land, which briefly produced phantom
COV002 findings against already-landed T-1677/T-1672 code -- resolved by
merging, not by touching that code). `tests/unit/test_ticket_store.py`
full file: 93 passed, 0 failed. `frob test --base main`'s full run
surfaces two PRE-EXISTING, UNRELATED failures (SYS108/self-model node
count, filed as T-1735 above) -- neither references this
ticket's scope; not claiming a clean full-suite run, only a clean scoped
one.

### Changed
```
 docs/design/ledger-v2.md        |  15 +++++
 tests/unit/test_ticket_store.py |  68 ++++++++++++++++++++++
 tickets.md                      | 122 +++++++++++++++++++++++++++++++++++++++-
 3 files changed, 204 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_v2_mode_writes_done_report_md_not_body` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestV2FullLifecycleDoneReport::test_close_does_not_refuse_recent_report` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_second_call_replaces_first_report` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_caller_never_touches_markdown` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_unknown_ticket_is_not_found` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 266 warning(s), 721 waived
- error-findings: none (measured, zero errors)
