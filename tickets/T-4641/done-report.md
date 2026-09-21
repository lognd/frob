## Done report

# T-4641 done report rationale

Reproduced locally (single-worker, bounded timeout + faulthandler-style
traceback capture via pytest's own stack-on-timeout): `tests/gates_suite/
test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_
tick008_clean` genuinely hangs, past a 300s bound, on this repo's live
~712-ticket queue. NOT load-dependent alone (per-run CPU contention from
the fleet exists, but the traceback pinpoints an actual algorithmic hang,
not a wait on a lock or I/O):

  tickets_gate(root, queue)
    -> _tickets_gate_inner
      -> empty_code_diff_violations(queue)
        -> _changed_paths_from_done_report(t.body)
          -> _FENCE_RE.search(rest)   [src/frob/gates/_empty_diff_close.py:99]

`_FENCE_RE = re.compile(r"```\n(.*?)\n```", re.DOTALL)` (line 65) run
against a large real Done report body with no closing fence backtracks
badly (effectively O(n^2)) over this repo's tickets/ tree (77MB across
700+ tickets, some tickets carrying very large bodies).

Both real-repo smoke tests in this file
(`TestTick008UnknownLedgerFields.test_real_repo_ledger_is_tick008_clean`
and `TestTick007UndispatchedStale.test_real_repo_scan_runs_end_to_end_
without_crashing`) ran the FULL `tickets_gate(root, queue)` dispatch even
though each only ever asserts about ONE rule family (TICK008, TICK007
respectively) -- pulling in every other TICK/GATE family sharing the
queue, including the unrelated hang above, for no reason either test
cares about.

Fix (bounded fixture, not a raised timeout, per this ticket's own stated
fix direction): call each test's own rule-family checker function
DIRECTLY --
  - `_tick008_unknown_ledger_fields(queue)` (pure, in-memory, no
    filesystem/git access of its own) for the TICK008 test.
  - `_tick007_undispatched_stale(root, queue)` for the TICK007 test
    (same file, same root-cause hang via the shared full-dispatch path;
    fixed alongside since it is the identical shape in the identical
    ticket-scoped file and was directly why a whole-file pytest run of
    tests/gates_suite/test_tick.py still could not complete cleanly with
    only the TICK008 test fixed).

Both bound the smoke tests to exactly the rule family they verify,
matching every other rule-scoped unit test already in this file, and
sidestep the unrelated `_FENCE_RE` hang entirely rather than raising a
timeout to tolerate it.

Measured:
  - BEFORE: `test_real_repo_ledger_is_tick008_clean` alone, run in
    isolation with a 300s wall-clock bound, does not complete (traceback
    captured mid-`_FENCE_RE.search` at the timeout boundary) -- matches
    CI's own 120.1-120.3s STALL-DETECTED report.
  - AFTER: `test_real_repo_ledger_is_tick008_clean` alone completes in
    ~9.2s wall (real 0m9.246s). The full file
    (`tests/gates_suite/test_tick.py`, 40 tests) now completes cleanly
    end-to-end (exitstatus=0, collected=40, failed=0) in ~4m32s under
    this session's own fleet CPU contention -- no longer hanging, only
    bound by ordinary shared-host load, which this ticket's Description
    explicitly distinguishes from a genuine hang and does not ask this
    ticket to eliminate.

Filed: T-5160 (bug, scope src/frob/gates/_empty_diff_close.py)
for the underlying `_FENCE_RE` O(n^2) hang -- out of this ticket's
tests/gates_suite/test_tick.py-only declared scope to fix directly.

Acceptance: T-4641's own ledger entry carries no formal `acceptance:`
bullet list (prose-only Description/Investigate framing); evidence is
bound directly to the ticket (not to an indexed criterion) via
`frob ticket evidence T-4641 <node-id>` (no `--accepts`).

### Changed
```
 tests/gates_suite/test_tick.py     | 38 ++++++++++++++++++++++++++++++++------
 tickets/T-4641/ticket.md           |  5 ++++-
 tickets/T-5160/ticket.md | 30 ++++++++++++++++++++++++++++++
 3 files changed, 66 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_tick.py::TestTick007UndispatchedStale::test_real_repo_scan_runs_end_to_end_without_crashing` (pytest node id, verified passing when recorded)
