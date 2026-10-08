+++
id = "01M4D6NWQ3F11S4MB3KT5K4JHZ"
title = "Register [land] (require_base_green, ci_required, ci_ignore, block_on_unknown_ci) in FrobConfig so validation and config sync see it"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:39Z"
updated = "2026-10-08T07:29:39Z"
scope = ["changelog.d/**", "crates/frob/**", "crates/frob-land/**"]

[[acceptance]]
text = "Given a frob.toml with [land], when doctor, check and config sync run, then the table validates and appears in the generated reference"
bound = false
+++

Follow-up from ~GHMWDGG: the table is read straight from the base frob.toml; whether FrobConfig::load tolerates it is unverified (cf. the unknown-key failure of [pm] sprint_gate under an older binary).
