+++
id = "01M7DHM0XC9QGX8T81HNGWJJ4E"
title = "gob-plan exec: precompiled slot executor to reach DOC002 1.3x (follow-up of 4E3SVYY)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-14T17:27:57Z"
updated = "2026-11-14T17:27:57Z"
labels = ["no-story"]
+++

Micro-optimisations on branch ticket/4E3SVYY (f98df80f0a) only moved DOC002 7.48x to 7.09x. Floor is ~2x handwritten from per-quantifier hash lookups and Val/Datum allocation; needs executor redesign (precompiled slots). no-story: internal perf.
