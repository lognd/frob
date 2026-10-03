+++
id = "01M3WYJ8059GN1VBGSA69X5BSZ"
title = "gob-rules + gob-macros: Rule derive, inventory registry, Finding, Severity"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0005"]
labels = ["milestone:2.0.0", "component:gob-rules"]
scope = ["crates/gob-rules/**", "crates/gob-macros/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ804VRZGKGH6ECGXSH9N"

[[acceptance]]
text = "Given a struct with #[derive(Rule)] and complete attributes, when the binary starts, then the registry lists it by id and slug with the doc comment as explanation"
bound = true

[[acceptance]]
text = "Given two rules declaring the same id, when the registry is built, then it fails naming both"
bound = true

[[acceptance]]
text = "Given a reason string under the configured minimum or matching a banned pattern, when checked, then the reason checker rejects it with the pattern name"
bound = true
+++

Implement crates/gob-rules and crates/gob-macros per rules.md sections 1 to 2 and D3/D32. gob-rules: Severity (Error, Warn, Advisory, Unresolved per rules.md), Finding { rule: RuleId, severity, span: Option<Span>, message, fingerprint, fix: Option<Fix> }, fingerprint = blake3 of (rule id, symref or file, normalized message) per D37/M15 (never line numbers), RuleMeta { id: FAMILYNNN, slug alias, family, product namespace, summary, explanation (markdown), tier Universal|Lang, scope File|Repo, fix kind Manual|Deterministic|VerifyCommit|FixIt, version u32, since }, Rule trait, a global registry over the inventory crate with lookup by id or slug and a duplicate-id check at startup that panics with both declaring crates. Exception primitive data types only (kind accept|defer|hotfix|baseline, reason, ticket, until) with the reason-quality checker from exceptions.md section 5 as a pure function; no directive parsing here. gob-macros: proc-macro crate exporting #[derive(Rule)] with #[rule(id = ..., slug = ..., family = ..., severity = ..., tier = ..., scope = ..., fix = ..., version = ...)] that generates the RuleMeta, an inventory::submit, and pulls the explanation from the item's doc comment. Compile-fail tests with trybuild for missing id and bad severity. gob-rules re-exports the derive. Example rule in gob-rules tests. Keep gob-macros free of workspace deps other than syn/quote/proc-macro2/darling.
