---
id: T-1572
title: 'frob coverage: add --base override, thread through make coverage-fast BASE='
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Refiled from worktree draft T-draft-a385ed9f (T-1526 follow-up; drafts cannot be cited by reports that must survive a land preview). make coverage-fast BASE=<ref> was honored by the old shell recipe but frob coverage currently hardcodes the touched-set base; add a --base flag and pass BASE through the Makefile wrapper.