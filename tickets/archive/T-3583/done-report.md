## Done report

Root cause: docs/design/macos-portability.md's Bucket C closure note
names src/frob/tickets/_land_finish_guard.py to explain it never existed
as a separate module -- a backticked path that DOC006 correctly reads as
a live file-path pointer since it is shaped like a tracked-file path.

Fix: add a same-line `<!-- frob:waive DOC006 reason="..." -->` HTML
comment directly above the pointer (the sanctioned escape DOC006's own
message names), matching the established idiom.

Evidence:
- uv run frob check --only docblocks (scoped read): zero DOC006 findings
  for docs/design/macos-portability.md before/after comparison
- uv run pytest -p no:xdist tests/test_docptr_gate.py::TestDoc006FilePath:
  4 passed (waiver mechanism itself unaffected)
- uv run pytest -p no:xdist tests/test_docptr_gate.py::
  TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_
  live_repo: still reports one DOC006 finding, but it is
  tickets/T-3587/ticket.md:43 ('src/tests/test_gates.py' is not a
  tracked file) -- unrelated pre-existing drift from another ticket, not
  touched by this change; confirms this ticket's own target is clean

Filed: none

Gates: DOC006 clean scoped to docs/design/macos-portability.md;
frob:no-behavior-change (doc-only waiver addition)

### Changed
```
 docs/design/macos-portability.md |  1 +
 tickets/T-3583/ticket.md         | 13 ++++++++++++-
 2 files changed, 13 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006FilePath::test_missing_path_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 4107 warning(s), 891 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@tickets/T-3587/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3583, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
