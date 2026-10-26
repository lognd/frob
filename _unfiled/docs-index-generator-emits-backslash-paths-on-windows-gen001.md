+++
id = "01M5W37Y1PAH12PCD44W3VRH2G"
title = "docs index generator emits backslash paths on Windows (GEN001 red on windows CI)"
type = "bug"
category = "todo"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-26T12:33:54Z"
updated = "2026-10-26T12:33:54Z"
scope = ["crates/gob-dev/src/render/**", "crates/gob-dev/tests/**", "docs/**"]

[[acceptance]]
text = "docs_index renders forward-slash links and paths on every platform (use gob_path::forward_slashes), with a unit test that feeds a Windows-style path component join"
bound = false

[[acceptance]]
text = "gen all --check is clean on Windows CI: no backslashes in docs/README index tables"
bound = false
+++

CI run on e09941d9e8: windows GEN001 failed, docs index tables had crunk\README.md style links. Ubuntu passed. Exit criterion 6.
