+++
id = "01M6607P2VZ5WZ4SH1TNZD5P85"
title = "CAP: direct shutil.move and os.rename source/dest"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T08:53:44Z"
updated = "2026-11-16T20:21:40Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/caps/**"]

[[acceptance]]
text = "Given a Python source calling shutil.move(a, b) or os.rename(a, b), when grimble check scans it, then fs.write is scoped to both paths (source and destination), proven by a test in crates/grimble-bind/src/caps.rs."
bound = false
+++

found while working ~MM08TTF: both paths are writes, undirected today
