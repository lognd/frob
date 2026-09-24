---
id: T-draft-a684db8f
title: 'land CAS publish: ledger-only sibling commits are not absorbed by the T-4572
  fast path'
state: queued
kind: bug
origin: human
created: '2026-09-24'
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
worktree: null
branch: null
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
Measured 2026-09-24: three lands (T-5324, T-5326, T-5474) were refused with "dev moved away while this land was composing" and each drift was ONE or TWO ledger-only sibling commits (chore(tickets): points T-5467; mirror scope T-5351; points T-5470), i.e. exactly the tickets/**-only advance T-4572's ledger-only CAS-retry fast path exists to absorb. Under a seven-agent fleet such commits arrive every few minutes, so the refusal now costs a full drain slot (10-25 minutes) several times per hour.

Fix: measure why the fast path did not absorb these (the log shows no ledger_only= line or attempt count near the refusal), make its attempt bound proportional to drift rate (or unbounded with backoff for pure-ledger advances), and log each attempt with the sibling commit list. Positive control: a test that advances dev with a tickets/**-only commit between compose and publish must land without a refusal.
