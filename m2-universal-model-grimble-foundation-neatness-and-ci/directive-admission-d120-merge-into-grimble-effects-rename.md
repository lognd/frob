+++
id = "01M4CXT0CB3JA23T20J1CTEKYZ"
title = "Directive admission (D120): merge into grimble:effects, rename core/shell/calls to grimble:, drop pure/honest/dispatcher/trusted/idempotent/hook, admission registry test"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T04:54:36Z"
updated = "2026-10-13T13:23:35Z"
scope = ["changelog.d/**", "crates/gob-directives/**", "crates/grimble-check/**", "crates/gob-check/**", "docs/reference/**", "docs/schemas/**"]

[[acceptance]]
text = "Given every registered directive verb, when the admission test runs, then each has a row naming not-derivable, not-an-exception and its consumers"
bound = true

[[acceptance]]
text = "Given a file using frob:pure or frob:dispatcher, when checked, then a deprecation finding offers the fix to grimble:effects none or an accept exception"
bound = true
+++

docs/design/cohesion.md 4. Old spellings parse for one minor release with a DSL deprecation finding and an automatic fix.
