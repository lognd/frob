---
id: T-4458
title: 'SEC110 on tests/helpers/bash.py: ProgramFiles env read in the Git Bash resolver
  needs the repo''s non-secret disposition'
state: queued
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/helpers/bash.py
- tests/unit/test_helpers_bash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Post-land sweep of T-4455 (commit c4751a25a) raised quarantine with SEC110 (env-secret-read, error severity, promote-at-zero per T-0973) on tests/helpers/bash.py: the new Git Bash resolver reads os.environ["ProgramFiles"] / ProgramFiles(x86) to probe Git for Windows install locations. Those variables are install paths, not secrets, but SEC110 is lexical over environment reads and has a zero-tolerance posture; every other named site in the repo carries an explicit disposition. Fix: either (a) route the lookup through the repo's existing non-secret env accessor if one exists (git grep -n "SEC110" src tests to see how sibling sites are dispositioned -- reuse the same mechanism, NO new pattern), or (b) attach a `frob:waive SEC110 reason="ProgramFiles/ProgramFiles(x86) are Windows install-root paths, not credentials; read only to locate git-bash.exe for tests"` directive at the exact anchor SEC110 names. ACCEPTANCE: (1) `frob check --only sec` on the tree reports 0 SEC110 errors; (2) the next ubuntu/macOS self-gate run shows 0 SEC110; (3) the quarantine finding SEC110:tests/helpers/bash.py is disposed to this ticket. Sprint v0.531.0 (CI green blocker introduced by T-4455).
