---
id: T-1604
title: 'Language support: Bash/Shell'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1599
parent: T-1597
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add Bash/Shell to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: The hardest of the five for the abstraction, and therefore the most valuable probe. There is no visibility concept, functions can be redefined, sourcing is dynamic, and much meaningful code is top-level statements rather than named symbols. Decide and document what a public symbol IS here (exported functions? every function? script entry points?) before implementing. Hash-only line comments, no block comments, so directive continuations matter.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.