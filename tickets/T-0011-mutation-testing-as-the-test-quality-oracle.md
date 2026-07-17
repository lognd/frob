---
id: T-0011
title: Mutation testing as the test-quality oracle
state: queued
kind: feature
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/gates/**,src/frob/testing/**
evidence: []
attachments: []
---
Add mutation testing (mutmut or equivalent) as the honest test-quality oracle; TEST-family gains a mutation-score floor. Counts and coverage floors are gameable proxies (assert-free tests pass them) -- this is the real defense. Deferred post-0.1.0.