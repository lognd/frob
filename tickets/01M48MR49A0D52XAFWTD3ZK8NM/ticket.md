+++
id = "01M48MR49A0D52XAFWTD3ZK8NM"
title = "Rule declarations: require polarity and must_measure, validate version/since, structured rule docs (ruff ViolationMetadata, ty declare_lint)"
type = "story"
category = "todo"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T12:59:20Z"
updated = "2026-10-06T13:27:44Z"
scope = ["crates/gob-macros/**", "crates/gob-rules/**", "crates/*/src/**"]

[[links]]
kind = "blocked-by"
target = "01M48PBZ7A1DSJJW9ZDKCJ0F5T"

[[acceptance]]
text = "a Rule without polarity or must_measure fails to compile with a span (trybuild ui case), and every existing rule declares both"
bound = false

[[acceptance]]
text = "version and since must be semver or the release placeholder; anything else fails to compile (trybuild)"
bound = false

[[acceptance]]
text = "a registry-driven test fails naming each rule whose doc lacks What it does / Why it matters / Example, or whose Example does not run as an mdtest"
bound = false

[[acceptance]]
text = "RuleMeta carries the declaring file and line and the rule page links to it (snapshot)"
bound = false
+++

Macro review 2026-10-06 against ruff (derive(ViolationMetadata): docs from the doc comment, required stability metadata) and ty (declare_lint!: doc comment with fixed sections, rendered to the rules page). Today #[derive(Rule)] silently defaults polarity to Pplus and must_measure to false (its own docs say to always declare them), takes version/since as unchecked strings, and accepts any doc comment as the explanation. Make polarity and must_measure required (a compile error naming the rule when missing, migrate the existing rules), validate version/since as semver at expansion, and require the doc comment to carry the sections What it does / Why it matters / Example (compile error with a span), so the generated rule pages have one shape; the Example block becomes an executable mdtest (build-test-ci.md 2, ty lint_docs).
