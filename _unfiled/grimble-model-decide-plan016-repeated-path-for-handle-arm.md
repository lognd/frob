+++
id = "01M6NZN0TMJWHA1Z3T75ZH9TDJ"
title = "grimble-model: decide PLAN016 repeated path for handle-arm retries"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-05T13:51:23Z"
updated = "2026-11-05T16:53:05Z"
scope = ["docs/design/grimble/**"]
+++

found while working ~NTVM2T5: spec does not say which steps a handle-arm retry repeats; PLAN016 skips handle arms until decided. Also decide: do an include's inner steps count for arm retries (implemented as yes).
