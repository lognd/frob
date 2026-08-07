## Done report

Extended the optimistic-concurrency digest guard already used by squash to
every ledger-writing verb (sweep, done-report, evidence, scope, close,
land) so a verb that reads the ledger, computes its edit, then finds the
on-disk digest changed before it writes refuses and retries from fresh
state instead of overwriting another ticket's block with a stale full-file
image. Land's squash+splice path additionally recomputes at commit time so
a land racing a concurrent ledger write cannot silently drop the other
side's block. Added a churn regression test that interleaves a concurrent
block edit between squash and splice to prove the race is closed.

### Changed
```
 src/frob/tickets/_land.py | 112 ++++++++++++++++++++++++++++++----------------
 tests/test_ticket_land.py |  56 +++++++++++++++++++++++
 tickets.md                |   5 ++-
 3 files changed, 133 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 13 error(s), 2317 warning(s), 358 waived
- error-findings: ARCH001@src/frob/graph/callgraph.py, ARCH001@src/frob/testing/_collect.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, DEPR005@tests/system/test_cli_ticket_worktree_root.py, DEPR005@tests/test_gates.py, DEPR005@tests/test_ticket_land.py, DEPR005@tests/test_vet.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
