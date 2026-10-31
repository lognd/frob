+++
id = "01M688124N09MGJXMHXHVSKPQW"
title = "C++ namespace alias (namespace s = std; s::system) is a silent pass"
type = "bug"
category = "todo"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T05:48:25Z"
updated = "2026-10-31T05:48:25Z"
scope = ["crates/grimble-bind/**, crates/gob-caps/**, crates/gob-symbols/**, crates/gob-ir/**, crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = 'C++ s::system("x") through namespace s = std reports certain process.spawn (or Unresolved), never clean'
bound = false

[[acceptance]]
text = "The ignored probe in symbolic_audit.rs is un-ignored and passes"
bound = false
+++

Probe checks clean today; using std::system and plain std::system resolve. Found while working ~AH9XAGZ; the probe is an #[ignore]d test in crates/grimble-check/tests/symbolic_audit.rs.
