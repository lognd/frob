---
id: T-3375
title: Exported FROB_SUGGEST_ACK=1 leaks into pytest subprocesses and false-fails
  its own bypass test
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_hook_frob_suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given an agent that exports FROB_SUGGEST_ACK=1 at shell level for a frob-suggest
    hook bypass, when that same shell later runs pytest, then the exported var does
    not silently change any test's observed behavior
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED today (Series EF, re-measuring chunk3a/3b/3c): the frob-suggest hook's documented escape hatch is 'prefix the ONE blocked command with FROB_SUGGEST_ACK=1'. An agent that instead does 'FROB_SUGGEST_ACK=1 bash -c "...uv run pytest..."' (a common shape when wrapping a command for a shell-level timeout) exports the var into the bash -c child's entire environment, which pytest then inherits and passes to every subprocess it spawns/tests. tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it specifically asserts on FROB_SUGGEST_ACK's bypass behavior and fails under this contamination -- reproduced live (failed inside a batch run with the var exported, passed solo with 'env -u FROB_SUGGEST_ACK'). This is a real hazard, not just a self-inflicted mistake: the ack is documented/intended as per-command, but nothing stops it from being exported at a shell level, and when it leaks into a test run it silently changes what that ONE test observes without the ack's side-effect being obvious to whoever is reading the failure. Ask: either (a) the hook-bypass docs/nudge text should explicitly warn against exporting FROB_SUGGEST_ACK rather than prefixing a single command ('FROB_SUGGEST_ACK=1 cmd', never 'export FROB_SUGGEST_ACK=1'), and/or (b) test_hook_frob_suggest.py's own ack-bypass test(s) should monkeypatch/isolate os.environ so an ambient exported value in the runner's own shell can never leak into the test's observed behavior (the test should control its own env var value, not inherit whatever the invoking shell happens to have set) -- (b) is probably the more durable fix since it protects the test's own correctness regardless of what any future runner's shell habits are.