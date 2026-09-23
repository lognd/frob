---
id: T-draft-98d6033e
title: Land-path collect failures are refused with returncode only; thread python_collection_failure_detail
  into land refusals
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
Observed 2026-09-23 on T-5334: the land dry-run's post-merge evidence re-verification ran pytest --collect-only, got returncode=2, and refused with 'evidence no longer resolves post-merge' / NotCloseable, but the only diagnostic available at any log level was returncode=2. frob.testing._collect captures the collector's stdout/stderr tail via _set_collection_failure_detail(), and python_collection_failure_detail() exists, but the land-path callers (the orphaned-evidence check and post-merge re-verify in the ticket land modules) never read it; only frob verify and gates/__init__.py do. The agent burned four dry-runs and an hour because the failure was invisible; the real cause (a post-merge collection error) was only inferable from the code path. Fix: thread python_collection_failure_detail() into every land-path refusal that stems from a collect failure, print the first 30 lines of the collector's stderr in the refusal message, and add a positive control: a fixture worktree with a deliberate ImportError in a test module must make the land refusal quote that ImportError. Silent-zero class: a collect that returns rc=2 with no text is indistinguishable from could-not-run.
