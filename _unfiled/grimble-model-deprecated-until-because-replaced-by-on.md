+++
id = "01M7EXXPCQKCQ0Q0AYNKVQG4S8"
title = "grimble-model: deprecated until= because= replaced_by on contract members/routes/variants, with removal rules"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:22:11Z"
updated = "2026-11-15T06:22:16Z"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXXP1YXB5DY9WKF73E4B3S"

[[acceptance]]
text = "Each of the three Error cases has a fixture"
bound = false

[[acceptance]]
text = "Syntax documented in SPEC"
bound = false
+++

Research: ~/projects/frob-research-lifecycle.md rec 2 (G03). Removal of a never-deprecated member, removal while a consumer reads it, and deprecation past until with readers are Errors. Depends on member diff.
