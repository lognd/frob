---
id: T-1601
title: 'Language support: Java'
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
Add Java to frob's supported languages, meeting the full adapter contract defined by the contract ticket -- not merely parsing.

Language-specific considerations to resolve explicitly: Package-private as the default visibility (no keyword) is the trap -- absence of a modifier is meaningful. Inner and anonymous classes, interfaces with default methods, annotations, and Javadoc as the doc-comment form. One public class per file is a convention frob can exploit for node ids.

Required for done:
- Symbol extraction producing stable node ids across reparses.
- Directive DSL parsing in this language's comment syntax, including wrapped/continued directives.
- Participation in the obligation graph: doc edges, test edges, and waivers behave as they do for Python.
- The parameterized adapter conformance suite passes with no skips, and any capability declared unsupported is declared explicitly rather than silently absent.
- A fixture repo (or fixture files) exercising the awkward cases named above.

If shared code needs a special case to accommodate this language, STOP and file that as a separate finding against the shared layer. A special case is evidence the abstraction is wrong, and absorbing it quietly is how the shared layer becomes Python-shaped by accretion.