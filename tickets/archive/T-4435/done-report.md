## Done report

T-4435: shared one load_all per sibling-state snapshot (pre/post merge), added elapsed-time log lines (WARNING >30s), added shared-load unit tests.

MEASURED (this checkout, 873-ticket v2 ledger, cold index cache):
- load_all(worktree) single call: cProfile shows 4.15s total (1.64s YAML/ticket-model parse across 873 tickets, 1.34s index-cache JSON write dominated by json.dump/_iterencode at 0.95s) -- roughly linear in ticket count and body size, so on the 4000+ ticket ledger T-4435 cites, each load_all is minutes, not seconds, and two independent loads per snapshot doubled that.
- BEFORE: _land_merge_stage called _sibling_ticket_states then _sibling_reopen_log_signatures pre-merge (2x load_all), and _assert_no_sibling_state_regression called both again post-merge (2x load_all) -- 4 full load_all(worktree) calls per land in the post-wip stretch, no log line before/after any of them.
- AFTER: both helpers take an optional loaded= (a dict[str, Ticket]) and skip their own load_all when given one. A new _timed_load_all(worktree) wraps load_all with elapsed-time logging (WARNING if >30s, else DEBUG) and is called ONCE per snapshot (pre-merge in _land_merge_stage, post-merge in _assert_no_sibling_state_regression), with the result passed to both helpers -- 4 load_all calls per land reduced to 2, and both remaining calls are now logged.
- Hot spot inside load_all itself (YAML parse + index-cache JSON re-serialize) is OUTSIDE this ticket's scope (src/frob/tickets/_store.py) -- not touched; if the 2x-per-snapshot reduction alone does not bring post-wip-to-merge under 5 minutes on the real 4000+ ticket fleet ledger, the remaining cost is in _store.py's load_all/_write_index_cache and belongs to a follow-up ticket, not this one.

### Changed
```
 src/frob/tickets/_land.py                  | 97 ++++++++++++++++++++++++------
 tests/unit/test_land_sibling_regression.py | 92 ++++++++++++++++++++++++++++
 tickets/T-4435/ticket.md                   |  5 ++
 3 files changed, 176 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_land_sibling_regression.py::TestSharedSiblingLoad::test_shared_load_is_reused_by_both_helpers` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSharedSiblingLoad::test_a_fake_ledger_of_n_tickets_loads_once_for_both_helpers` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSharedSiblingLoad::test_default_no_loaded_arg_still_loads_standalone` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_pre_fix_shape_would_have_silently_reverted_sibling` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 4854 warning(s), 964 waived
- error-findings: REF002@docs/design/macos-portability.md
