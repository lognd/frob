---
id: T-0026
title: 'Repo hygiene: remove v1 GitHub templates and release workflow, add .gitattributes'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: medium
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- .github/**
- .gitattributes
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a fresh clone, when a file is committed, then git prints no CRLF warning
  evidence: []
- text: Given .github, when read, then no template mentions Python, uv or pytest
  evidence: []
threat: null
component: workspace
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up from T-0003. Delete .github/workflows/release.yml (PyPI publish) and rewrite the issue and PR templates under .github for the Rust workspace (no uv run frob, no Python). Add .gitattributes with '* text=auto eol=lf' so commits stop printing CRLF warnings on this host, and normalize line endings in one commit. Also add Cargo.lock to [tickets] registry_files is already done; nothing else.