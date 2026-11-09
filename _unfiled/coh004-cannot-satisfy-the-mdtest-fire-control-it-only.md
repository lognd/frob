+++
id = "01M6VS2WJY7S0BQM0WEJ9M3D61"
title = "COH004 cannot satisfy the mdtest fire control: it only reports Unresolved"
type = "bug"
category = "done"
outcome = "duplicate"
priority = "medium"
reporter = "lognd"
created = "2026-11-07T19:52:04Z"
updated = "2026-11-07T20:40:31Z"
scope = ["crates/grimble-check/**", "crates/gob-mdtest/**"]
+++

found while working ~GYNK2NK: grimble-check coh002_rule mdtest_corpus fails with MissingControl: rule COH004 has no expect=fire block. COH004 is heuristic and never fires (Unresolved only), so the controls audit in gob-mdtest run.rs cannot be satisfied. Decide: let Unresolved-only heuristic rules waive the fire control, or change the rule.
