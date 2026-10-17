+++
id = "01M55896EM27W5SD8BGZ0816YV"
title = "gob-rules/gob-check/gob-macros: stage-bodied and relayed repo rules with per-rule subjects (prerequisite of ~7Z6YH8P)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-17T15:39:26Z"
updated = "2026-10-17T19:34:32Z"
scope = ["crates/gob-rules/**", "crates/gob-check/**", "crates/gob-macros/**", "docs/design/rule-authoring.md"]
+++

found while working ~7Z6YH8P. The ticket asks for body = stage(ModelCheck|Binding) but #[rule] has no body form, RuleSet::stage entries have no inapplicable/subjects, and a non-must_measure repo rule cannot report its subject count (subjects_examined for MDL would vanish). Needed: (1) a stage/relay body so a rule can relay findings a sibling stage already computed (keeping typed UnresolvedReason, per-finding severity, required reason, custom anchors, byte ranges, fixes, which plain Out cannot express); (2) SubjectsRun -> Option<usize> and subjects for any repo rule; (3) inapplicable for stage rules (SYS not_applicable). Blocked on lease: gob-check is leased by ~YT46TP7.
