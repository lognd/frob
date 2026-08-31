## Done report

Added test_ack_prefixed_first_attempt_is_allowed_through (must-stay-quiet) and test_unacked_first_attempt_is_still_blocked (must-fire) to tests/test_hook_frob_suggest.py, matching T-3071's own acceptance criteria. Verified the must-stay-quiet fixture genuinely fails against the pre-T-3071 hook (git show 1aafb6b96~1:.claude/hooks/frob-suggest.py run directly against the same payload denies even with the ack), confirming this is a real regression pin, not a vacuous test. Full tests/test_hook_frob_suggest.py suite (49 tests) passes.

### Changed
```
 tests/test_hook_frob_suggest.py | 34 ++++++++++++++++++++++++++++++++++
 tickets/T-3601/ticket.md        |  5 ++++-
 2 files changed, 38 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::test_ack_prefixed_first_attempt_is_allowed_through` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_unacked_first_attempt_is_still_blocked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 26 error(s), 4116 warning(s), 893 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/test_check_runner.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
