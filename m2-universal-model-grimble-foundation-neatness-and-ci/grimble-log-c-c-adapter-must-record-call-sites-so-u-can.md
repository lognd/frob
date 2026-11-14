+++
id = "01M703GDD7M0W356CVGE8XHH4G"
title = "Grimble LOG: C/C++ adapter must record call sites so U can witness LOG001"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-11-09T12:11:11Z"
updated = "2026-11-14T20:55:42Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/src/c*.rs"]

[[acceptance]]
text = "extract_file on a C source records call sites with the enclosing function as caller"
bound = true
+++

found while working ~MV8PWVD: extract_file yields no calls or uses for C
