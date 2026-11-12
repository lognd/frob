+++
id = "01M5F8MNMXE10ZQFN7BRA0V3XC"
title = "unity pack: dead-code (DEAD001) reads the engine entry-point vocabulary"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T12:58:06Z"
updated = "2026-11-12T16:48:45Z"
labels = ["no-story"]
scope = ["crates/grimble-arch/src/**", "crates/gob-ir/src/engine.rs", "changelog.d/**", "crates/grimble-check/src/product.rs", "crates/grimble-arch/tests/rules.rs"]

[[acceptance]]
text = "Given a Unity pack project with engine entry points (Awake/Start/Update etc), when DEAD001 runs, then those methods are not reported dead, covered by a test"
bound = true
+++

found while working ~YR0STJ5: only COV001 consumes EngineVocab roots
