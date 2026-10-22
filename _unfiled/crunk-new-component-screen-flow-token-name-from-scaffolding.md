+++
id = "01M5H8MMN5PXGJG2XGS76STB57"
title = "crunk new component|screen|flow|token NAME [--from ...] scaffolding verb"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-22T07:36:34Z"
updated = "2026-10-22T19:35:56Z"
scope = ["crates/crunk/**", "docs/crunk/README.md", "docs/reference/cli/crunk.md"]

[[acceptance]]
text = "Given crunk new component|screen|flow|token NAME, when run in a project, then a valid skeleton design file is written in the documented location and passes crunk validation"
bound = true

[[acceptance]]
text = "Given the target file already exists, when crunk new runs, then it refuses without overwriting and exits non-zero"
bound = true

[[acceptance]]
text = "Given an invalid NAME or a --from source that does not exist, when crunk new runs, then it fails with a clear error and writes nothing"
bound = true
+++

Cut from AFVVZ8Y (only crunk edit shipped). See docs/design/crunk.md section 5.
