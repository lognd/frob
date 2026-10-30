+++
id = "01M665STQ6VPTEB61Z68K6G441"
title = "Wire PACK001 core-effects lock drift into grimble check"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-30T10:31:02Z"
updated = "2026-10-30T10:31:02Z"
scope = ["crates/grimble-check/src/**"]
+++

found while working ~867GGVJ: grimble check emits PACKS_NOT_LOADED and PackHost returns 0 subjects, so lock drift of core-effects is proven only at gob_packs::lock::verify. Call pack_rules::evaluate(lock, [PackState::Loaded(core_effects::locked()?)], []).
