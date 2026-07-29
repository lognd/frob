# FROBLEMS

Local notes on frob tooling failures hit in this repo. Tracked in git
(despite `.gitignore`'s standard entry for it -- this repo's own copy is
force-added); durable items get tickets.

## 2026-07-21: scope narrowing blocked by ScopeLeaseConflict (T-0485)

During the doable-warning scope-narrowing sweep, `frob ticket scope --add`
refused every add under a tree leased by an in-progress ticket
(T-0263: src/frob/strata/**, tests/unit/strata/**, docs/strata/**;
T-0423: src/frob/arch/**, src/frob/check/**, src/frob/graph/**;
T-0460: src/frob/render/**) -- even when the add was a strict subset of the
ticket's own pre-existing broad overlap, i.e. the change only SHRANK the
contention. Because scope changes are atomic, the whole narrowing rolls back
and the over-broad glob (and its WARNING) cannot be cleared.

Also hit: ScopeRemoveOrphansEvidence + lease interplay wedges T-0160
completely on the tests/** side: its recorded evidence includes
tests/unit/strata/test_native_staleness.py (under T-0263's lease), so the
covering --add required by the remove is itself refused.

Filed as T-0485. Tickets left un-narrowed, to re-narrow once
T-0263/T-0423/T-0460 land: T-0235 T-0261 T-0339 T-0341 T-0383 T-0384 T-0392
T-0393 T-0394 T-0395 T-0401 T-0410 T-0428 T-0439 T-0440; partial leftovers:
T-0160 (tests/** stays), T-0461 (re-add src/frob/render/ post-T-0460).
