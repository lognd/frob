+++
id = "01M6607P2VZ5WZ4SH1TNZD5P85"
title = "CAP: direct shutil.move and os.rename source/dest"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T08:53:44Z"
updated = "2026-11-16T20:38:25Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/caps/**", "crates/grimble-bind/tests/it/caps.rs"]

[[acceptance]]
text = "Given a Python source calling shutil.move(a, b) or os.rename(a, b), when grimble check scans it, then fs.write is scoped to both paths (source and destination), proven by a test in crates/grimble-bind/src/caps.rs."
bound = true
+++

found while working ~MM08TTF: both paths are writes, undirected today
