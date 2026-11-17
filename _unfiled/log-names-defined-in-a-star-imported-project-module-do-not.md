+++
id = "01M65FKMBKNXK4PDXXDHFTKHDK"
title = "LOG: names defined in a star-imported project module do not shadow builtins"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T04:03:10Z"
updated = "2026-11-17T06:19:58Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/grimble/output-atoms.md"]
+++

found while working 01M64230T88F77RTBYS9M3CY3C: locally defined (Opaque) names are not bound by star import.
