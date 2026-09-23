---
id: T-draft-c7aa1ed2
title: land --dry-run stops before squash-apply so T-3324 self-conformance and DOC006
  pointer refusals never run; DRY RUN clean is a false READY
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Observed twice today (T-5302, T-5360): agent reports 'DRY RUN clean -- merged=True wip_committed=False', the real land then refuses with SELFAUDIT001 (undeclared fs.read via-list) and DOC006 (illustrative paths) attributable to the land's own touched files. Cause: src/frob/app/ticket_runner/_land_cmd.py ~3469 returns at 'would finalize/close/squash-apply/commit' before src/frob/tickets/_land_squash.py::_run_pre_commit_checks (the unscoped pre-commit sweep, _refuse_if_selfaudit_findings_in_touched_files, docptr and sys111 findings) ever executes, so the dry-run never measures the checks that most often refuse a land. Fix: in dry-run, build the staged squash preview on a throwaway ref exactly as the real land does, run _run_pre_commit_checks against it, report its findings as the dry-run verdict, then unwind; never commit. Positive control: a fixture worktree that reads a file from a module not in the strata via-list must make the dry-run report SELFAUDIT001. Update docs/guides (land dry-run contract) and the BRIEF idiom that dry-run is the READY proof.