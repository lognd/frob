## Done report

Root cause: T-3577's kept skip-stub used pytest's Class::method
collect-only separator in its frob:tests directives instead of this
graph's own single-:: dotted-qualname convention, so DOC007 flagged the
target-form and DRIFT002 flagged the resulting unresolved edge -- exactly
the 2 new (rule, file) identities / 24 findings the T-3577 post-land
sweep reported.

Fix: correct the separator (:: -> .) in all 6 frob:tests directives
above TestSigbreakFaultHandlerCrossPlatformSafety.

Evidence:
- uv run frob check --only docblocks (scoped read): zero DOC007/DRIFT002
  findings for tests/unit/test_conftest_sigbreak_faulthandler.py before/
  after comparison (before: 6 DOC007 + 6 DRIFT002 hits; after: 0, only
  pre-existing unrelated DOC007/DRIFT002 on src/frob/verify/_bisect.py
  remain)
- uv run pytest -p no:xdist tests/unit/test_conftest_sigbreak_faulthandler.py:
  6 skipped, 0 failed (unchanged from before -- these are fixed skips per
  T-3577's own contract)
- uv run ruff check tests/unit/test_conftest_sigbreak_faulthandler.py:
  clean

Filed: none

Gates: DOC007/DRIFT002 clean scoped to this file; frob:no-behavior-change
(directive-syntax-only fix, no test or production code behavior change)

### Changed
```
 tests/unit/test_conftest_sigbreak_faulthandler.py | 12 ++++++------
 tickets/T-3580/ticket.md                          | 13 ++++++++++++-
 2 files changed, 18 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_succeeds_when_faulthandler_register_is_absent_on_simulated_win32` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 28 error(s), 4112 warning(s), 891 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/macos-portability.md, DOC006@tickets/T-3587/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3580, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
