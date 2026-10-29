+++
id = "01M63G1NY275Y890ZD5W1EVN63"
title = "gob-symbols C# graph overflows the stack on using static System.Console"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-29T09:32:21Z"
updated = "2026-10-29T09:32:21Z"
scope = ["crates/gob-symbols/**"]
+++

found while working ~JKKJPTT: one-file C# repo with using static System.Console aborts with stack overflow (reproduced on the baseline release binary)
