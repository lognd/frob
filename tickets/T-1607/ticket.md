---
id: T-1607
title: 'Language expansion: remaining ranked languages, in research-recommended batches'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: low
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Implement the remaining ranked languages from the research ticket's target list, in the batch order it recommends, after the five named languages have proven the contract.

Split into further child tickets per batch rather than attempting all at once -- this ticket is the placeholder the research output turns into a concrete plan. Each batch must clear the parameterized adapter conformance suite before the next begins.

Expect the cost per language to FALL sharply after the first few if the contract is right, and to stay flat if it is wrong. A flat cost curve is the signal that the contract ticket did not actually succeed and should be revisited before continuing -- report it rather than grinding through.