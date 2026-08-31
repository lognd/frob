## Done report

First-attempt path in _escalate now returns silently when FROB_SUGGEST_ACK=1 is set, instead of unconditionally denying. Both first-block message texts corrected to describe the ack working on the first attempt, not just repeats. Manually verified via direct hook stdin invocation: (1) FROB_SUGGEST_ACK=1 ruff check src/ passes silently on first encounter, (2) the same command without the ack still denies on first encounter with the corrected message. Existing 47-test suite in tests/test_hook_frob_suggest.py still passes unchanged. Filed T-3601 for the missing automated first-block/ack fixtures since T-3071's own scope is .claude/hooks/frob-suggest.py only, not the test file. Synced the materialized ~/.claude/hooks/frob-suggest.py copy; frob claude sync --check reports 9 file(s) in sync.

### Changed
```
 .claude/hooks/frob-suggest.py      | 25 ++++++++++++++++++++-----
 tickets/T-3071/ticket.md           |  6 +++++-
 tickets/T-3601/ticket.md | 29 +++++++++++++++++++++++++++++
 3 files changed, 54 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::test_ack_prefixed_third_attempt_is_allowed_through` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_fourth_attempt_needs_the_ack_again` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 24 error(s), 4119 warning(s), 890 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
