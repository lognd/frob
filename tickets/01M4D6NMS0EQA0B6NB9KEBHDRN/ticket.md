+++
id = "01M4D6NMS0EQA0B6NB9KEBHDRN"
title = "grimble ack: validate arguments and preconditions before binding the repository; it errors on this repository after 6-9 s"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:30Z"
updated = "2026-10-10T19:36:35Z"
scope = ["changelog.d/**", "crates/grimble/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given invalid arguments, when grimble ack runs, then it refuses in milliseconds; given valid ones on this repository, then it succeeds or explains why"
bound = false
+++

notes/research/profile-2026-10-07.md section 5 item 13: --dry-run --all gives E-ACK-EMPTY and a file path E-ACK-REFUSED, each after a full bind.
