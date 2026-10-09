+++
id = "01M4FGYEWFAA9K4AHNCTV4NG4F"
title = "template entity does not parse: grmb-spec 4.7 excuse templates are MDL000"
type = "bug"
category = "todo"
priority = "high"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:34Z"
updated = "2026-10-09T05:07:34Z"
idempotency_key = "logand-gaps-T4"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble*/**", "crates/gob-*/**", "changelog.d/**"]

[[acceptance]]
text = "Given the grmb-spec 4.7 example template gen_proto { excuse net.listen for ... because=...; }, when grimble check runs, then it parses with no MDL000"
bound = false

[[acceptance]]
text = "Given a template with an excuse missing because, when grimble check runs, then MDL008"
bound = false

[[acceptance]]
text = "Given a template, when check --json runs, then template_excuses lists it with source"
bound = false
+++

Repro 04-template-entity-unparsed (~/projects/frob-v2-repros/logand-grimble-20261009/04-template-entity-unparsed): grmb-spec 4.7 and 14.1 item 7 make template the eighth entity kind and the only place an excuse can be written (MDL018 sends users there), but the parser rejects it at top level. Without it generated code cannot be excused.
