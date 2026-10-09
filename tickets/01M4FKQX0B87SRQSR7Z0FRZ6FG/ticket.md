+++
id = "01M4FKQX0B87SRQSR7Z0FRZ6FG"
title = "gob-plan grl_spec tests fail at HEAD: NEAT013 spec block does not parse and print_stability fixed-point fails"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T05:56:25Z"
updated = "2026-10-09T15:04:22Z"
scope = ["crates/gob-plan/**", "docs/design/grl-spec.md"]

[[acceptance]]
text = "Given the grl-spec examples, when gob-plan tests run, then both tests pass"
bound = false
+++

found while working ~FSW5067: nextest ci run shows grl::parse::tests::every_grl_example_in_grl_spec_parses (NEAT013 block with vocab(...) knob) and gob-plan print_stability::every_whole_rule_in_the_spec_is_a_fixed_point_and_round_trips failing; unrelated to the CAP change.
