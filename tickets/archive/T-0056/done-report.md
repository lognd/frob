## Done report

Delivered src/frob/strata/_facts.py: build_facts (fails closed on
duplicate ids, dangling flow/boundary references, unknown lattice levels,
cyclic lattices; emits deny-by-default structural diagnostics for
at-least-once-into-non-idempotent and label-above-clearance) and FactBase
(nodes_at, reachable with witness paths + barrier semantics, worst_age
longest-path staleness with inf-on-cycle, demand in base units). 14 new
unit tests bound via frob:tests; describes anchors + frob:doc edges to
docs/strata/kernel.md#fact-base. Ticket check exit 0, ruff clean.
