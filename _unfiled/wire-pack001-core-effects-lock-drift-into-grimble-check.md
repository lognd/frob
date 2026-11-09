+++
id = "01M665STQ6VPTEB61Z68K6G441"
title = "Wire PACK001 core-effects lock drift into grimble check"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T10:31:02Z"
updated = "2026-11-09T14:25:13Z"
labels = ["no-story"]
scope = ["crates/grimble-check/src/**", "crates/grimble-check/tests/pack001_core.rs"]
+++

found while working ~867GGVJ: grimble check emits PACKS_NOT_LOADED and PackHost returns 0 subjects, so lock drift of core-effects is proven only at gob_packs::lock::verify. Call pack_rules::evaluate(lock, [PackState::Loaded(core_effects::locked()?)], []).
