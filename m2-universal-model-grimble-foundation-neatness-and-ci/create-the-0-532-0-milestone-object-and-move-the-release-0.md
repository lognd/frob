+++
id = "01M4069ZE5BQECP28D8PTH7VKB"
title = "Create the 0.532.0 milestone object and move the release:0.532.0 labels onto it"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:13:00Z"
updated = "2026-10-03T15:29:07Z"
idempotency_key = "m2-rel-assemble"
labels = ["milestone:2", "area:release"]
scope = ["tickets/**"]

[[links]]
kind = "blocked-by"
target = "01M4069RACAQ8Z2C8APK0YKGNK"

[[links]]
kind = "blocked-by"
target = "01M4069RJJ4C73Z6GKKSV1E7PS"

[[acceptance]]
text = "Given the object, when frob release status 0.532.0 runs, then it lists the three exit criteria and the open tickets"
bound = true

[[acceptance]]
text = "Given PM034, when frob check runs, then it is silent for every member"
bound = true
+++

Run frob milestone new 0.532.0 with the goal and the three exit criteria of releases.md 7, add this epic and the milestone-2 epic ~0BTGRT5 members that are labelled, drop the interim label, and let PM034 prove membership. Uses the verbs only; no hand edits.
