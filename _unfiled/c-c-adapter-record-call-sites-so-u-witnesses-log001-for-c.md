+++
id = "01M7088KFWFVQ9W4PZN2HR4QEV"
title = "C/C++ adapter: record call sites so U witnesses LOG001 for C and C++"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T13:34:18Z"
updated = "2026-11-09T13:35:00Z"
scope = ["crates/gob-symbols/src/c.rs"]
+++

c.rs records no CallSite; record call expressions with byte spans as java.rs does. Follow-up of MV8PWVD.
