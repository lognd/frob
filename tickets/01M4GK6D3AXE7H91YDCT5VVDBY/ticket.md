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
updated = "2026-10-09T15:24:53Z"
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
+++

Revision 2 of docs/design/grmb-planning.md from the R1 synthesis (notes/research/grmb-r1-synthesis.md on ticket ~19SEHXJ): apply change list C1-C36 and record the owner decisions below as decision rows. Then write the mockup corpus (synthesis section 6.1 domains and 6.2 stress cases) as fixtures with expected findings, and list what the corpus breaks for research cycle R2 (section 6.3).

Owner decisions 2026-10-09:
- D1 operators: keep the mockup symbols -> => -|> -?> as the one spelling, no alias dialect; P0 think-aloud check before freeze.
- D2 catch-all: `_` (hides, Warn) plus `unknown` (legal only when every known variant has an arm; warns when a new variant lands on it); outcome sets `closed` by default, `open` for externally owned outcomes.
- D3 goal groups: default `all`, plus `one_of { ... }` with an `exclusive` flag; no AND/OR formulas.
- D5 strictness: Lean-style `sorry` is the primitive (owner: "maybe we do a LEAN thing of sorry"): `sorry [because=...] [ticket=...] [until=...]` is legal wherever a hole is (arm body, chain element, realization, goal leaf, outcome variant, whole entity body); it checks with a warning, taints every dependent entity, and `grimble status --sorry` (like Lean #print axioms) lists every entity that transitively rests on a sorry; release profiles forbid reachable sorry. Replaces the synthesis's `todo` hole (C8) and the scoped draft marker (C9); a `draft` marker is NOT adopted now; R2 decides whether sugar is needed.
Coordinator decisions (owner delegated, recommendations taken): D4 actor kind `external` with a quick-fix from `system`; D6 keep GRL for grimble's rule language, write "grimble rule language" in grmb-facing docs, record the ITU-T Z.151 clash; D7 no new decision entity yet, reuse vmodel kind decision, revisit in R2 if the corpus loses alternatives; D8 approval gating only for opt-in top tier, default off.
