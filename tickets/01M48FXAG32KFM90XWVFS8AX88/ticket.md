+++
id = "01M48FXAG32KFM90XWVFS8AX88"
title = "grimble-bind: SYS004 checks undeclared flows over import and JSX component call edges between owners"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:34:47Z"
updated = "2026-10-06T14:59:36Z"
scope = ["crates/grimble-bind/**", "design/model.grmb", "docs/design/binding.md", "crates/gob-mdtest/coverage-allowlist.toml"]

[[acceptance]]
text = "SYS013 (the id binding.md 11.3 assigns to undeclared flow) fires once per ordered owner pair when a Must TS import or call edge, JSX component uses included, crosses owners with no flow in that direction; the web conformance fixture fires ui to api."
bound = true

[[acceptance]]
text = "An Unknown or May edge, or a May owner, is Unresolved (unresolved-edge or may-only-owner), never clean; an external package is not an edge between owners; foreign ends are unchecked."
bound = true

[[acceptance]]
text = "The rule consumes the one SymbolGraph of the snapshot through the existing binding path (owners, flows, Cx), with no web-specific side path; it is not applicable with fewer than two code-owning nodes or no import or call edge."
bound = true

[[acceptance]]
text = "A flow in either direction between the two owners allows the edge; with no flow between them it fires."
bound = true
+++

The shared web fixture (ui owns src/components, api owns src/api; App.tsx imports and calls fetchUser) examines 2 SYS004 subjects and reports nothing: SYS004 does not yet walk cross-owner import and call edges through JSX component references. First real grimble web rule. Found while working ~4M1BX5H.
