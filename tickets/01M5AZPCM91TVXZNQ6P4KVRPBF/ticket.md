+++
id = "01M5AZPCM91TVXZNQ6P4KVRPBF"
title = "Frob rule corpora: add the vacuous (reason=vacuous) case for must_measure rules COV001 REF001 TODO002"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T21:04:48Z"
updated = "2026-10-20T01:56:03Z"
scope = ["crates/*/tests/mdtest/**", "crates/frob-check/tests/corpus.rs", "docs/reference/rules/**", "crates/gob-mdtest/coverage-allowlist.toml"]

[[acceptance]]
text = "COV001, REF001 and TODO002 each have a vacuous Unresolved corpus case in frob-check, and their coverage-allowlist entries are removed"
bound = true
+++

Burn down the [[gap]] kind=vacuous entries for product frob in crates/gob-mdtest/coverage-allowlist.toml; found while working ~WPZC326.
