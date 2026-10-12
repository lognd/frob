+++
id = "01M4K4QKXHB534W7BMFWXKT9TC"
title = "frob doctor fails CFG001: frob.toml lacks the materialized tickets.branch knob"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 1
reporter = "Claude"
created = "2026-10-10T14:51:04Z"
updated = "2026-10-10T14:53:42Z"
scope = ["frob.toml"]

[[acceptance]]
text = "frob doctor reports 0 errors"
bound = true
+++

found while coordinating the drain: frob doctor on experimental reports CFG001 missing-materialized-knob tickets.branch; frob config sync writes it.
