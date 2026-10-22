+++
id = "01M5JHRGF0BKG6ZGNXBZR3F5DB"
title = "crunk parity tests fail on CRAFT010 advisory for init_default"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T19:35:13Z"
updated = "2026-10-22T19:46:55Z"
scope = ["crates/crunk/tests/**", "tests/crunk-parity/divergences.toml"]

[[acceptance]]
text = "Given the crunk parity tests, when run, then every_corpus_project_passes_or_has_a_reasoned_divergence and violations_match_python_for_every_project pass"
bound = false

[[acceptance]]
text = "Given a CRAFT010 advisory on init_default, when the cause is found, then it is fixed or recorded as a reasoned divergence, not silenced"
bound = false
+++

found while working 76STB57: pre-existing failures in parity and violations_match_python_for_every_project
