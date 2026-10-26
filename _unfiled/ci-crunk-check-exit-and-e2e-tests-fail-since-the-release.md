+++
id = "01M5X2XDTA4WAYXGS19F3D43SD"
title = "CI: crunk check_exit and e2e tests fail since the release ramp downgrades new rules to warn"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-26T21:47:24Z"
updated = "2026-10-26T21:47:29Z"
scope = ["crates/crunk/**"]

[[acceptance]]
text = "Given the crunk check_exit and e2e tests, when nextest -p crunk runs, then all pass with the ramp active in the product and ramp = false (or ramp-aware expectations) in the fixtures"
bound = false
+++

CI run 40400911278 on 065cd9cf0d: crunk::check_exit an_error_severity_violation_exits_one and crunk::e2e e2e_02/03/04/06 fail on ubuntu and windows (exit 0 not 1, differing findings) because ~B3EMY2Z wired the ramp so rules new in 0.532.0 report at warn. ~YWF1B8K now lets crunk.toml carry [rules] ramp = false. Fix the fixtures/replay scenarios (and divergences list if needed); keep the product behaviour.
