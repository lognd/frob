---
id: T-3992
title: 'CI001: CI/local gate parity and min_frob_version cross-check'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/repo_meta.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given this repo's own CI gates-fast workflow, land --dry-run, and a real land,
    when this ticket's first step runs, then it reports whether the three surfaces
    provably check the same rule set
  evidence: []
- text: given a configured test-runner path referenced by no CI workflow, when the
    new rule runs, then CI001 flags it
  evidence: []
- text: given min_frob_version diverging from the version CI's own workflow pins,
    when the new rule runs, then it is flagged
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-204 (T-3984 item 9). VERIFIED: git grep confirms min_frob_version exists as a config concept (src/frob/repo_meta.py, src/frob/doctor.py) but nothing cross-checks it against the actual version CI pins, and no existing rule checks that every configured test-runner path is referenced by some CI workflow.

FINDING THIS WOULD HAVE CAUGHT: CI/local gate parity drift -- a configured test runner whose paths no GitHub Actions workflow (or equivalent CI config) actually references, so CI silently runs a narrower check set than local `frob check`/`frob test` does; and min_frob_version declared in repo config diverging from the frob version CI's own workflow pins, so CI could be validating against a different frob than the one the repo claims to require.

THIS ONE IS DIRECTLY OURS TOO, per T-3984's own framing: we have an open question about whether CI gates-fast, `frob ticket land --dry-run`, and a real land run the same checks, with no documented relationship. Scope this ticket's first step as answering that for frob's OWN CI (are all three surfaces provably checking the same rule set), before generalizing to a consumer-facing CI001 rule.
