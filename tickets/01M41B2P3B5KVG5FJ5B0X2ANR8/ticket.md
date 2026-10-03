+++
id = "01M41B2P3B5KVG5FJ5B0X2ANR8"
title = "Text view prints a verb's rendered lines raw instead of as an indented YAML-ish list"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T16:55:39Z"
updated = "2026-10-03T17:37:25Z"
scope = ["crates/gob-cli/**", "crates/frob/tests/snapshots/**", "crates/frob/src/board_cmd.rs", "crates/frob/tests/board.rs"]

[[acceptance]]
text = "Given frob board --text, when it runs, then stdout is exactly the renderer's rows with no envelope header, list markers or indent"
bound = true

[[acceptance]]
text = "Given --json, when it runs, then the envelope is unchanged"
bound = true
+++

frob board (~4XZVMNC) renders its own text into data.lines, but the generic text envelope prints it as 'board: ok / lines: / - row' with a 6-character indent, which wastes width and looks archaic. When a verb's data carries pre-rendered lines (board, and any future dashboard verb), the text view should print them verbatim with no envelope header or list markers; JSON is unchanged. Owner preference: pretty output from one renderer.
