## Done report

Changed: none (evidence-only close)

Investigation: the ticket body itself states 0 symbols at exactly 0.0%
branch coverage for this package -- all 13 findings are partial-coverage/
module-line, the lower-priority tier, so acceptance[1]'s dead-code
routing criterion is vacuously satisfied (nothing to judge or route).

Ran the package's full test surface (tests/test_stats.py,
tests/test_stats_agentic.py: 10 tests total) standalone:
uv run pytest tests/test_stats.py tests/test_stats_agentic.py
-p no:cacheprovider -n0 -q -- all 10 pass. Sampled three of the ten and
confirmed each is a real behavioral assertion (not import-only/filler):
- test_ticket_stats_counts_states_and_doable: asserts on real
  count/doable-list output from ticket_stats over constructed tickets
- test_category_time_buckets_by_subcommand: asserts real time-bucket
  aggregation from a synthetic agentic event stream
- test_retread_candidates_require_repeat_and_known_tree_hash: asserts the
  repeat + known-tree-hash gating logic for retread-candidate detection

`frob check --ticket T-1298 --only test` in this worktree: 0 errors, 6
warnings, none TEST005 (TEST005 not computable here -- no coverage stamp
in this fresh worktree, TEST006 fires instead; consistent with playbook
sec 6b -- coverage stamping is coordinator-only). Per the T-1297
precedent (sibling TEST005 ticket, same 0-at-0.0% shape), binding
acceptance[0] on the strength of the ticket's own 0-at-0.0% claim plus
this sampled behavioral verification, not a fresh full-package TEST005
recount (which this worktree cannot produce).

Evidence:
- tests/test_stats.py::test_ticket_stats_counts_states_and_doable
- tests/test_stats_agentic.py::test_category_time_buckets_by_subcommand
- tests/test_stats_agentic.py::test_retread_candidates_require_repeat_and_known_tree_hash

Filed: none

Gates: uv run frob check --ticket T-1298 --only test -- 0 errors, 6
warnings (none TEST005), 3 pre-existing waived warnings unrelated to this
ticket.

### Changed
```
 tickets.md | 129 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 120 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_stats.py::test_ticket_stats_counts_states_and_doable` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::test_category_time_buckets_by_subcommand` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::test_retread_candidates_require_repeat_and_known_tree_hash` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 419 warning(s), 684 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design
