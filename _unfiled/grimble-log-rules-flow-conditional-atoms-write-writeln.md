+++
id = "01M63G1NFTCN016KS8PT3JQNPF"
title = "Grimble LOG rules: flow-conditional atoms (write/writeln handles, os.open flags, shutil/json.dump/csv sinks, Path.write_text, js pipe, cs TextWriter)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-11-06T22:52:05Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/grimble/output-atoms.md"]
+++

found while working ~JKKJPTT: atoms whose output depends on where a handle flows are not detected
