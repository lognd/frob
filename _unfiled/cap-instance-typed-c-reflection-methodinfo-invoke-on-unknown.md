+++
id = "01M64ZYSNAWWBYFVHEC10TMK06"
title = "CAP: instance-typed C# reflection (MethodInfo.Invoke on unknown-origin values) is not reported"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T23:29:38Z"
updated = "2026-11-17T00:21:34Z"
labels = ["no-story"]
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "Given a C# unit calling MethodInfo.Invoke on a value of unknown origin, when grimble binds it, then a May reflection use is reported rather than nothing"
bound = false
+++

found while working S3EC85S: reflection chains are resolved only from literal Type.GetType roots
