# Ticket/strata shared-graph inventory (T-3032)

One sentence: which graph-shaped concerns in `frob.tickets` are genuinely
shared with strata (and so belong in a shared kernel) versus genuinely
ticket-specific (and so should stay in `frob.tickets`), module by module,
with the reasoning and the extraction status of each.

This is the per-concern inventory T-3032's acceptance criteria requires,
covering the six modules the owner's 2026-08-26 directive measured
(`parent`/`blocked_by`/`children`/`ancestor`/`closure`/`cycle`/`graph`
reference counts): `_setters.py` (81), `_models.py` (64), `_doable.py`
(32), `_store.py` (28), `_evidence.py` (16), `_scope.py` (4).

## Method

T-3032 supersedes the "migrate tickets last" plan (T-3004 section 9) with
an incremental one: pick the smallest shared concern, prove existing
regression tests cover its current behaviour, extract it to a shared
home, reroute tickets onto it, verify tests pass unchanged, land, repeat.
This document is written the same way -- each row below is graded
SHARED, TICKET-SPECIFIC, or SIMILAR-BUT-SUBTLY-DIFFERENT (kept separate
per the ticket's own warning: "a forced abstraction over two subtly-
different semantics is worse than two implementations").

## Inventory

### `src/frob/tickets/_evidence.py` (16 graph-shaped references)

| Concern | Verdict | Reasoning |
|---|---|---|
| `_open_descendant_ids` (parent-chain, any-depth walk, T-0715 done-transition guard) | **SHARED -- EXTRACTED THIS LEAF** | Pure id-graph traversal (build `{parent: [children]}`, BFS from a root), no ticket-state semantics in the walk itself (only in the filter applied to its OUTPUT). Duplicated verbatim in `frob.gates._milestone` before this leaf (both modules' docstrings disclosed it). Now both delegate to `frob.graph._hierarchy.children_by_parent_id`/`descendant_ids`. |
| Evidence-id-to-pytest-node-id binding, `frob:tests` reachability | TICKET-SPECIFIC | No graph shape at all here besides looking up a bound id in a set; this is ticket ledger bookkeeping (evidence/acceptance-criterion binding), not a hierarchy or reachability concern strata shares. |

### `src/frob/tickets/_doable.py` (32 graph-shaped references)

| Concern | Verdict | Reasoning |
|---|---|---|
| `blocked_by` transitive resolution (`_open_blockers`, MILE001's "blocked by a later-milestone ticket" check) | **SHARED, NOT YET EXTRACTED -- follow-up ticket T-draft-5d5c1eb2** | Same shape as the parent/child walk: an edge relation (`blocked_by` instead of `parent`) over ticket ids, walked to find live blockers. Strata's own dependency/flow edges (`design/frob.strata`'s `mediate`/flow declarations) need the identical "is X still blocked by something live" closure. Candidate for the SECOND extraction. |
| `effective_milestone`'s ancestor walk (declared/inherited-from-parent resolution) | **SIMILAR-BUT-SUBTLY-DIFFERENT -- keep separate, for now** | Superficially another parent-chain walk, but it stops at the FIRST ancestor with a declared value (short-circuit, not full-depth collection) and folds in a repo-level config default as a terminal fallback (`[tickets].default_milestone`) -- semantically a "resolve one inherited scalar value" walk, not a "collect a whole reachable set" walk like `descendant_ids`. Forcing it onto the same primitive would need a callback/predicate parameter this leaf's positive-control tests do not exercise; left as its own implementation rather than a premature abstraction. |
| `_doable_sort_key`, `runs_last` pairing, quarantine/lease collision checks | TICKET-SPECIFIC | These consult ticket STATE (queued/planned/lease ownership) alongside the graph shape; the graph traversal is incidental to a scheduling policy strata has no equivalent of. |

### `src/frob/tickets/_models.py` (64 graph-shaped references)

| Concern | Verdict | Reasoning |
|---|---|---|
| `_validate_parent` (typed-id shape validation, dangling-reference refusal at construction time) | **SHARED, NOT YET EXTRACTED -- follow-up ticket T-draft-e7434c27** | strata-core's own `GraphSchema` (T-3005) already does "construction-time refusal of a dangling/malformed typed reference" as its generic contract; `Ticket.parent`'s validator is a narrower, hand-written instance of exactly that contract. Candidate extraction, but blocked on deciding whether it goes through the Rust `strata_core` extension (today's `.pyi` only exposes `reachable`/`worst_age`/`demand`/`vmodel_check` -- no generic schema-validation entry point yet) or a pure-Python `frob.graph` equivalent; needs its own design pass before extracting, so filed as a follow-up rather than attempted in this same land. |
| `runs_last`, `scope`, `milestone`, evidence, lease fields and their pydantic validators | TICKET-SPECIFIC | Plain field validation with no graph shape (a string pattern, a semver-looking value, a glob) -- the "64 references" count picks up `parent`/`blocked_by` field DECLARATIONS on `Ticket` itself, most of which are the typed-id fields the `_validate_parent` row above already covers; the rest are unrelated fields whose names happen to contain a matched substring (e.g. `evidence_scope` matching `scope`). |

### `src/frob/tickets/_store.py` (28 graph-shaped references)

| Concern | Verdict | Reasoning |
|---|---|---|
| In-memory index construction (`TicketQueue.tickets`, id-to-ticket lookup) | TICKET-SPECIFIC | A flat id-keyed map, not a graph structure -- it is the LOOKUP TABLE the graph-shaped concerns above (in `_evidence.py`/`_doable.py`/`_milestone.py`) all consult to turn an id back into a `Ticket`, but building it is no different from any other repo's primary-key index. |
| Ledger file I/O, archive/active split, `frob:ticket`-directive cross-referencing | TICKET-SPECIFIC | File-format and persistence concerns; the "28 references" count is dominated by `parent`/`blocked_by` appearing in docstrings and comments discussing the fields this module PERSISTS, not graph algorithms this module RUNS. |

### `src/frob/tickets/_setters.py` (81 graph-shaped references)

| Concern | Verdict | Reasoning |
|---|---|---|
| Cycle refusal on `blocked_by`/`parent` mutation (a `frob ticket block`/`frob ticket set-parent` call refusing to create a cycle) | **SHARED, NOT YET EXTRACTED -- follow-up ticket T-draft-452acd80** | Cycle detection over an edge relation is the single most reusable graph primitive named in the ticket's own "LIKELY SHARED" list, and strata's own DAG-shaped declarations (dependency edges, layering) need identical cycle refusal. This is the best NEXT candidate after `blocked_by` transitive resolution above, since a cycle check over `blocked_by` naturally follows from having already extracted that edge relation's closure walk. |
| The 81-count's remainder: field-mutation guards for `runs_last`, `scope`, lease fields, state-transition legality | TICKET-SPECIFIC | Mutation-time business rules (can this transition happen given the CURRENT state machine), not graph algorithms; most of the count is `parent`/`blocked_by` appearing as one of several fields a single setter function validates together, not a graph walk. |

### `src/frob/tickets/_scope.py` (4 graph-shaped references)

| Concern | Verdict | Reasoning |
|---|---|---|
| Scope-glob-to-doc/code closure (`docs/modules/graph.md#scope-closure-t-0998`) | TICKET-SPECIFIC | Already documented as consulting `frob.graph.affects`'s existing shared machinery (T-0998) rather than duplicating a walk -- this module is a CONSUMER of the shared graph kernel already, not a second implementation of one. The 4 references are `affects()`/`closure` calls into that existing shared code, not duplicated logic to extract. |

## Extraction status

| # | Concern | Status |
|---|---|---|
| 1 | Parent/child any-depth descendants walk | **DONE, this leaf** -- `frob.graph._hierarchy.children_by_parent_id`/`descendant_ids`, `frob.gates._milestone` and `frob.tickets._evidence._open_descendant_ids` rerouted onto it |
| 2 | `blocked_by` transitive resolution | Follow-up ticket filed: T-draft-5d5c1eb2 |
| 3 | Cycle refusal over `blocked_by`/`parent` mutation | Follow-up ticket filed: T-draft-452acd80 |
| 4 | Typed-id / dangling-reference construction-time refusal (`_validate_parent`) | Follow-up ticket filed: T-draft-e7434c27, needs its own design pass first (see `_models.py` row above) |

Each follow-up is filed as its OWN ticket rather than bundled, per this
ticket's own METHOD section: "DO NOT extract several concerns in one
land. The value of this approach is that each step is individually
revertible."
