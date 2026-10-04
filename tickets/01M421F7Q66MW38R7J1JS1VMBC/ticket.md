+++
id = "01M421F7Q66MW38R7J1JS1VMBC"
title = "frob finds sibling binaries next to its own executable first, then on PATH (D87)"
type = "story"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T23:26:59Z"
updated = "2026-10-04T00:56:21Z"
scope = ["crates/frob-check/src/sibling.rs", "crates/frob-check/tests/sibling.rs", "docs/design/sibling-contract.md", "crates/gob-exec/src/discover.rs", "crates/gob-exec/src/lib.rs", "crates/gob-exec/src/program.rs", "crates/gob-exec/tests/discover.rs", "crates/frob/src/doctor.rs", "crates/frob/tests/sibling_discovery.rs", "crates/frob-check/src/sibling/mod.rs", "docs/design/products.md", "crates/frob/tests/snapshots/cli__doctor_schema.snap", "crates/frob/tests/cli.rs"]

[[acceptance]]
text = "Given grimble next to the running frob and not on PATH, when frob check runs, then it finds and runs that grimble"
bound = false

[[acceptance]]
text = "Given different grimble versions next to frob and on PATH, when frob doctor runs, then it reports both and uses the one next to frob"
bound = false
+++

D87 (products.md 6): uv tool install frob exposes only frob on PATH while grimble and crunk, installed as dependencies, sit in the same tool environment. Sibling discovery must look first in the directory of the running frob executable (resolve symlinks; bin/ on Unix, Scripts\\ on Windows, .exe suffix on Windows), then on PATH, and report which location it used (in check's fidelity or sibling section and in frob doctor). A sibling found in both places: the one next to frob wins and doctor notes the other with its version if it differs. Use Path and argv APIs only (paths.md); no string path handling.
