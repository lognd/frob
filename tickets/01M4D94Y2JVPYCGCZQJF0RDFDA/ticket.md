+++
id = "01M4D94Y2JVPYCGCZQJF0RDFDA"
title = "hot-context capability: region reachable (Must/May) from vocabulary-declared hot roots; Unknown edges give Unresolved"
type = "story"
category = "todo"
priority = "high"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-08T08:12:49Z"
updated = "2026-10-08T08:12:49Z"
scope = ["changelog.d/**", "crates/gob-ir/**", "crates/gob-symbols/**", "crates/gob-caps/**"]

[[acceptance]]
text = "Given a MonoBehaviour whose Update calls a helper that calls GetComponent, when hot(region) is queried, then the helper call is Must-hot"
bound = false

[[acceptance]]
text = "Given a call through an interface with unknown targets, when queried, then the answer is May; given the unity pack disabled, then NotApplicable"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md rows U02, U03 (4.2 N17); notes/research/creators-games-2026-10-08.md 5.1 ranks 2-3 (Unity docs, Microsoft analyzers, JetBrains performance-critical context, Dunstan measurements). JetBrains' hot context is IDE-only, so this is value only frob provides in CI. Also usable for game loops, render bodies and request handlers.
