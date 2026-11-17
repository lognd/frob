+++
id = "01M66JP3Y9AHPNPNK5S9ZHTAS8"
title = "Prune baseline in the merge-train path (train_check, candidate)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-30T14:16:11Z"
updated = "2026-11-17T01:21:35Z"
labels = ["no-story"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "merge-train candidates prune dead baseline keys on the merge tree like single land"
bound = false
+++

found while working QJPFKV3: only the single-land prepare path prunes.
