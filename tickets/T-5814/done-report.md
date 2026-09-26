## Done report

Between-lands re-exec: frob ticket land --drain now compares an mtime
fingerprint of frob's own package plus native extensions (strata_core,
frob_core) at the top of every drain_next call against the value
captured on this process's first call; on a change (a land during THIS
drain touched frob's own source), it logs and os.execv's the identical
argv so the next drain_next call runs under the newly-landed code.
Declared the new tickets_ledger::exec capability site in
design/frob.strata and bumped the SYS111 via-list ratchet in
docs/design/registry/capability-via-ratchet.lock.json (2 -> 3).

### Changed
```
 design/frob.strata                                 |   7 +-
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 docs/modules/tickets-landing.md                    |  22 +++++
 src/frob/tickets/_land_queue.py                    | 102 ++++++++++++++++++++-
 tests/unit/test_land_queue.py                      |  82 +++++++++++++++++
 tickets/T-5814/ticket.md                           |   5 +
 6 files changed, 219 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_land_queue.py::TestReexecIfSourceChanged::test_reexec_if_source_changed_noop_first_call` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestReexecIfSourceChanged::test_reexec_if_source_changed_noop_when_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestReexecIfSourceChanged::test_reexec_if_source_changed_execs_on_change` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestReexecIfSourceChanged::test_drain_next_calls_reexec_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
