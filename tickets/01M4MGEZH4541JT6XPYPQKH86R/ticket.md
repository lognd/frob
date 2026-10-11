+++
id = "01M4MGEZH4541JT6XPYPQKH86R"
title = "Repo-level strip = symbols for the dev and test profiles so developer and CI test builds are smaller without a user cargo config"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-11T03:35:19Z"
updated = "2026-10-11T16:10:40Z"
scope = ["Cargo.toml"]

[[acceptance]]
text = "Cargo.toml sets strip = symbols for the dev and test profiles and leaves release, dist and profiling unstripped (measured: gob-cache shared test executable 26.7 MB to 3.6 MB with default debug, 4.8 MB to 3.5 MB with debug = 0), and the profile_coverage test passes"
bound = true
+++

found while draining tickets: adding strip = symbols to the user-level dev and test profiles cut linked test executables from 200 MB to about 20 MB. The repo currently ships no strip setting for dev or test, so every developer and CI run links the large binaries. Verify it does not break the debugger workflow (debug = 0 already).
