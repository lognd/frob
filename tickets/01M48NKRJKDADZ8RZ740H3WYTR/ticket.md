+++
id = "01M48NKRJKDADZ8RZ740H3WYTR"
title = "cargo dev new-rule scaffold, compiled and run in CI (ruff add_rule.py, clippy new_lint)"
type = "task"
category = "todo"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:14:25Z"
updated = "2026-10-06T13:14:25Z"
scope = ["crates/gob-dev/**", ".github/workflows/ci.yml"]

[[links]]
kind = "blocked-by"
target = "01M48MR49A0D52XAFWTD3ZK8NM"

[[acceptance]]
text = "cargo dev new-rule output builds and its mdtest passes without edits"
bound = false

[[acceptance]]
text = "a cargo dev ci step scaffolds into a temporary copy and fails if the scaffold stops compiling"
bound = false
+++

Source review N3 (notes/research/codegen-macros.md G9): ruff (scripts/add_rule.py, exercised in ci.yaml) and clippy (cargo dev new_lint) keep a new-rule scaffold that CI proves still compiles, which protects macro changes. Add cargo dev new-rule --product P --id ID --slug S --family F writing the rule struct with every required attribute (polarity, must_measure, version, since per ~D3ZK8NM), a doc skeleton with the required sections, the mdtest corpus file with a fire and a clean block, and the registration touchpoint; a CI step scaffolds into a temporary copy, builds it and runs its mdtest.
