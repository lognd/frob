+++
id = "01M5XNHDQCQBE228DR8FZ3G6WK"
title = "Grimble expressiveness and granularity"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-27T03:12:53Z"
updated = "2026-10-27T03:12:53Z"
idempotency_key = "grimble-expr-epic-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
+++

Pessimistic audit 2026-10-26 (report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md). The capability layer (CAP001/CAP002/CAP005) is far coarser and leakier than the docs claim: net.connect is never detected in any language, may arguments are parsed but never enforced, at selectors collapse to file granularity, one in-scope use masks all out-of-scope uses of an atom, TypeScript/C#/shell are silently clean, detection is unresolved-callee spelling match with no alias resolution, only 7 atoms exist (the designed core-effects pack has 18 plus typed args), there is no effect transitivity, unowned code is unchecked, and a one-line accept CAP001 silences a node with no human gate. Children: a spec ticket first, then implementation by axis. Related existing: ~JKKJPTT (logging-routing rule), ~JXNJRTQ (output-atom catalogue), ~RAD5ARW (CAP004 emission), ~N8ZASNE (matrix verb), ~T28A73Q (COH002 tables into gob-caps), ~WNH8N7X (vocab classes and import resolution for NEAT013), ~RGQ353T (logand enforcement-gaps epic).
