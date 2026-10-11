+++
id = "01M4MGEZH4541JT6XPYPQKH86R"
title = "Repo-level strip = symbols for the dev and test profiles so developer and CI test builds are smaller without a user cargo config"
type = "task"
category = "todo"
priority = "medium"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:35:19Z"
updated = "2026-10-11T03:35:19Z"
scope = ["Cargo.toml"]

[[acceptance]]
text = "cargo build --profile dev with the repo profile produces test executables at most a tenth of today's size, and the existing profile_coverage and release builds are unchanged"
bound = false
+++

found while draining tickets: adding strip = symbols to the user-level dev and test profiles cut linked test executables from 200 MB to about 20 MB. The repo currently ships no strip setting for dev or test, so every developer and CI run links the large binaries. Verify it does not break the debugger workflow (debug = 0 already).
