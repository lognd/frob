+++
id = "01M4GK6D3AXE7H91YDCT5VVDBY"
title = "grmb planning rev 2: apply R1 synthesis C1-C36 and owner decisions (sorry holes, unknown/open, all/one_of), then the mockup corpus"
type = "docs"
category = "todo"
priority = "medium"
points = 8
parent = "01M4FDAD29CBF7S4EM2FKR5TXQ"
reporter = "lognd"
created = "2026-10-09T15:06:06Z"
updated = "2026-10-09T15:31:39Z"
labels = ["grimble"]
scope = ["docs/design/grmb-planning.md", "docs/design/README.md", "docs/design/grmb-spec.md", "notes/research/grmb-corpus/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4FCWY3H8CRHYYHVQ19SEHXJ"

[[acceptance]]
text = "Given the R1 synthesis and the owner decisions in this ticket, when rev 2 lands, then grmb-planning.md applies every C item or records why not, and README.md has a decision row per owner decision"
bound = false

[[acceptance]]
text = "Given synthesis section 6, when the corpus lands, then notes/research/grmb-corpus holds one mockup set per domain and one fixture per stress case, each with expected findings, plus a list of what the grammar could not express"
bound = false

[[acceptance]]
text = "Given the owner direction of 2026-10-09 (impl blocks as traced, verified, fallibility-checked chains), when rev 2 lands, then grmb-planning.md specifies impl blocks as ordered waypoint chains (ui, api route, call, store, pack kinds) using the scenario chain tokens with reach semantics; per-hop verified_by; per-waypoint outcome maps (variant <- error type/status) checked both ways (unmapped producible error, unproducible variant) at the binding's fidelity (Exact/May/Unknown, Unknown reported Unresolved); hop reachability over the code graph; cross-language hops matched by HTTP method and route between client call sites and server routes; a derived full path shown by grimble trace with suggest-only pinning (waypoints, never every hop: bind by selector, never restate); and the convention of a sibling X.impl.grmb file"
bound = false

[[acceptance]]
text = "Given a waypoint whose error set cannot be determined exactly (Python raise sets, TS throw), when the outcome-map check runs, then it reuses the existing opaque/Unresolved mechanism of binding.md (opaque-cone, required Unresolved fails the gate), and the declared outcome map acts as the explicit error-set claim: answers resting on it are conditional per D121 (clean in CI, Unresolved at release) until per-arm verified_by tests exercise each mapped error. The doc must not describe weak languages as a tolerated gap (owner 2026-10-09: grimble already throws on opaque)"
bound = false

[[acceptance]]
text = "Given the owner request 2026-10-09 to codify what must be written, when rev 2 lands, then grmb-planning.md defines the required-waypoint set over a step's derived code cone (entry to next step's entry or actor return, over call and framework edges, all routes): R1 entry (actor-kind specific handler), R2 ownership crossing between owning nodes, R3 transport gap (no call edge: HTTP/RPC/queue/IPC/FFI/DB), R4 effect site of a granted capability atom, R5 error origin of each non-ok variant and any producible unmapped escaping error, R6 boundary-entity crossing, R7 hand-off continuity to the next step; states that verbosity is a function of declared node granularity; and specifies rules missing-waypoint (Error, suggest-only fix), chain-break (Error or Unresolved on opaque), unattributed-error (Error, opaque -> Unresolved), off-path waypoint (Error) and redundant waypoint (Advisory); R2 questions recorded: branching code paths (one_of waypoint alternatives), async hand-off semantics, which atoms count as observable effects"
bound = false

[[acceptance]]
text = "Given the existing grmb entities, when rev 2 lands, then the planning layer reuses them instead of parallel constructs: ownership crossings come from node owns; a cross-node impl hop names an existing flow (-> via FLOW) whose producer/consumer/contract supply the selectors, and a hop with no flow is SYS015; effect waypoints are checked against may grants (CAP rules); outcome payload types are contract entities; trust crossings reference boundary entities; verified_by is the vmodel Evidence relation. The impl block itself owns only in-node waypoints (entry, effect sites, error origins) and outcome maps"
bound = false

[[acceptance]]
text = "Given the owner decisions of 2026-10-09, when rev 2 lands, then it specifies (a) a pedantic profile in which ambient faults (per-language class from R2-H) need one declared policy per scenario or system, and outside it ambient faults are out of scope by explicit declaration in the report; (b) the V pairing goal->acceptance, scenario->system/e2e, flow->integration/contract, waypoint->unit, with verification obligations created when a level is written (sorry allowed until tests exist) and grimble trace showing goal->scenario->waypoints->code with paired verification status; both grounded in notes/research/grmb-r2-verification.md and grmb-r2-faults.md (ticket ~5QA6P6W)"
bound = false
+++

Revision 2 of docs/design/grmb-planning.md from the R1 synthesis (notes/research/grmb-r1-synthesis.md on ticket ~19SEHXJ): apply change list C1-C36 and record the owner decisions below as decision rows. Then write the mockup corpus (synthesis section 6.1 domains and 6.2 stress cases) as fixtures with expected findings, and list what the corpus breaks for research cycle R2 (section 6.3).

Owner decisions 2026-10-09:
- D1 operators: keep the mockup symbols -> => -|> -?> as the one spelling, no alias dialect; P0 think-aloud check before freeze.
- D2 catch-all: `_` (hides, Warn) plus `unknown` (legal only when every known variant has an arm; warns when a new variant lands on it); outcome sets `closed` by default, `open` for externally owned outcomes.
- D3 goal groups: default `all`, plus `one_of { ... }` with an `exclusive` flag; no AND/OR formulas.
- D5 strictness: Lean-style `sorry` is the primitive (owner: "maybe we do a LEAN thing of sorry"): `sorry [because=...] [ticket=...] [until=...]` is legal wherever a hole is (arm body, chain element, realization, goal leaf, outcome variant, whole entity body); it checks with a warning, taints every dependent entity, and `grimble status --sorry` (like Lean #print axioms) lists every entity that transitively rests on a sorry; release profiles forbid reachable sorry. Replaces the synthesis's `todo` hole (C8) and the scoped draft marker (C9); a `draft` marker is NOT adopted now; R2 decides whether sugar is needed.
Coordinator decisions (owner delegated, recommendations taken): D4 actor kind `external` with a quick-fix from `system`; D6 keep GRL for grimble's rule language, write "grimble rule language" in grmb-facing docs, record the ITU-T Z.151 clash; D7 no new decision entity yet, reuse vmodel kind decision, revisit in R2 if the corpus loses alternatives; D8 approval gating only for opt-in top tier, default off.
