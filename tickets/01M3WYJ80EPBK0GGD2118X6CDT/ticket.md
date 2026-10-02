+++
id = "01M3WYJ80EPBK0GGD2118X6CDT"
title = "gob-directives: Directive derive, frob: namespace parser, binding rules, PARSE and DSL rules"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0014"]
labels = ["milestone:2.0.0", "component:gob-directives"]
scope = ["crates/gob-directives/**", "crates/gob-macros/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ8059GN1VBGSA69X5BSZ"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80DWFZK0DPR4CBP0KHT"

[[acceptance]]
text = "Given a comment with frob:ticket followed by a fn two lines later, when scanned, then the directive binds to that fn"
bound = false

[[acceptance]]
text = "Given a frob: directive with an unknown verb, when scanned, then DSL001 fires with the span and a did-you-mean"
bound = false

[[acceptance]]
text = "Given a 7-char ticket handle in a directive, when scanned, then DSL002 fires with the expansion fix"
bound = false
+++

Implement crates/gob-directives and the Directive derive in gob-macros per code-model.md section 4 and D32. #[derive(Directive)] with #[directive(namespace = "frob", verb = "ticket")] and typed fields (positional, key=value, lists), generating the parser table, a docs entry and the JSON schema. Scanner over comments in Rust (via gob-languages) and markdown HTML comments, honoring the namespaces listed in the [directives] namespaces knob; unknown namespaces ignored, unknown verbs in an honored namespace -> DSL001. Binding rules from v1 carried unchanged: a directive binds to the symbol that starts within 2 lines after it, else the enclosing symbol, else the file; frob:tests canonical reorientation. Directives for milestone 1: frob:ticket <ulid>, frob:todo <ulid>, frob:doc <path#slug>, frob:tests <test id>, frob:invariant <name>, frob:accept and frob:defer (exception kinds with because=, ticket=, until=). Rules: PARSE001 malformed directive, DSL001 unknown verb, DSL002 abbreviated ticket id (D24: only full 26-char ULIDs persist). Output DirectiveRecord { namespace, verb, args, span, bound symref }. Tests via corpus files.
