+++
id = "01M7DQH6RH4YHBRBWD046YF7FZ"
title = "crunk visual regression rule: pick a non-colliding id (VIS001 is grimble-arch) and finish registration + [vis] thresholds"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-14T19:11:16Z"
updated = "2026-11-14T19:56:41Z"
labels = ["no-story"]
+++

CFF3C0J built crunk_gallery::png_io (commit 654c1ba595 on ticket/CFF3C0J) but VIS001 is owned by grimble-arch. Choose a new id (e.g. VISUAL001), register the rule, md page, [vis] thresholds (crunk-spec scope), bump ids.len(). The png dependency tree also needs an owner vet decision (VET001/3/4, duplicate miniz_oxide) before it can land.
