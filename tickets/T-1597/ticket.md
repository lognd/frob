---
id: T-1597
title: 'Language support expansion: C#, Java, CUDA, Zig, Bash and the top 20-50 languages'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- src/frob/lang/**
- docs/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Umbrella for expanding frob's language support from its current set to the most widely used languages, and for hardening the cross-language machinery that expansion depends on.

Two goals, and the SECOND is the real one:

1. Coverage: named explicitly by the user -- C#, Java, CUDA, Zig, and Bash/Shell -- plus the rest of the top 20-50 languages, chosen from evidence rather than intuition (see the research child).

2. Stress-testing the machinery. Every language added is an independent probe of whether frob's abstractions are genuinely language-agnostic or quietly Python-shaped. Each new adapter that needs a special case in shared code is a design bug in the shared layer, not a quirk of the language. Expansion is how those get found. Treat a required special case as a finding to ticket, not a detail to absorb.

Sequencing: the research/ranking child and the adapter-contract child come FIRST. Adding languages one at a time against an unspecified contract is how the current per-language drift happened; the contract must be explicit and statically enforced before the batch work starts.

Non-negotiable for every language added: directive parsing (the frob comment DSL) must work in that language's comment syntax, symbol extraction must produce stable node ids, and the language must participate in the obligation graph (doc edges, test edges, waivers) exactly like Python does. A language that can only be parsed but cannot carry obligations is not supported, it is merely tokenized.