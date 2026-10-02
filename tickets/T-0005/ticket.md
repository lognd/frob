---
id: T-0005
title: 'gob-rules + gob-macros: Rule derive, inventory registry, Finding, Severity'
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0004
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob-v2-wt/t-0005
branch: t-0005
scope:
- crates/gob-rules/**
- crates/gob-macros/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:cargo nextest run --profile ci -p gob-rules -p gob-macros exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: 'Given a struct with #[derive(Rule)] and complete attributes, when the binary
    starts, then the registry lists it by id and slug with the doc comment as explanation'
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-rules -p gob-macros exit=0 sha256=e3b0c44298fc
- text: Given two rules declaring the same id, when the registry is built, then it
    fails naming both
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-rules -p gob-macros exit=0 sha256=e3b0c44298fc
- text: Given a reason string under the configured minimum or matching a banned pattern,
    when checked, then the reason checker rejects it with the pattern name
  evidence:
  - cmd:cargo nextest run --profile ci -p gob-rules -p gob-macros exit=0 sha256=e3b0c44298fc
threat: null
component: gob-rules
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-rules and crates/gob-macros per rules.md sections 1 to 2 and D3/D32. gob-rules: Severity (Error, Warn, Advisory, Unresolved per rules.md), Finding { rule: RuleId, severity, span: Option<Span>, message, fingerprint, fix: Option<Fix> }, fingerprint = blake3 of (rule id, symref or file, normalized message) per D37/M15 (never line numbers), RuleMeta { id: FAMILYNNN, slug alias, family, product namespace, summary, explanation (markdown), tier Universal|Lang, scope File|Repo, fix kind Manual|Deterministic|VerifyCommit|FixIt, version u32, since }, Rule trait, a global registry over the inventory crate with lookup by id or slug and a duplicate-id check at startup that panics with both declaring crates. Exception primitive data types only (kind accept|defer|hotfix|baseline, reason, ticket, until) with the reason-quality checker from exceptions.md section 5 as a pure function; no directive parsing here. gob-macros: proc-macro crate exporting #[derive(Rule)] with #[rule(id = ..., slug = ..., family = ..., severity = ..., tier = ..., scope = ..., fix = ..., version = ...)] that generates the RuleMeta, an inventory::submit, and pulls the explanation from the item's doc comment. Compile-fail tests with trybuild for missing id and bad severity. gob-rules re-exports the derive. Example rule in gob-rules tests. Keep gob-macros free of workspace deps other than syn/quote/proc-macro2/darling.