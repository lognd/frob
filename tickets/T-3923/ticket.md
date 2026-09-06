---
id: T-3923
title: extend frob vet to require SHA-pinned uses in GitHub Actions workflows
state: queued
kind: security
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/**
  reason: narrow to the vet package where the new workflow-uses rule belongs
  actor: logan
  at: '2026-09-05'
- op: add
  glob: src/frob/vet/**
  reason: narrow to the vet package where the new workflow-uses rule belongs
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Part B of T-3922: add a frob vet rule that flags any non-first-party
uses: reference in .github/workflows/*.yml that is not a 40-hex SHA (a
tag or branch ref = flagged).

T-3922 (Part A, landed) pinned all eight of frob's own third-party
actions to 40-hex SHAs, including first-party actions/* -- the stated
line there was "cheap and total, no exemption for first-party." Decide
whether frob vet enforces that same breadth or instead allows an
allowlist for first-party actions/* (GitHub's own org, lower but
nonzero risk) -- state the decision, do not default it.

MUST-FIRE fixture: a workflow with a tag-pinned non-first-party uses:
is flagged.
MUST-STAY-QUIET: a 40-hex SHA pin passes; a first-party action passes
if an allowlist is the chosen line.

Filed separately per T-3922's explicit instruction: Part B is a
separate land and must not hold Part A behind it.
