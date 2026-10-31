+++
id = "01M688121YPN90V6GKDTFZAPQN"
title = "Java Class.forName with a literal then getMethod is a silent pass"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T05:48:25Z"
updated = "2026-10-31T06:30:43Z"
scope = ["crates/grimble-bind/**", "crates/gob-caps/**", "crates/gob-symbols/**", "crates/gob-ir/**", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = 'Java Class.forName("java.lang.Runtime").getMethod("exec", String.class) reports a CAP001 (certain process.spawn or Unresolved), never clean; computed Class.forName(c) stays reported'
bound = false

[[acceptance]]
text = "The ignored probe in symbolic_audit.rs is un-ignored and passes"
bound = false
+++

Probe checks clean today while Class.forName(c) and Class.forName("java.lang." + "Runtime") are reported, so a literal name defeats the reflection detector. Found while working ~AH9XAGZ; the probe is an #[ignore]d test in crates/grimble-check/tests/symbolic_audit.rs.
