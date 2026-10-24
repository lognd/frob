+++
id = "01M5PC8KZJ95RRS27B5DV06D9X"
title = "CI red on Linux: frob check --skip-tools reports 69 error findings (PATH001/PATH002/GRL016/TICK006/PARSE001/TEST001)"
type = "bug"
category = "in-progress"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-24T07:16:07Z"
updated = "2026-10-24T07:44:00Z"
scope = ["crates/crunk-*/**", "crates/frob-evidence/**", "crates/grimble-model/**", "docs/**", "frob.toml", "crates/gob-dev/**", "crates/gob-path/**", "crates/gob-check/**", "crates/frob-check/**", "crates/grimble-lints/**", "crates/gob-fs/**", "tests/crunk-parity/**", "packs/grimble-sysdesign/**", "crates/gob-plan/**", "crates/frob-lease/**"]

[[acceptance]]
text = "frob check --skip-tools --trust-from origin/experimental reports zero error-severity findings on the Linux CI check step"
bound = true
+++

List of findings: see CI run 40069211396 job rust (ubuntu-latest); list copied at /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/ci-check-errors.txt. Fix the code (Path operations, not literal separators) rather than waiving; waive only with a reason where truly unavoidable.
