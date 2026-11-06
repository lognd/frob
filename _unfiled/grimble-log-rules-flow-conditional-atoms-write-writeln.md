+++
id = "01M63G1NFTCN016KS8PT3JQNPF"
title = "Grimble LOG rules: flow-conditional atoms (write/writeln handles, os.open flags, shutil/json.dump/csv sinks, Path.write_text, js pipe, cs TextWriter)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-11-06T22:52:14Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/log/**", "docs/design/grimble/output-atoms.md", "changelog.d/01M63G1NFTCN016KS8PT3JQNPF.*.md"]

[[acceptance]]
text = "Stream-sink atoms (py.json-dump, py.csv-writer, py.shutil) fire when the destination resolves to a std stream, directly or through an alias, and stay silent for other destinations"
bound = false
+++

found while working ~JKKJPTT: atoms whose output depends on where a handle flows are not detected
