## Done report

Ran test_unpinned_polyglot_runs_python_stage 10x locally (uv run pytest
-p no:xdist): never failed. Treating as CI-transient per the ticket's
own instruction, and applying the T-3578 pattern (name the real
failure detail) instead of a code fix: on json.JSONDecodeError, raise
an AssertionError carrying r.returncode/r.stdout/r.stderr so the next
occurrence names the actual cause instead of a bare "line 1 column 1".

Evidence:
- uv run pytest -p no:xdist tests/system/test_cli_check.py::
  TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage -q x10:
  0 failures
- uv run pytest -p no:xdist tests/system/test_cli_check.py::
  TestCheckPolyglot: 2 passed
- uv run ruff check tests/system/test_cli_check.py: clean

Filed: none

Gates: frob:no-behavior-change (failure-path message only)

### Changed
```
 tests/system/test_cli_check.py | 15 ++++++++++++++-
 tickets/T-3584/ticket.md       | 13 ++++++++++++-
 2 files changed, 26 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 26 error(s), 4109 warning(s), 891 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3584, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
