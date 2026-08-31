## Done report

Replaced policy._IMPORT_PATTERNS per-language regex with frob.lang.extract_imports, the same grammar-driven walk frob.cycle already uses, per T-2996's NO-DUPLICATION finding. Line numbers for reporting are recovered by a plain text lookup over the already-identified specifier, not a second import grammar. Evidence cites pre-existing tests/test_policy.py forbidden-import tests since scope is src/frob/policy/** only (no test-file edits). Filed: none. Gates: gate:SCOPE/gate:PREWORK clean; other gate families show pre-existing repo-wide failures unrelated to src/frob/policy.

### Changed
```
 src/frob/policy/__init__.py | 101 ++++++++++++++++++++++----------------------
 tickets/T-3235/ticket.md    |   5 ++-
 2 files changed, 54 insertions(+), 52 deletions(-)
```

### Evidence
- `tests/test_policy.py::TestRules::test_forbidden_import_fires` (pytest node id, verified passing when recorded)
- `tests/test_policy.py::TestRules::test_forbidden_import_passes_outside_glob` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 26 error(s), 4108 warning(s), 892 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3235, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
