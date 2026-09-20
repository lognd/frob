---
id: T-4459
title: Worktree test runs import frob from the ROOT src (editable .pth), measuring
  main instead of the branch
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/agent_runner.py
- src/frob/app/ticket_runner/_work*.py
- src/frob/doctor.py
- tests/test_worktree_pythonpath*.py
- docs/modules/agent*.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: pre-land unscoped sweep found 6 SELFAUDIT001 (SYS100) findings attributable
    to T-4459's touched files (cli::env.read at agent_runner.py, testsuite::exec+fs.write
    at test_worktree_pythonpath.py); not waivable in-file (symref binds to design-graph
    node names), must be declared in design/frob.strata plus the matching capability-via-ratchet.lock.json
    ceiling bumps, same recipe T-4455/T-4443 used
  actor: logan
  at: '2026-09-13'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: pre-land unscoped sweep found 6 SELFAUDIT001 (SYS100) findings attributable
    to T-4459's touched files (cli::env.read at agent_runner.py, testsuite::exec+fs.write
    at test_worktree_pythonpath.py); not waivable in-file (symref binds to design-graph
    node names), must be declared in design/frob.strata plus the matching capability-via-ratchet.lock.json
    ceiling bumps, same recipe T-4455/T-4443 used
  actor: logan
  at: '2026-09-13'
body_changes:
- mode: append
  reason: 'BUG002 confirmatory-only waiver: T-2025 squash-lands-repro-with-fix limitation,
    real before/after measured manually'
  actor: logan
  at: '2026-09-13'
  old_length: 1240
  new_length: 2835
evidence:
- tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath::test_env_output_names_worktree_src_on_pythonpath
- tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath::test_documented_entry_point_makes_worktree_code_importable
- tests/test_worktree_pythonpath.py::TestImportSourceStatus::test_matching_worktree_reports_clean
- tests/test_worktree_pythonpath.py::TestImportSourceStatus::test_mismatched_worktree_reports_loudly
- tests/test_worktree_pythonpath.py::TestImportSourceStatus::test_no_worktree_src_never_mismatches
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_doctor.py::TestImportSourceStatus::test_no_worktree_src_never_mismatches
  new_node: ''
  reason: moved into tests/test_worktree_pythonpath.py to stay within T-4459's declared
    scope (SCOPE001)
  actor: logan
  at: '2026-09-13'
- old_node: tests/unit/test_doctor.py::TestImportSourceStatus::test_mismatched_worktree_reports_loudly
  new_node: ''
  reason: stale, file outside T-4459 declared scope; superseded by tests/test_worktree_pythonpath.py::TestImportSourceStatus
  actor: logan
  at: '2026-09-13'
- old_node: tests/unit/test_doctor.py::TestImportSourceStatus::test_matching_worktree_reports_clean
  new_node: ''
  reason: 'stale id: the test lives in tests/test_worktree_pythonpath.py (already
    bound); the land refused because this id does not resolve post-merge'
  actor: logan
  at: '2026-09-13'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-13 by the T-4449 rebase agent: running the root checkout's interpreter (`/home/logan/projects/frob/.venv/bin/python -m pytest ...`) with a worktree as cwd imports `frob` from the ROOT src/ because the editable install's .pth points at /home/logan/projects/frob/src, not at the worktree's src/. A worktree test run therefore exercises main's code, not the branch under test, unless PYTHONPATH="$(pwd)/src" is set. The alternative agents use, `uv run` inside the worktree, builds a stray per-worktree .venv (seen today: a Python 3.11 venv in t-4445 whose `frob ticket body` sat in D-state for 50+ minutes). Both shapes silently mis-measure. ACCEPTANCE: (1) `frob ticket work`/`frob agent env` (whatever provisions or enters a worktree) exports PYTHONPATH=<worktree>/src (or installs the worktree's src editable into a shared venv) so the checked-out branch is what imports; (2) `frob doctor` in a worktree reports which src/ `import frob` resolves to and fails loudly when it is another checkout's; (3) a test that creates a worktree, runs python -c "import frob; print(frob.__file__)" through the documented entry point, and asserts the worktree path; (4) docs/modules (agent/worktree docs) state the rule. Sprint v0.532.0.




frob:waive BUG002 reason="check-repro cannot produce a real verdict for these node ids: T-2025's squash-lands-the-repro-test-with-its-fix limitation applies here too -- the repro tests and the PYTHONPATH-export fix were added in the same worktree commit, so no ancestor commit contains the tests without the fix (TEST_ABSENT_AT_PARENT at the merge-base). Confirmatory-only by construction, not by omission. The real fail-before/pass-after was measured manually in this worktree: BEFORE the agent_runner.py change, \`cd <worktree> && env -u PYTHONPATH uv run frob agent env .\` printed only FROB_WORKTREE/FROB_AGENT/PYTEST_XDIST_AUTO_NUM_WORKERS -- no PYTHONPATH line -- and a subprocess python -c \"import frob; print(frob.__file__)\" run with PYTHONPATH unset from inside the worktree resolved to /home/logan/projects/frob/src/frob/__init__.py (the ROOT checkout), not the worktree's own src/. AFTER the fix, the same \`uv run frob agent env .\` invocation additionally printed export PYTHONPATH=<worktree>/src, and evaluating that export before the same import check resolved frob.__file__ to <worktree>/src/frob/__init__.py. Symmetrically for doctor.py's _import_source_status: before this ticket the function/ImportSourceStatus did not exist at all; after, calling it with a root whose own src/frob/__init__.py differs from the currently-imported module's file returns mismatched=True (measured directly against /home/logan/projects/frob as the mismatched root while running from the t-4459 worktree's own src/), and mismatched=False when root IS the worktree the import resolved from."

## Reopen log
- 2026-09-13: the refused land (18:57 UTC, PreLandUnscopedSweepFailed) wrote state=done to main before unwinding; no code landed (git log main --grep 'land T-4459' is empty); reopening so the corrected worktree can land