+++
id = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
title = "Shared web language engine: TS/TSX/JSX/CSS/HTML facts in gob for every product (D96)"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-06T04:29:06Z"
updated = "2026-10-06T04:29:06Z"

[[acceptance]]
text = "Every child closed or dropped with a reason"
bound = false

[[acceptance]]
text = "frob check, grimble check and crunk check each report at least one finding computed from the shared markup or style capability on a TSX/CSS fixture"
bound = false
+++

Implements docs/design/language-engines.md (D96). Facts about what is written in web code (syntax, imports, calls, JSX elements and attributes, CSS declarations, constant values, packages, framework routes) live in gob behind capabilities with Must/May/Unknown honesty and GRL catalog words, so crunk (tokens, A11Y), grimble (graph, WEBSEC, ROUTE) and frob (COV, AFFECT, touched tests) share one engine. First consumer: the owner's platform repository (Python, TS/TSX, CSS, crunk.toml).
