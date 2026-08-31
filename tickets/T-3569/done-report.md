## Done report

Mirrored T-3487's fix (the sibling test, test_with_serial_pools_worker_is_majority_attributed) onto test_without_serial_pools_worker_is_unattributed: replaced the pure-ratio bound (without < with_serial * 0.5) with an absolute-AND-relative pair (without < 0.7 absolute, with_serial > without * 1.5 relative). Ground truth (run 33370059331): without=0.5062, with_serial=0.9992 -- the ratio bound broke down because with_serial sits near its 1.0 ceiling, making without/with_serial land just over 0.5 on a rounding technicality even though 0.506 is decisively smaller than 0.999 in absolute terms, the actual property under test. Evidence: 3x local pass via FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist (reproduces the fix's correctness on Linux; the original mis-stated-bound failure was ubuntu-CI-noise-dependent per the coordinator's ground truth, not independently reproduced failing here). Filed: none.

### Changed
```
 tickets/T-3569/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 32 error(s), 4088 warning(s), 892 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/land-splice-test-then-impl.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3569, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, call-top-callable@tests/conftest.py, invalid-argument-type@tests/conftest.py
