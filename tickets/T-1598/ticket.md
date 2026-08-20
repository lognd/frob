---
id: T-1598
title: 'Language expansion: research and rank the target set, define per-language
  semantics'
state: queued
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: T-1597
tier: story
sprint: post-1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'coordinator decision: defer live multi-source web research to a dedicated
    pass, do not attempt from memory'
  actor: logan
  at: '2026-08-19'
  old_length: 1680
  new_length: 2530
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Produce the evidence base for the expansion, so the language set is defensible rather than a guess.

Deliverables:

1. A ranked target list of 20-50 languages, each row citing its sources. Use several independent rankings and say where they disagree: TIOBE, RedMonk, GitHub Octoverse, Stack Overflow Developer Survey, and IEEE Spectrum are the usual five; weight by what a frob user is plausibly running in a repo that needs obligation tracking, not by raw popularity alone (COBOL and MATLAB rank higher than their relevance here; CUDA and Zig rank lower than theirs).

2. Per language: tree-sitter grammar availability and maturity (this repo already depends on tree-sitter-language-pack -- record which targets it already ships, which need a separate crate, and which have no usable grammar at all, since that last group changes the cost dramatically).

3. Per language: comment syntax for the directive DSL, including the awkward cases -- languages with no line comment, languages where the block comment cannot nest, and languages with significant indentation that constrains where a directive may sit.

4. Per language: what "public symbol" even means. This is where the abstraction will strain. Header/implementation splits in C/C++, Java package-private, Rust pub(crate), Go capitalization, C# internal, and shell functions with no visibility concept at all do not share one definition. The research must state the intended per-language rule BEFORE any adapter is written.

5. A recommended batch order, with the user's five named languages (C#, Java, CUDA, Zig, Bash) first.

Output goes in docs/ as a durable reference, not just a ticket comment -- later batches read it.

Deliberately NOT attempted this round: this ticket requires live
multi-source web research (TIOBE, RedMonk, GitHub Octoverse, Stack
Overflow Developer Survey, IEEE Spectrum), each row citing real,
current sourcing per the ticket's own deliverable 1. That is a
distinct, larger unit of work than a normal drain-queue slot, and its
output (rankings, availability tables) would date quickly regardless.

It must NOT be attempted from model memory -- fabricated ranking
numbers or citations that merely look plausible would be worse than no
document at all, and would be effectively undetectable later without
re-doing the research from scratch. An implementer picking this up
should budget it as a dedicated research pass with real web access,
not fold it into a normal ticket dispatch.

Left queued and untouched otherwise; no partial content added.
