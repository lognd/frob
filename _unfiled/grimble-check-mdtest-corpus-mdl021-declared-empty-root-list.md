+++
id = "01M5A8VN73Y80YRBFPJHATF3JF"
title = "grimble-check mdtest corpus: MDL021 'declared empty root list' case reports a required Unresolved instead of a finding"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-19T14:25:43Z"
updated = "2026-11-03T07:47:14Z"
+++

tests/mdtest/mdl021.md case 'A declared empty root list fires #1' fails on main: expected a non-Unresolved MDL021 finding, got a required Unresolved. Found while working ~P04H5Z3.
