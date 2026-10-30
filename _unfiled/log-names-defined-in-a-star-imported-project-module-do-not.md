+++
id = "01M65FKMBKNXK4PDXXDHFTKHDK"
title = "LOG: names defined in a star-imported project module do not shadow builtins"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T04:03:10Z"
updated = "2026-10-30T04:03:10Z"
scope = ["crates/grimble-check/src/log/**", "docs/design/output-atoms.md"]
+++

found while working 01M64230T88F77RTBYS9M3CY3C: locally defined (Opaque) names are not bound by star import.
