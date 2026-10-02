---
id: T-draft-dff8a953
title: 'gob-directives: Directive derive, frob: namespace parser, binding rules, PARSE
  and DSL rules'
state: queued
kind: feature
origin: agent
created: '2026-10-02'
priority: high
blocked_by:
- T-0013
- T-0005
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
worktree: null
branch: null
scope:
- crates/gob-directives/**
- crates/gob-macros/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a comment with frob:ticket followed by a fn two lines later, when scanned,
    then the directive binds to that fn
  evidence: []
- text: 'Given a frob: directive with an unknown verb, when scanned, then DSL001 fires
    with the span and a did-you-mean'
  evidence: []
- text: Given a 7-char ticket handle in a directive, when scanned, then DSL002 fires
    with the expansion fix
  evidence: []
threat: null
component: gob-directives
anchor: false
anchor_reason: null
land_commit: null
---
Implement crates/gob-directives and the Directive derive in gob-macros per code-model.md section 4 and D32. #[derive(Directive)] with #[directive(namespace = "frob", verb = "ticket")] and typed fields (positional, key=value, lists), generating the parser table, a docs entry and the JSON schema. Scanner over comments in Rust (via gob-languages) and markdown HTML comments, honoring the namespaces listed in the [directives] namespaces knob; unknown namespaces ignored, unknown verbs in an honored namespace -> DSL001. Binding rules from v1 carried unchanged: a directive binds to the symbol that starts within 2 lines after it, else the enclosing symbol, else the file; frob:tests canonical reorientation. Directives for milestone 1: frob:ticket <ulid>, frob:todo <ulid>, frob:doc <path#slug>, frob:tests <test id>, frob:invariant <name>, frob:accept and frob:defer (exception kinds with because=, ticket=, until=). Rules: PARSE001 malformed directive, DSL001 unknown verb, DSL002 abbreviated ticket id (D24: only full 26-char ULIDs persist). Output DirectiveRecord { namespace, verb, args, span, bound symref }. Tests via corpus files.