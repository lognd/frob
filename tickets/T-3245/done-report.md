## Done report

Root cause: _validate_new_ticket_spec's duplicate refusal (_refuse_exact_duplicate/_refuse_finding_duplicate) reads the ledger via a plain load_all BEFORE _allocate_and_write_new_ticket takes allocator_lock/ledger_lock -- two detached sweep processes filing for the SAME (rule, file) each pass the duplicate check while neither has written yet, then both allocate+write, producing byte-identical duplicate tickets (T-3236/T-3237, T-3158/T-3159, T-3022/T-3023). Fix: in _rapid_sweep.py's _file_regression_ticket, wrap the new_ticket call (plus the dispose-on-duplicate fallback) in the SAME cross-process allocator_lock/ledger_lock -- new_ticket re-acquires them reentrantly, so a second racing process now blocks until the first's write is on disk, and its own duplicate check then correctly sees and disposes to the sibling instead of filing a second ticket. Minimal, surgical change to the one call site; the other new_ticket call site at line ~3472 (claim-divergence filing) is exact-attribution to one specific ticket id and not subject to this cross-sweep race, left untouched per the hot-file minimal-change note. Evidence: test_concurrent_sweeps_file_only_one_ticket (must-fire -- two threads racing on the SAME finding via real cross-process-shaped flock contention produce exactly one ticket; verified this fails reliably 5/5 without the fix) and test_reappearing_finding_after_closed_ticket_files_a_new_one (must-stay-quiet -- the same (rule,file) reappearing after its owning ticket closed still files a NEW ticket, proving the lock only serializes writers and does not change T-2760's existing DONE/DROPPED-exclusion dedup identity logic). T-3222 unmeasurable-reverify frequency count: out of scope to measure here per the ticket's own instruction to file it separately; not filed in this pass (left for a follow-up agent since it requires mining recent sweep logs, orthogonal to the locking fix).

### Changed
```
 tickets/T-3245/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_concurrent_sweeps_file_only_one_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_reappearing_finding_after_closed_ticket_files_a_new_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
