## Done report

Fixed the invalid-argument-type regression: fix_sys_interface_canonical_order(root, snapshot: GraphSnapshot) is called by these tests with None instead of a GraphSnapshot -- ty correctly flags this since the param is not Optional. Same class of defect as T-1894 (a caller passing a value that doesn't satisfy the callee's declared static type, discovered by a post-land sweep, not by any runtime failure). Rather than loosen the handler's signature to GraphSnapshot | None (the handler documents that snapshot is only there for fix-engine signature uniformity across handlers and is genuinely unused here), fixed the tests to construct and pass a real, minimal, unused GraphSnapshot(root='', symbols={}, edges=()) -- keeps the production signature honest for the one real caller (frob.gates._fix_engine.py's dispatch table, which does pass a real snapshot) and keeps the test's intent (order-only, snapshot-independent behavior) unchanged. Verified 'uv run frob check --ticket T-1896 --only ty': clean, 0 diagnostics (previously 3, all three call sites in this file). Ran both tests directly: 2 passed. Closed with --skip-mutation-evidence for the same reason as T-1894: the defect was a static-only type mismatch with no runtime-observable failure at the parent commit, so no fail-then-pass delta is possible against the parent commit; the bound tests are the same real regression coverage as before, now type-correct. Common shape across T-1894 and T-1896 (asked for by the coordinator): both are a caller passing a value whose runtime behavior was always fine but whose static type didn't match the callee's declared parameter type -- T-1894 was too-narrow invariant typing (dict vs Mapping) on a production call path, T-1896 was a caller passing None into a non-Optional parameter in test code. Neither was a real bug in the sense of producing wrong runtime behavior; both were the type checker catching a real but consequence-free mismatch introduced by a recent land, which is exactly the post-land sweep's job. No single shared root cause beyond 'agents landing new call sites without running ty locally first' -- suggest running frob check --only ty scoped to touched files as a standard closing step before ticket close, not just before land, to catch this class before the sweep does.

### Changed
```
 rapid-debt.jsonl                                    |  4 ++++
 src/frob/app/ticket_runner/_lifecycle.py            | 14 +++++++++++++-
 tests/test_tickets_scope_mutation.py                |  4 ++--
 .../gates/test_sys_interface_canonical_order.py     | 17 ++++++++++++++---
 tickets/T-1894/done-report.md                       | 21 +++++++++++++++++++++
 tickets/T-1894/ticket.md                            |  7 ++++++-
 tickets/T-1896/ticket.md                            |  5 ++++-
 7 files changed, 64 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
