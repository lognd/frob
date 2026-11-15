+++
id = "01M7DZCFW0YB0PH3WDFWR5Q961"
title = "Grimble LOG: open(fd 1/2) and file-handle destinations for json.dump/csv/shutil/pipe"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-14T21:28:30Z"
updated = "2026-11-15T04:01:47Z"
labels = ["no-story"]
+++

cut from ~KGBAD9H: open(1,'w') / open(sys.stdout.fileno()) needs a py.open fd catalogue row in docs/design/grimble/output-atoms.md (outside log/** scope); file-handle 'or file' destinations are an advisory-severity decision since data files are not logs.
