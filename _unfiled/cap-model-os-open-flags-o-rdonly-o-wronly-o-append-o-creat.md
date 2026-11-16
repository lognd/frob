+++
id = "01M6607NN6SJGYE41YHRVV6B3H"
title = "CAP: model os.open flags (O_RDONLY/O_WRONLY/O_APPEND/O_CREAT)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T08:53:44Z"
updated = "2026-11-16T20:16:08Z"
labels = ["no-story"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/caps/**", "packs/core-effects/atoms.toml", "crates/grimble-bind/tests/it/caps.rs"]

[[acceptance]]
text = "Given a Python source calling os.open(p, os.O_RDONLY), when grimble check scans it, then an fs.read use is reported and not fs.write, proven by a test in crates/grimble-bind/src/caps.rs."
bound = true
+++

found while working ~MM08TTF: os.open flags are not in the Python vocab
