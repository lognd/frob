+++
id = "01M4D95N49XQ50SFQNHS82E1JG"
title = "TYPING001: strict null or type checking disabled in project configuration (tsconfig, csproj Nullable, pyright, ty or mypy settings)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CXSN7VTEYX5AVSZVDX2WPZ"
reporter = "lognd"
created = "2026-10-08T08:13:03Z"
updated = "2026-10-08T08:13:03Z"
scope = ["changelog.d/**", "crates/grimble-lints/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given a tsconfig with strict false or a csproj without Nullable enable, when grimble check runs, then TYPING001 is Advisory naming the exact key to set"
bound = false

[[acceptance]]
text = "Given strict settings, when checked, then clean"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md row K06 (4.2 N14): notes/research/mining-report-2026-10-08.md C29 2.9 percent, 40 percent blocking; F-NULL-EDGE 8.1 percent of escaped mistakes (notes/research/mining-report-2026-10-08.md 6.2). Feeds [types] trust (cohesion.md 2.2).
