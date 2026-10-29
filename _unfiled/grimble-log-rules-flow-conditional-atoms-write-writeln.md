+++
id = "01M63G1NFTCN016KS8PT3JQNPF"
title = "Grimble LOG rules: flow-conditional atoms (write/writeln handles, os.open flags, shutil/json.dump/csv sinks, Path.write_text, js pipe, cs TextWriter)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-10-29T09:32:21Z"
scope = ["crates/grimble-check/src/log/**"]
+++

found while working ~JKKJPTT: atoms whose output depends on where a handle flows are not detected
