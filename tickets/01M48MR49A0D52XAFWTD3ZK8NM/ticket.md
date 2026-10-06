+++
id = "01M48MR49A0D52XAFWTD3ZK8NM"
title = "Rule declarations: require polarity and must_measure, validate version/since, structured rule docs (ruff ViolationMetadata, ty declare_lint)"
type = "story"
category = "todo"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T12:59:20Z"
updated = "2026-10-06T13:14:10Z"
scope = ["crates/gob-macros/**", "crates/gob-rules/**", "crates/*/src/**"]

[[acceptance]]
text = "a Rule without polarity or must_measure fails to compile with a span (trybuild ui case)"
bound = false

[[acceptance]]
text = "a malformed version or since fails to compile (trybuild)"
bound = false

[[acceptance]]
text = "a rule doc without the three sections fails to compile, and every existing rule is migrated"
bound = false

[[acceptance]]
text = "each rule's Example block runs as an mdtest"
bound = false
+++

Macro review 2026-10-06 against ruff (derive(ViolationMetadata): docs from the doc comment, required stability metadata) and ty (declare_lint!: doc comment with fixed sections, rendered to the rules page). Today #[derive(Rule)] silently defaults polarity to Pplus and must_measure to false (its own docs say to always declare them), takes version/since as unchecked strings, and accepts any doc comment as the explanation. Make polarity and must_measure required (a compile error naming the rule when missing, migrate the existing rules), validate version/since as semver at expansion, and require the doc comment to carry the sections What it does / Why it matters / Example (compile error with a span), so the generated rule pages have one shape; the Example block becomes an executable mdtest (build-test-ci.md 2, ty lint_docs).
