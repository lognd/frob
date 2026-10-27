+++
id = "01M5FEF9785BFG86935HYZ7H5P"
title = "Share the inline-case dir reader across parser inline tests"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T14:40:01Z"
updated = "2026-10-27T02:58:36Z"
+++

tests/inline.rs in gob-plan, grimble-model, gob-directives and crunk-spec duplicate the resources/inline dir reader; extract a shared helper. Found while working ~2GG2KXR.
