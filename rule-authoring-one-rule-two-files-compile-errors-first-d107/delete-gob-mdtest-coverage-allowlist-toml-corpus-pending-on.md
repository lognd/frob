+++
id = "01M6QK5DEGBC20VB7EXD1XQHVS"
title = "Delete gob-mdtest coverage-allowlist.toml: corpus = pending(..) on ~21 rules; adopt rule_suite! in rule crates"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-11-06T04:51:38Z"
updated = "2026-11-06T04:51:38Z"
labels = ["no-story"]
scope = ["crates/*/src/rules/**", "crates/gob-mdtest/**"]
+++

Split from ~JHD5710. Needs the corpus field ticket. Replaces mdtest!(dir=src/rules) with rule_suite! and removes the 18 case-kind and 3 matrix gaps.
