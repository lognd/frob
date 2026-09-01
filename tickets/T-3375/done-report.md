## Done report

Root cause: tests/test_hook_frob_suggest.py's _run_edit_hook merged the runner's full os.environ into each spawned frob-suggest.py Edit-hook invocation, so an ambient FROB_SUGGEST_ACK=1 exported at shell level (e.g. an agent wrapping a command in 'FROB_SUGGEST_ACK=1 bash -c ...' for a timeout) leaked into pytest's own subprocess env and silently bypassed TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it's ack-gated assertions. Fix (option b from the ticket, the more durable one): both _run_hook and _run_edit_hook now start from a base os.environ snapshot with FROB_SUGGEST_ACK stripped, layering only each call's own explicit env override on top -- a test controls its own acked/unacked case regardless of the runner shell's exports. Reproduced the exact failure by checking out the pre-fix test file and running 'FROB_SUGGEST_ACK=1 uv run pytest tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it' (AssertionError: assert None is not None, matching the ticket's own repro exactly), then confirmed the fixed file passes both with and without the ambient export. Full 49-test suite passes both ways. Note for BUG002: the standard parent-commit repro check runs without FROB_SUGGEST_ACK exported, so it will see this test PASS at parent too (the defect only manifests when the invoking shell ambiently exports the var, which the repro checker does not do) -- see frob:waive BUG002 with this same explanation.

### Changed
```
 tests/test_hook_frob_suggest.py | 33 +++++++++++++++++++++++++++++----
 tickets/T-3375/ticket.md        |  4 +++-
 2 files changed, 32 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 27 error(s), 4115 warning(s), 893 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/test_check_runner.py, COV003@tests/test_config_frob_toml_milestone.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3375, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json
