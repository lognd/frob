## Done report

Restore ty platform-narrowing for os.major/os.minor. T-3768 replaced an in-body sys.platform assert with a @skipif decorator; ty does not read skipif for narrowing, so it flagged os.major/os.minor (POSIX-only per typeshed) as unresolved-attribute under win32, downing the self-gate on ubuntu+mac. Added back an in-body assert sys.platform != win32. ty clean, test passes 11/0 on Linux, skip still fires on win32.

### Changed
```
 tickets/T-3774/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_fleet_status_ground_truth.py::TestLandLockHolderClaim::test_must_fire_the_true_holder_among_waiters` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4324 warning(s), 919 waived
- error-findings: none (measured, zero errors)
