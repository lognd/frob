---
id: T-5267
title: 'wire frob.doctor tool registry into frob check/frob ticket land: loud UNMEASURED
  block, non-zero exit, --allow-missing-tool'
state: in-progress
kind: feature
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/*.py
- src/frob/gates/__init__.py
- src/frob/vet/_scan.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: TOOL001-003 rule ids must be registered in _KNOWN_GATE_RULES so the new
    gate is waivable/known
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5267
branch: t-5267
---
T-5139's tool registry (frob.doctor._RELEVANT_TOOLS/relevant_tool_findings, cargo-audit->VET005) and _osv.py's Result-typed OsvQueryError.UnparseableResponse landed, but src/frob/check/*.py (T-4692's live lease) and src/frob/gates/__init__.py (T-5135's live lease) could not be touched at ticket time. Remaining DESIGN items from T-5139: (3) a relevant-and-missing/failed tool makes every rule it serves UNMEASURED and the run exit non-zero, new rules TOOL001/TOOL002/TOOL003, override --allow-missing-tool NAME --reason; (4) frob check/frob vet/frob test/frob ticket land end with a loud UNMEASURED block (rule family -> tool -> failure kind -> remedy), --json carries unmeasured[], land refuses when non-empty for a relevant tool (same override); (5) a DUP or ARCH finding on a new bare shutil.which outside the registry. Acceptance [1],[3],[4],[5] of T-5139 (UNBOUND at T-5139 close) map onto this ticket.