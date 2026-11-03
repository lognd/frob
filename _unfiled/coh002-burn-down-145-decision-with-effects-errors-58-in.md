+++
id = "01M6G5ET66DE26C61NN88J9AE2"
title = "COH002 burn-down: 145 decision-with-effects errors (58 in unleased crates), then delete [rules.COH002]"
type = "chore"
category = "todo"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-11-03T07:37:25Z"
updated = "2026-11-03T11:33:11Z"
scope = ["crates/**", "frob.toml", "Cargo.lock", "scripts/claude-hooks/frob-suggest.py"]
+++

145 real findings (functions branching on computed data and doing fs effects); needs per-function refactors (pure decision + effect in caller) or grimble:shell marks. Biggest: frob 65 findings total, gob-symbols, gob-plan, gob-dev, grimble-model 19. 896 further unresolved findings are unknown-callee noise fixable via [coh] effect_calls/trivial in grimble.toml. Not started.
