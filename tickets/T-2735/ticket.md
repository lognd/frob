---
id: T-2735
title: Document T-2721's git-tracked/mirrored waive-audit watermark in docs/modules/app.md
state: done
kind: docs
origin: human
created: '2026-08-20'
priority: medium
blocked_by:
- T-2694
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/app.md
- src/frob/gates/_waive_audit_watermark.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive_audit_watermark.py
  reason: closing T-2735 requires re-pointing the AFFECT001 waiver that cites it as
    a live tracker (registry LiveTrackerCited refusal)
  actor: logan
  at: '2026-08-20'
evidence:
- cmd:python3 -c "import sys,pathlib;t=pathlib.Path('docs/modules/app.md').read_text();ok='waive-audit-watermark.json'
  in t and 'GIT-TRACKED' in t.upper();print('watermark section documents git-tracked
  location:', ok);sys.exit(0 if ok else 1)" exit=0 sha256=3ce2ada25ec3
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2721 changed `frob.gates._waive_audit_watermark.save_watermark` to commit
the watermark file (now git-tracked at the repo root, not `.frob/`) and
mirror it onto the primary checkout from a worktree.
`docs/modules/app.md#waive-audit-t-2467` (the section `frob:doc` targets
for this module) was NOT updated in T-2721's own change:
`docs/modules/app.md` was held by a live cross-worktree lease (T-2694) for
T-2721's entire duration, so T-2721 could not touch it and waived
AFFECT001 on `save_watermark` citing this ticket.

Update that section to describe: the watermark is now committed in git
(not gitignored per-checkout scratch state), the file lives at the repo
root (`waive-audit-watermark.json`, `.gitignore`-negated like
`rapid-debt.jsonl`), and `save_watermark` mirrors a worktree's write onto
the primary checkout immediately (same shape as T-2563's ledger mirror)
so the fleet sees audit progress without waiting for a land.