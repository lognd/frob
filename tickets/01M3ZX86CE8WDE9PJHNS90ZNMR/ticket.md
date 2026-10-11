+++
id = "01M3ZX86CE8WDE9PJHNS90ZNMR"
title = "Generated GLOSSARY.md from this repository's effective configuration"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-11T22:31:38Z"
idempotency_key = "m2-nav-gen-glossary"
labels = ["milestone:2", "area:navigation"]
scope = ["crates/frob-ledger/src/gen/glossary.rs", "crates/frob-ledger/src/gen/mod.rs", "crates/frob-ledger/tests/gen_glossary.rs", "docs/guides/ticket-branch.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given a repository with `handle_min_len = 9`, when generated, then the glossary says 9"
bound = true

[[acceptance]]
text = "Given a schema field with no glossary entry, when checked, then GEN001 reports it"
bound = true
+++

Implements navigation.md section 3.1 and 3.3.

Fields, states, links and handles as configured here, never the defaults; checked equal to the schema.
