+++
id = "01M68CKMCEMGZ5V79E8ZCE2A5G"
title = "C++ namespace alias siblings: using-directive of an alias, inline namespaces, alias in class scope"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T07:08:27Z"
updated = "2026-10-31T09:37:40Z"
scope = ["crates/gob-symbols/**", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = "using namespace <alias-of-std>; then bare system(...) reports process.spawn or Unresolved"
bound = true

[[acceptance]]
text = "alias declared in a class, or via an inline/reopened namespace, resolves the same as a file-scope alias"
bound = true
+++

Found while working ~HVSKPQW: only namespace s = std; s::name is resolved (scope-aware, chained). Not verified: using namespace through an alias, aliases in class bodies, user-declared namespace std.
