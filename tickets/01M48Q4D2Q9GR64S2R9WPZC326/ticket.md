+++
id = "01M48Q4D2Q9GR64S2R9WPZC326"
title = "Coverage meta-test: required cases per polarity, tier and must_measure"
type = "story"
category = "todo"
priority = "high"
parent = "01M48Q4BE7FBVXDVYH59ZVPK66"
reporter = "lognd"
created = "2026-10-06T13:40:59Z"
updated = "2026-10-06T13:40:59Z"
scope = ["crates/gob-mdtest/**", "crates/*/tests/**"]

[[links]]
kind = "blocked-by"
target = "01M48Q4CHCFKJ9SSTVT471060B"

[[acceptance]]
text = "removing COV001's unresolved case fails naming COV001 P- unresolved"
bound = false

[[acceptance]]
text = "a Universal rule without its matrix rows fails naming it"
bound = false

[[acceptance]]
text = "the allowlist entries are per case kind with tickets"
bound = false
+++

testing.md 3: coverage.rs reads RuleMeta polarity, tier and must_measure and requires the case kinds of the table per rule; the allowlist is keyed by (product, rule, case kind), shrink-only, each with a ticket; a rule's fire and clean cases live in one suite file and the clean case certifies subjects. Split ~C5DQ4WJ and ~QSK0WB1 into per-kind entries. Design: docs/design/testing.md (D106); audit: notes/research/u-testing-audit.md.
