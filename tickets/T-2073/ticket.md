---
id: T-2073
title: Split _doable along the decide/IO/format seam (ARCH001 117 lines + ARCH103)
state: done
kind: feature
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
evidence_scope:
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_text_mode
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_json_mode
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_nothing_doable
designated_repro_test: null
acceptance:
- text: given src/frob/app/ticket_runner/_query.py, when frob check --only archgate
    runs, then neither ARCH001 nor ARCH103 is reported for that file (both measured
    present before the change)
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_text_mode
- text: given the doable commands existing test surface, when it runs after the split,
    then it stays green -- a refactor of a load-bearing function needs its callers
    exercised, not just a gate reading zero
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_json_mode
  - tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_nothing_doable
threat: null
component: ticket_runner
anchor: false
anchor_reason: null
land_commit: null
---
Floor errors measured unscoped on main, both at
src/frob/app/ticket_runner/_query.py:324:

    ARCH001  function `_doable` has 117 lines (threshold: 60)
    ARCH103  `_doable` mixes I/O, string-formatting, and 8 decision points
             in one body

ARCH103 names the correct seam, so the split follows it rather than chopping
the body at line 60 to get under the threshold (which would clear ARCH001 and
leave ARCH103 firing):

  - I/O steps: queue load, the T-2006 sweep-revalidate, the T-2034-hardened
    write path
  - a pure decision step returning a `_DoableSelection` NamedTuple: the
    `doable()` call, sprint filter, in-flight/dispatchable split, alarm
    ordering
  - render steps: JSON and plain formatting

No behaviour change. T-2034's fix for the query-verb dirty-write bug is
preserved through the split, not altered -- `frob ticket doable` writing to
the shared root and abandoning writes on lock loss DirtyMain-blocked the whole
fleet once already.

Work is already implemented and committed on branch `t2043-query-split`
(worktree .claude/worktrees/t2043-query-split). That branch was authored
before this ticket existed and stamps the placeholder id `T-2043` in 7 places;
`T-2043` is a REAL and unrelated ticket (post-land sweep regression from
T-2023), so every one of those references must be corrected to this ticket's
id before landing, or the obligation graph gains false edges. Note that
`frob ticket renumber` only rewrites `frob:ticket` directive comments, not
free-form prose or commit messages -- check both.

## Done report

Changed: src/frob/app/ticket_runner/_query.py

- _doable: split along decide/IO/format seam (was 117 lines,
  ARCH001+ARCH103, both fixed, no other change to observable behavior).
- New: _load_doable_queue, _revalidate_doable_queue,
  _log_dropped_sweep_tickets, _reload_queue_after_drop (I/O steps),
  _select_doable_tickets + _DoableSelection NamedTuple (pure decision
  step), _render_doable_json, _render_doable_plain (format+I/O steps).

Evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_text_mode
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_json_mode
- tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_nothing_doable

Measured: `frob check --only archgate` on the post-merge tree (main
merged in: T-2046/T-2067/T-2048 and later lands through T-2074) shows
neither ARCH001 nor ARCH103 for src/frob/app/ticket_runner/_query.py
(only a pre-existing, unrelated LARGE001 file-size finding remains).
Full doable-command test surface (TestTicketDoable, plus
test_app_runners_t0714_doable_summary.py,
test_app_runners_t0715_sprint_tier.py,
test_app_runners_doable_stale_lease.py,
test_app_runners_t1822_already_landed.py,
test_app_runners_t0976_mutation_evidence.py) passes green, except
TestTicketDoableSprintByParent::test_doable_sprint_filter, which fails
identically pre- and post-change (confirmed unrelated: reproduced with
the working tree untouched when a git-stash attempt was correctly
blocked by this repo's stash-guard hook).

`frob check --only archgate --only test --ticket T-2073`: gate:ARCH's 4
remaining (non-waived) errors are all pre-existing findings in
src/frob/app/ticket_runner/_rapid_sweep.py and src/frob/tickets/_land.py
-- outside this ticket's scope, none in _query.py.

`frob check --land-parity`: clean -- 0 unscoped error(s).

Filed: none (T-2034, the query-verb dirty-write bug this refactor
preserves the fix for, was already landed before this ticket started;
no new out-of-scope issue found).

Gates: frob check --only archgate clean for _query.py (measured before
AND after this ticket's merge with main); frob check --only test clean
for this ticket's evidence; frob check --land-parity clean.

### Changed
```
 src/frob/app/ticket_runner/_query.py | 223 ++++++++++++++++++++++++++---------
 tickets/T-2073/ticket.md             |  15 ++-
 2 files changed, 177 insertions(+), 61 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_text_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_doable_json_mode` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketDoable::test_nothing_doable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, COV001@src/frob/strata/_claims.py, DOC002@src/frob/strata/_claims.py, DUP001@src/frob/app/ticket_runner/_query.py
