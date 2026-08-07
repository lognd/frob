## Done report

Root cause: finalize_draft (src/frob/tickets/__init__.py) computed its
candidate final id via _load_merged/_next_ticket_id OUTSIDE any lock,
then called renumber_one, which only acquired ledger_lock afterward, once
the id was already fixed. Two sibling lands each renumbering their own
residue draft against the same root could both read the same pre-write
snapshot and both compute the same final id -- the T-1086-vs-T-0684 field
incident (third occurrence 2026-07-28).

Fix: finalize_draft now holds ledger_lock(root) across the whole
read (_load_merged) -> compute (_next_ticket_id) -> write (renumber_one)
sequence. ledger_lock is reentrant per thread, so renumber_one's own
internal lock acquisition is a no-op re-entry, not a deadlock. A
concurrent finalizer blocked on the OS-level flock always recomputes its
id against the fresh post-write ledger the moment it acquires the lock,
never a stale pre-write snapshot -- mirrors the new_ticket/T-0458
single-writer allocation pattern and the T-1036 splice-guard lineage.

Regression test: TestFinalizeDraftAllocationRace.test_two_concurrent_
finalize_draft_calls_get_distinct_ids in
tests/test_tickets_ledger_concurrency.py -- two draft tickets released
via a threading.Barrier(2) so both finalize_draft calls genuinely
interleave against the same root; asserts both calls succeed, allocate
DISTINCT final ids, and both finalized blocks survive in the ledger.

Scope was extended from the ticket's original declaration
(src/frob/tickets/_land.py, _store.py, tests/test_ticket_land.py) to add
src/frob/tickets/__init__.py, tests/test_tickets_ledger_concurrency.py,
docs/modules/tickets.md, and frob.lock -- the actual race lives in
finalize_draft (__init__.py), not in _land.py/_store.py, and AFFECT001/
DRIFT002/SCOPE001 required the doc update and lock re-ack to land in the
same diff. Recorded via `frob ticket scope T-1090 --add ... --reason-file`.

Verification: frob check --ticket T-1090 clean across gates-fast,
gates-native, gates-security, lint, and static (0 errors in each).
frob test --base main: touched-set selection (4 python test outcomes)
passed, exit 0. git diff main --diff-filter=D --stat empty.

### Changed
```
 docs/modules/tickets.md                  |  15 ++
 frob.lock                                |  10 +
 src/frob/tickets/__init__.py             |  57 ++++--
 tests/test_tickets_ledger_concurrency.py |  71 +++++++
 tickets.md                               | 335 ++++++++++++++++++++++++++++++-
 5 files changed, 469 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_tickets_ledger_concurrency.py::TestFinalizeDraftAllocationRace::test_two_concurrent_finalize_draft_calls_get_distinct_ids` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 694 warning(s), 421 waived
- error-findings: REG003@docs/design/registry/supply-chain.yaml, TICK006@tickets.md
