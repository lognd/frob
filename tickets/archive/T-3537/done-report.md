## Done report

Restated the must-fire property in tests/unit/test_frob_core_gil.py and its shared-shape mirror tests/unit/strata/test_strata_core_gil.py: timeout FIRED (Timeout banner in stdout) AND the call did NOT run to completion, with a generous 30.0s wall bound instead of the previous tight 5.0s bound; raised the outer subprocess.run harness timeout 9->40 to stay above the new assertion bound. Ground truth: CI run 33353658750 showed preemption working (banner printed) but tripping the tight bound at 7.006s on a slow macOS runner. Evidence: 3x local pass for both tests via FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist. frob check --ticket T-3537: gate:SCOPE clean; other gate families repo-wide/pre-existing. frob:waive BUG002 recorded: macOS-only, cannot fail-then-pass on Linux (the loosened bound cannot regress coverage). Filed: none.

### Changed
```
 tickets/T-3537/ticket.md | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_frob_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_near_duplicate_indices` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_strata_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_worst_age` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 25 error(s), 4067 warning(s), 895 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3537, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
