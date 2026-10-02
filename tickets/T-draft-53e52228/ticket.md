---
id: T-draft-53e52228
title: 'gob-log: tracing setup, FROB_LOG, redaction'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0003
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
- crates/gob-log/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given FROB_LOG=gob_git=debug, when init runs, then only gob_git debug events
    are emitted
  evidence: []
- text: Given a transcript containing a GitHub token and an AWS key, when redacted,
    then both are masked and the rest is unchanged
  evidence: []
threat: null
component: gob-log
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-log per architecture.md section 5 and D37/M24. Provide init(product, verbosity, json: bool) building a tracing-subscriber with EnvFilter from FROB_LOG (documented as the one diagnostic env var), human or JSON layer to stderr, span timing for commands; a redact(text) function that masks common secret shapes (bearer tokens, AWS keys, GitHub tokens ghp_/github_pat_, URLs with userinfo, KEY=VALUE where KEY matches *TOKEN*|*SECRET*|*PASSWORD*) for use by evidence capture and telemetry; a test-only subscriber capture helper. Rustdoc notes that products never println outside renderers.