# The .grmb planning layer

Status: DRAFT, written under ticket ~83H49E3 from the owner's mockup of
2026-10-08 and the coordinator's decisions (D124-D133 in README.md).
Owner intent: "multi-level, mirroring the design cycle getting more
specific, but with actual bindings to code/tickets and when tickets are
completed to code. Part of it is including UML concepts with Zig/Rust-like
variant handling."

Inputs: grmb-spec.md (lexical rules 2.x, names 2.7 and 5, entities 4,
selectors 6, directives 8, U encoding 9, binding 10, MDL 11),
grimble-model.md (sections 5 and 7), binding.md (the relation B and the
SYS rules), rules.md (families), sibling-contract.md 3.7 and 3.8
(entities, bindings, `grimble.graph/1`), tickets.md (the `implements`
link and close guards).

Where this file and grmb-spec.md disagree on a planning construct, this
file wins; on everything else grmb-spec.md wins. The planning layer is
ADDITIVE to language major 2 (grmb-spec 3.4): every text that was valid
before keeps its meaning (section 2.1 says how).

## 1. Purpose and the levels

grmb-spec 1 excluded runtime behaviour from the language because v1's
behaviour constructs (`scenario`, sagas, six-phase blocks) never reached
the prover. The planning layer re-admits behaviour in one checkable form:
a typed outcome per step and exhaustive handling, so that a design change
(a new failure variant) propagates like a compile error and becomes a
ticket. It does not describe timing, concurrency or state machines
(section 16).

The left arm of the V, each level more specific than the one above:

| Level | Construct | UML analogue | V-model level (grmb-spec 4.5) | Binds to |
|---|---|---|---|---|
| 0 | `system`, `actor` | system boundary, actors | (context, no level) | - |
| 1 | `goal` variant tree | use cases, include, precedence | `requirements` (top variants), `requirement_spec` (refinements) | tickets (epics) |
| 2 | `scenario` of `step`s with outcome variants | activity and sequence diagrams, alternate and exception flows | `system_spec` | tickets (stories), acceptance tests |
| 3 | `impl STEP for SCENARIO`, `page` | realization, components, navigation | `component_design` (impl), `system_design` (page) | code selectors, tickets (tasks), unit tests |
| 4 | code | - | - | symbols (binding.md) |

The right arm: every planning entity may carry `verified_by SELECTOR;`
(6.2), evaluated as the Evidence relation of grmb-spec 8.3. The V-model
level comes from the construct kind, so the kernel's closure rules apply
without hand-written `vmodel` entities (section 6.3); `vmodel` stays for
doc-anchored artifacts.

## 2. Lexical additions

### 2.1 Planning words are contextual (D125)

grmb-spec 2.6 reserves every keyword in every position, and 3.4 allows
only additions that make previously invalid text valid within a major.
Reserving `system`, `step`, `page` or `end` everywhere would break a
major-2 model that names a node `system`. So the planning words are
CONTEXTUAL, in two classes:

| Class | Words | Recognized |
|---|---|---|
| item heads | `system` `actor` `goal` `step` `scenario` `impl` `page` | at item position only (top level, inside `namespace`, inside a `system` body). An item position never started with an identifier before, so `system web_app;` was MDL000 and is now valid: additive |
| body words | `realizes` `requires` `fails` `with` `handle` `end` `ok` `err` `retry` `max` `else` `title` `verified_by` `in` `entry` `from` `_` | inside the body or header of a planning item only (no major-2 text has one) |

Inside planning items every planning word is reserved: a planning entity,
outcome variant or error name equal to one of them is MDL031 (`system`
cannot name an actor, `end` cannot name a variant, `_` cannot name
anything). Existing keywords keep their meaning where the planning
grammar reuses them (`as`, `for`, `include`, `node`, `page` as a clause
word after `requires`). Outside planning items the words are identifiers
exactly as before.

The keyword table of grmb-spec 2.6 gains a second list, the contextual
planning words, and the editor grammar generator reads both (a
contextual word is highlighted only in planning scopes).

### 2.2 Tokens

Added to the `punct` production of grmb-spec 2.2, by maximal munch:

```
punct_plan = "=>" | "-|>" | "-?>" | "*" ;
```

Conflict check against the 2.2 table: `-` alone, `>` alone, `?` and `*`
are not tokens there, so each new token starts with a character sequence
that was a lexical error (MDL000) before; `=` followed by `>` was `=` then
an error. `->` keeps its meaning and is never a prefix of a new token
(`-|>` and `-?>` differ at the second character). `|` keeps its selector
meaning: `-|>` is one token, so `a -|> b` never lexes as `a - | > b`.
`*` is a token only in the impl header (`for *`); inside a selector it
stays a glob character within a string. `_` is an `ident` lexically and a
planning word (2.1).

### 2.3 Names

The mockup's `web_app::customer` paths become dotted refs: grmb-spec 2.7
gives `::` two meanings only (root anchor, pack qualifier) and dots join
name segments. Its string names (`"place-order"`) become snake_case
identifiers: 2.7 forbids string entity names. A human label is the
`title "..."` clause. `let` bindings are dropped: every planning entity
is named and qualified names already work across files (grmb-spec 5).

## 3. Grammar (EBNF)

Over the tokens of grmb-spec 2.2 plus 2.2 here; `name`, `ref`, `qname`,
`string`, `number` and `selector` are those of grmb-spec 2.7 and 6.1;
`common` is the common clauses of grmb-spec 4 (`alias`, `renamed_from`,
`attr`, exception clauses).

```
item        = ... | plan_item ;                    (* grmb-spec items, extended *)
plan_item   = system | actor | goal | step | scenario | impl | page ;

system      = "system" name ( ";" | "{" { sys_member } "}" ) ;
sys_member  = item | title | verified_by | common ;

actor       = "actor" name ":" ident ( ";" | "{" { actor_cl } "}" ) ;
actor_cl    = "node" ref ";" | title | common ;

goal        = "goal" ref [ "as" ident ] "{" { variant } "}" ;
variant     = name [ "requires" ref { "," ref } ] ( ";" | "{" { goal_cl } "}" ) ;
goal_cl     = title | verified_by | common ;

step        = "step" step_name [ "->" outcome ] ( ";" | "{" { step_cl } "}" ) ;
step_name   = owner "." name ;
owner       = "system" | ref ;                      (* ref resolves to an actor *)
outcome     = "{" outcome_v { "," outcome_v } [ "," ] "}" ;
outcome_v   = name [ "(" ref ")" ] ;                (* ref resolves to a contract *)
step_cl     = title | common ;

scenario    = "scenario" name [ "realizes" ref { "," ref } ] [ fails ]
              "{" { sc_member } "}" ;
fails       = "fails" "with" "{" name { "," name } [ "," ] "}" ;
sc_member   = chain_stmt | handle | title | verified_by | common ;
chain_stmt  = chain ( ";" | (* empty when the chain ends with "}" *) ) ;
chain       = { elem link } tail ;
link        = "->" | "-|>" | "-?>" ;
elem        = step_ref | "include" ref ;
step_ref    = [ "::" ] [ "system" "." ] qname ;     (* resolves to a step *)
tail        = elem "=>" arms | terminal ;
terminal    = "end" "ok"
            | "end" "err" "(" name ")"
            | "retry" step_ref "max" number [ "else" chain ] ;
arms        = "{" { arm } "}" ;
arm         = pattern "->" chain_stmt ;
pattern     = "_" | qname ;                         (* one segment: a variant; more: step.variant *)
handle      = "handle" arms ;

impl        = "impl" step_ref "for" ( ref | "*" ) "{" { impl_cl } "}" ;
impl_cl     = realization | "requires" "page" ref ";" | "in" "node" ref ";"
            | title | verified_by | common ;
realization = ident [ name ] "=" selector ";" ;     (* ident: a pack realization kind *)

page        = "page" name ( ";" | "{" { page_cl } "}" ) ;
page_cl     = "entry" ";" | "from" ref { "," ref } ";" | realization
            | title | verified_by | common ;

title       = "title" string ";" ;
verified_by = "verified_by" selector [ "for" qname ] ";" ;   (* qname: step.variant, 5.3 *)
```

Notes on the productions.

- A clause starting with an identifier that is not a planning word, in an
  `impl` or `page` body, is a realization clause.
- `ok` is a name in `outcome_v` and `pattern`; it is the distinguished
  success variant. A step without `-> outcome` has outcome `{ ok }`.
- In a `chain`, the `->` of `arm` (pattern to arm chain) and the `->` link
  are the same token; position decides.
- `retry ... max` without `max` is parsed (so the message is specific)
  and reported MDL027, not MDL000.

## 4. Entities and naming

The planning layer adds seven entity kinds to the eight of grmb-spec 4:
`system`, `actor`, `goal`, `step`, `scenario`, `impl`, `page`. All live in
the one namespace of grmb-spec 5.1; anchors are `kind/full-name`
(grmb-spec 5.5): `goal/web_app.customer.place_order`.

### 4.1 system: an entity with an interior

`system NAME { ... }` declares an entity and a containment prefix, like a
`namespace` that has an identity. Items inside get the prefix `NAME.`.
More files join a system by being mounted at its name: `include
"web_app/*.grmb" as web_app;` gives the same prefix (grmb-spec 5.2 already
makes a mount prefix and a namespace one thing); a mount prefix or
namespace whose full name equals a system's full name is that system's
interior, not an MDL001 collision.

Every actor, goal, step, scenario, impl and page belongs to exactly one
system: the system whose full name is the longest proper prefix of the
item's full name. A planning item with no enclosing system is MDL031.
Architecture entities (nodes, flows, contracts) may live inside a system
interior or outside it; they do not belong to systems.

The system is also the implicit owner of reaction steps: inside the
system `S`, `system.X` names the step `S.system.X`. `system` is a
planning word, so that segment never collides with a user name.

### 4.2 actor

```
actor customer : human;
actor payments : external { node payment_api; }
```

| Field | Clause | Required | Meaning |
|---|---|---|---|
| name | `actor NAME` | yes | full name `S.NAME` |
| kind | `: KIND` | yes | from the actor-kind vocabulary: core `human`, `external`, `timer`, `device`; a pack may add kinds (D126). Unknown is MDL031 |
| node | `node REF;` | no | the node that IS this actor (typically `kind external` or a device driver node); its steps are then located in that node for SYS015 |

Actors are the only irreducible event generators (D126): every scenario
starts with an actor step (MDL029); `system` steps are reactions. The
mockup's `system` actor kind is spelled `external` because `system` is a
planning word, and `external` matches the core node kind.

### 4.3 goal: keyed variant sets

```
goal customer as action {
  browse_items;
  place_order requires browse_items;
  track_order requires place_order;
}
goal customer.place_order as path { guest; account; }
```

A `goal PATH [as KEY] { variants }` block declares a VARIANT SET at
PATH, which resolves to an actor or a goal (MDL006 otherwise). Each
variant is a goal entity with full name `PATH-full-name.VARIANT`
(`web_app.customer.place_order`). The Rust reading is `enum Customer {
BrowseItems, PlaceOrder(Path), TrackOrder }` with `enum Path { Guest,
Account }`. `as KEY` names the dimension for reports (the mockup's
`with key "action"`); it is optional.

- Several blocks on one PATH are additive (one variant set, as `extend`);
  two different KEYs on one PATH are MDL031.
- Nesting refines: a block at a goal path is an OR refinement by
  enumeration (KAOS style). LEAVES are goals with no variant set.
- `requires X` is a precondition: X must have been achieved before. X
  resolves to a goal of the same system (MDL031 across systems). The
  relation is transitive and acyclic (MDL030).
- Goals and steps under one actor share the actor's prefix; a goal and a
  step with the same name are MDL001 (goals name outcomes, steps name
  actions, so a collision is a naming smell anyway).

### 4.4 step

```
step customer.submits_cart;
step customer.enters_payment -> { ok, declined(decline_reason), timeout };
step system.queries_products -> { ok, no_item_found };
```

A step is declared once, with its OUTCOME TYPE, and then used by any
number of scenarios. Full name: `OWNER-full-name.NAME` for an actor owner,
`S.system.NAME` for a reaction. The outcome is a finite set of variant
names, default `{ ok }`; a variant may carry a payload that is a
`contract` entity (grmb-spec 4.3): the UML class-diagram role is the
existing contract, bound to a code type, and there is no new type system.
A variant name may repeat across steps; equal names mean the same error
(Zig error-set semantics, 5.3).

The outcome is part of the step's Sig facet (section 8): adding a variant
changes the step's signature, which is exactly the change this layer
exists to propagate.

### 4.5 scenario

```
scenario checkout realizes customer.place_order {
  customer.submits_cart
    -> system.shows_total
    -> customer.enters_payment => {
         ok       -> system.confirms_order -> end ok;
         declined -> retry customer.enters_payment max 3;
         timeout  -> end err(timeout);
       }
}
```

| Field | Clause | Required | Meaning |
|---|---|---|---|
| name | `scenario NAME` | yes | full name `S.NAME` |
| realizes | `realizes G, ...` | no | goals this scenario realizes (UML realization of a use case); a scenario that realizes nothing and that no scenario includes is PLAN010 |
| fails with | `fails with { v, ... }` | no | the declared error set; collected variants listed here propagate to an including scenario instead of being handled (5.4) |
| main chain | one `chain` statement | yes, exactly one | the main success scenario with its alternates; zero or several are MDL026 and MDL031 |
| handle | `handle { arms }` | no, at most one | end-of-scenario exhaustive match over the collected set |
| verified_by | `verified_by SEL [for STEP.VARIANT];` | list | acceptance tests; with `for`, the arm(s) covering that pair (6.2) |

`scenario` is the construct name because `flow` is taken (data movement,
grmb-spec 4.2); Cockburn's "main success scenario" is the reading. v1's
unused `scenario` keyword was a different construct and stays dropped.

### 4.6 impl: a step bound to code

```
impl system.shows_total for checkout {
  handler = "api/orders.py::compute_total";
  in node backend;
  verified_by "tests/api/test_orders.py::test_total*";
}
impl customer.submits_cart for * {
  requires page order_page;
  ui order_button = "src/frontend/components/order/OrderButton.tsx::OrderButton";
}
```

| Field | Clause | Required | Meaning |
|---|---|---|---|
| step | `impl STEP` | yes | the step realized |
| target | `for SCENARIO` or `for *` | yes | one scenario, or every scenario that uses the step; a specific impl wins over `for *` for its scenario |
| realization | `KIND [NAME] = SELECTOR;` | list | KIND from the pack's realization vocabulary (`ui`, `page`, `api`, `handler`, `isr`, `driver`, `topic`, ...; never grammar, as node kinds, D127); the right-hand side is a selector (grmb-spec 6), so B, SYS004, SYS007, SYS008 and `grimble ack` apply unchanged |
| pages | `requires page P;` | list | transitive navigation requirement (5.7) |
| node | `in node N;` | no | declared location; when absent it is the owner of the bound identities (6.4) |

Full name (an entity needs one, grmb-spec 9.2 has no anonymous units):
`S.SCENARIO.OWNER.STEP` for a specific impl
(`web_app.checkout.system.shows_total`), and `S._.OWNER.STEP` for `for *`
(`_` is a planning word, so no scenario can be named `_`). An impl whose
step its target scenario never uses is MDL031.

### 4.7 page: the navigation graph

```
page home { entry; ui = "src/frontend/pages/Home.tsx::Home"; }
page catalogue { from home; ui = "src/frontend/pages/Catalogue.tsx::Catalogue"; }
page order_page { from catalogue; ui = "src/frontend/pages/Order.tsx::OrderPage"; }
```

Pages are entities so that the mockup's "transitively requires home page,
order browser" is computable: `from` edges form a navigation graph (cycles
allowed: navigation goes back), `entry` marks where a user starts. A
missing page is MDL006; reachability and the transitive requirement are
5.7. `page` is in the core vocabulary because navigation is generic
(screens on a device menu are pages too); what realizes a page is pack
vocabulary.

### 4.8 Common planning clauses

- `title "..."`: human label; Attr facet (renaming the label never makes
  the entity changed).
- `verified_by SEL [for STEP.VARIANT];`: list; on goals, scenarios,
  impls and pages. Not accepted on actors and steps (MDL000): a step is
  verified through the impls and scenarios that use it.

## 5. Semantics

Stated as relations over the model term, in the style of grmb-spec 10;
each failed condition names its rule (section 7).

### 5.1 Sets

- `Sys`, `Act` with `kind : Act -> ActorKinds`.
- `G`, the goals, with `parent : G -> Act + G`; `sub(g)` is g and its
  descendants; `L = { g in G | no variant set at g }` are the leaves.
- `St`, the steps, with `owner : St -> Act + {system}` and
  `Out : St -> P(V)`, a non-empty finite set of variant names; `ok in V`
  is distinguished.
- `Sc`, the scenarios, with `realizes : Sc -> P(G)` and
  `F : Sc -> P(V) + {undeclared}`.
- `Im`, the impls, `Im subset St x (Sc + {*})`.
- `Pg`, the pages, with `Entry subset Pg` and `From subset Pg x Pg`
  (`(a, b)` when `page b { from a; }`).

### 5.2 Goals: refinement, precedence, realization, coverage

- `Req subset G x G` from `requires`; its transitive closure `Req+` must
  be irreflexive (MDL030). Consumers: `frob plan` orders tickets by it
  (blocked-by, 10.5), and `grimble status` shows it; no check reads it
  at run time (a goal is not a state).
- `Covers(s) = L intersect union { sub(g) | g in realizes(s) }`.
- EXHAUSTIVENESS: the scenarios form a match over the goal enum. A leaf
  `l` with `l not in Covers(s)` for every s is UNREALIZED: obligation
  `unrealized_goal`, rule PLAN001 (a planning obligation, not a parse
  error: the design is incomplete, not wrong).
- A scenario that realizes a goal with children covers the whole subtree
  like a binding `PlaceOrder(_)`; it hides a refinement added later, so it
  is PLAN002 (Warn), for the same reason as the `_` arm (MDL028).

### 5.3 Scenario typing

Let `e` range over chain elements. `Out(e)` is the step's outcome for a
step element and `Out(include s') = Eok(s') + E(s')` for an include
(5.4), where `Eok(s')` is `{ ok }` when some path of s' ends `end ok`,
else empty. A PAIR is `(e, v)` with `v in Out(e)`; patterns match pairs.

Operators:

| Token | Meaning | Condition (else MDL024) | Effect | Rust / Zig analogue |
|---|---|---|---|---|
| `e -> c` | sequence | `Out(e) = { ok }` | none | plain call |
| `e -\|> c` | continue on `ok`, collect the rest | `ok in Out(e)` | `Col += { (e, v) : v in Out(e) \ { ok } }` | `?` / `try` with an inferred error-set union |
| `e -?> c` | continue on `ok`, collect `none` | `Out(e) = { ok, none }` | `Col += { (e, none) }` | `?` on `Option` |
| `e => { arms }` | immediate exhaustive match | every `v in Out(e)` matched (MDL022); every arm reachable (MDL025) | arms are typed recursively; nothing is collected by the match itself | `match` / `switch` |
| `handle { arms }` | end-of-scenario exhaustive match | 5.4 | | `catch \|e\| switch (e)` |
| `fails with { ... }` | declared error set | 5.4 | propagation | function returning `!T` / `Result` |
| `include s` | invoke a scenario as a step | include graph acyclic (MDL026) | `Out = Eok(s) + E(s)` | UML include, a call |
| `end ok`, `end err(v)` | terminal | `v in F(s)` if declared (MDL023) | adds to the ending set | `return` |
| `retry e max N [else c]` | bounded loop | 5.5 (MDL027) | | - |

Arm matching. The arm for pair `(e, v)` in a `=>` block or a `handle`
is the most specific arm whose pattern matches it: `e.v` (step-qualified,
the prefix resolves to e's step or included scenario) beats `v` beats
`_`. Two arms of equal specificity matching one pair, and an arm that
matches no pair of the block's domain (an unknown variant, a variant not
collected, or one always taken by a more specific arm), are MDL025. Arm
order carries no meaning, so `grimble fmt` may sort arms (section 8). A
`_` arm is accepted and is MDL028 (Warn): it hides a variant added later,
which is exactly the design change this layer exists to propagate.

Chains are typed in one of three contexts: the MAIN chain and the arm
chains of `=>` blocks reachable from it collect into `Col(s)`; HANDLE arm
chains collect into `Colh(s)`.

### 5.4 Error sets, handle and propagation

- If `F(s)` is declared, the error set `E(s) = F(s)` and every
  `end err(v)` in s needs `v in F(s)` (MDL023). If undeclared,
  `E(s) = { v | end err(v) occurs in s }`, counting the implicit ends of
  5.5 (Zig's inferred error set), and nothing propagates.
- Every pair `(e, v) in Col(s)` is HANDLED (a handle arm matches it) or
  PROPAGATED (`F(s)` declared, `v in F(s)`, no handle arm matches);
  otherwise MDL023. A handle arm that matches no pair of `Col(s)` is
  MDL025; a scenario with handle arms and empty `Col(s)` reports MDL025
  on each arm.
- Handle arms cannot nest a handle: every pair of `Colh(s)` must
  propagate (`v in F(s)`), else MDL023. This is Zig's `try` inside a
  `catch` body.
- A propagated variant joins `E(s)`, so `Out(include s)` in an including
  scenario carries it and the includer must handle it in turn: the change
  travels up the include graph until something matches it.

### 5.5 Retry

`retry e max N [else c]` appears only as the tail of an arm chain
(MDL027 elsewhere).

- TARGET. For a `=>` arm, e is an element on the chain path from the
  start of the main chain to the matched element, inclusive. For a handle
  arm, e precedes, on every path, each element that produces a pair the
  arm matches, or is that element. Otherwise MDL027.
- BOUND. `N` is a number of at least 1; `max` is required (an unbounded
  loop is MDL027).
- MEANING. Execution resumes at e; the arm's match is evaluated again; on
  the (N+1)-th arrival at this arm the `else` chain runs instead. Without
  `else`, the default is `end err(v)` where v is the arm pattern's variant;
  an arm whose pattern is `_` needs an explicit `else` (MDL027). The
  default end counts toward `E(s)`.

### 5.6 Paths, start, succession, termination

- A PATH of s is a sequence of elements from the first element of the
  main chain to a terminal, following links, `=>` arms and, after a
  collecting element, the handle arm that matches the collected pair;
  `include` is one element (its inside is the included scenario's path).
- START: the first element of the main chain is a step whose owner is an
  actor, or an include of a scenario that starts that way (MDL029).
- `Succ(s) subset St x St`: `(a, b)` when b immediately follows a on some
  path of s, through a link, into the first element of a matched arm, or
  from a collecting element into the first element of the handle arm that
  matches its pair. Retry adds `(last element of the arm, e)`. `Succ` is
  what SYS015 (6.5) and the sequence rendering (section 11) read.
- TERMINATION: the grammar forces every chain to end in a terminal or a
  `=>` block, retries are bounded and the include graph is acyclic
  (MDL026), so every path is finite. MDL026 also reports a chain left
  unterminated by error recovery (a `hole`).

### 5.7 Pages

`Reach = { p | some From-path from a page in Entry reaches p }`. For an
impl clause `requires page x`, `Path(x) = { p in Reach | x is reachable
from p by From }`, the pages on some navigation path from an entry to x.
`x not in Reach` is PLAN008 (Warn). The requirement is transitive: the
impl is `bound` only when every page in `Path(x)` is bound (5.8). This is
the mockup's "transitively requires home page, order browser".

### 5.8 Status

Status is computed per planning entity in the order `declared < bound <
verified`, from the `lo` of the selector answers (grmb-spec 6.4); the
same computation over `hi` gives `status_hi`. They differ only where a
selector is May or Unknown, and the JSON carries both (section 9).

- impl and page. `bound` iff the entity has at least one realization
  clause, every realization selector resolves non-empty, and (impl) every
  page in `Path(x)` of each `requires page x` is bound. `verified` iff
  bound and it has at least one `verified_by` and each resolves non-empty
  to test units.
- step use. For `(st, s)`, `Impl(st, s)` is the specific impl if one
  exists, else the `for *` impl, else none (status `declared`).
- scenario. The meet of `status(Impl(st, s))` over the steps it uses and,
  for `verified`, its own non-empty `verified_by`. Includes contribute the
  included scenario's status.
- goal. A leaf: the meet over scenarios that cover it (none: `declared`),
  capped at `bound` without its own `verified_by`. An inner goal: the meet
  over its leaves and the same cap.
- system and actor: no status; rollup counts only.

`verified` here means "verification is bound": grimble never runs tests,
it reads U (D130). Whether the bound tests pass is frob's overlay
(`frob test` evidence, 10.2).

## 6. Binding, verification and the V-model

### 6.1 Binding

Realization clauses add rows to B (grmb-spec 10.2, binding.md 1.2) with
role `realization` and the clause's KIND; `verified_by` adds rows with
role `verified_by`. Sources and ranks are those of grmb-spec 10.3 (a
`grimble:binds` directive naming an impl is rank 1). Nothing else changes:
an empty realization selector is SYS004, a changed bound body SYS007, a
rename SYS008, and `grimble ack` records them.

### 6.2 verified_by and arms

`verified_by SEL;` is the Evidence relation of grmb-spec 8.3 with the
planning entity as subject; `frob:tests <symref>` naming a planning entity
is the same relation from the test side. With `for STEP.VARIANT` on a
scenario, the evidence covers the arms whose pattern matches that pair
(a `=>` arm or a handle arm); the arm anchors are
`scenario/S.NAME/arm[OWNER.STEP.VARIANT]` (section 8.1). An arm with no
covering evidence is PLAN006 (Advisory).

### 6.3 Derived V-model

Each planning entity is a V-model artifact by construction:

| Entity | Level | Paired test level of its `verified_by` | Derived links |
|---|---|---|---|
| goal whose parent is an actor | `requirements` | `customer_test` | - |
| goal whose parent is a goal | `requirement_spec` | `customer_test_plan` | `refines` its parent goal |
| scenario | `system_spec` | `system_integration_test_plan` | `refines` each goal in `realizes` |
| page | `system_design` | `subsystem_integration_test_plan` | `allocates` to the impls requiring it |
| impl | `component_design` | `component_unit_test` | `refines` its scenario (`for *`: each scenario using the step) |

The kernel's closure rules (orphan requirement, unjustified design,
untested artifact, orphan test, trace cycle; grmb-spec 14.2 question 4)
run over `vmodel` entities and these derived artifacts together. One
root cause, one finding: for a planning entity the PLAN rule is reported
(PLAN001 for an orphan requirement leaf, PLAN010 for an unjustified
scenario, PLAN005 for an untested artifact) and the kernel closure
finding on the same anchor is suppressed. A `vmodel` link may target a
planning entity (a `vmodel` design decision that `decides` a scenario);
MDL014's "target is not a vmodel" admits planning kinds.

### 6.4 Location of an impl

`node(i)` is the `in node` clause if present; otherwise `owner(u)`
(grmb-spec 6.5) when all bound identities u of the impl's realizations
have one owner, else Unknown. A declared `in node` that differs from a
Must owner of a bound identity is PLAN009 (Warn). For a step of an actor
with `node N`, `node` is N. For a step use, `node(st, s) = node(Impl(st,
s))`, or the actor's node.

### 6.5 Behaviour implies data flow (SYS015)

For every `(a, b) in Succ(s)` with `node(a, s) = X`, `node(b, s) = Y`,
both known and `X != Y`, the model must declare a `flow` from X to Y
(direction matters: the behaviour moves data from X to Y). Missing is
SYS015 (Error, P+). A pair where either node is Unknown is Unresolved,
never clean. This is where the planning layer meets the node and flow
model, and the reason an impl names its node. The brief stated this for
consecutive system steps; a human step realized by a `ui` component in a
frontend node is the same data movement, so the rule reads every step use
with a known node.

## 7. Rules

### 7.1 MDL: well-formedness (grimble-model, extends grmb-spec 11)

| Id | Alias | Severity | Condition |
|---|---|---|---|
| MDL022 | MDL-NONEXHAUSTIVE | Error | a `=>` block or a `handle` does not match some variant of its domain (names the missing variants) |
| MDL023 | MDL-UNHANDLED | Error | a collected pair neither handled nor propagated; a pair collected inside a handle arm that is not in `fails with`; `end err(v)` with v outside a declared `fails with` |
| MDL024 | MDL-FALLIBLE-SEQUENCE | Error | `->` after an element whose outcome is not `{ ok }`; `-\|>` on an outcome without `ok`; `-?>` on an outcome other than `{ ok, none }` |
| MDL025 | MDL-UNREACHABLE-ARM | Error | an arm that matches no pair of its domain (unknown variant, variant never collected, always shadowed), or two arms of equal specificity on one pair |
| MDL026 | MDL-UNTERMINATED | Error | a scenario with no main chain, a chain without a terminal (recovery), or a cycle in the scenario include graph |
| MDL027 | MDL-RETRY | Error | `retry` without `max`, `max 0`, outside an arm, target not on the path (5.5), or no `else` under a `_` arm |
| MDL028 | MDL-WILDCARD-ARM | Warn | an arm with pattern `_` |
| MDL029 | MDL-SCENARIO-START | Error | the main chain starts with a `system` step or an include of a scenario that does |
| MDL030 | MDL-REQUIRES-CYCLE | Error | a cycle in goal `requires` |
| MDL031 | MDL-PLANNING | Error | a planning item outside a system; a planning word used as a name; an unknown actor kind or realization kind; two `as` keys on one goal path; `requires` across systems; an impl for a step its scenario never uses; more than one main chain |

Unresolved references (unknown actor, undeclared step, missing page,
unknown contract payload, goal path of the wrong kind) are MDL006, as for
every other reference. The rules are P+ over the exact model term; a
subject inside a `hole` reports one Unresolved (grmb-spec 11).

Adding a variant to a step therefore produces MDL022 in every scenario
that matches that step and MDL023 in every scenario that collects it
without a covering arm, and through `fails with` in every includer: the
change propagates like a compile error, and `frob plan --from-design
--findings` can turn each one into a ticket (10.5).

### 7.2 PLAN: obligations and coverage (grimble; new family)

Family `PLAN`, ids PLAN001-PLAN099, owner grimble, crate grimble-bind
(status needs B). Registered in rules.md 3 by P2.

| Id | Alias | Severity | Condition | Obligation kind |
|---|---|---|---|---|
| PLAN001 | PLAN-UNREALIZED-GOAL | Advisory | a goal leaf covered by no scenario (5.2) | `unrealized_goal` |
| PLAN002 | PLAN-COARSE-REALIZATION | Warn | a scenario realizes a goal that has refinements (5.2) | - |
| PLAN003 | PLAN-UNIMPLEMENTED-STEP | Advisory | a step use `(st, s)` with no impl, specific or `for *` | `unimplemented_step` |
| PLAN004 | PLAN-UNBOUND-IMPL | Advisory | an impl or page with no realization clause (an empty selector is SYS004, listed as the same obligation, not reported twice) | `unbound_impl` |
| PLAN005 | PLAN-UNVERIFIED | Advisory | a goal leaf, scenario, impl or page with no `verified_by`, or whose evidence resolves empty | `unverified` |
| PLAN006 | PLAN-ARM-UNCOVERED | Advisory | an arm with no covering `verified_by ... for` (6.2) | `uncovered_arm` |
| PLAN007 | PLAN-AFFORDANCE | Warn | the impl's realization kinds do not satisfy the pack's affordance rule for the step owner's kind (core pack: `human` needs one of `ui`, `cli`, `api`; a `system` step needs `handler`; `device` needs `isr` or `driver`; `timer` needs `handler` or `isr`) | - |
| PLAN008 | PLAN-PAGE-UNREACHABLE | Warn | a page not reachable from an entry, or a `requires page` target outside `Reach` (5.7) | - |
| PLAN009 | PLAN-NODE-MISMATCH | Warn | `in node N` differs from the Must owner of a bound identity (6.4) | - |
| PLAN010 | PLAN-UNJUSTIFIED-SCENARIO | Warn | a scenario that realizes nothing and that no scenario includes | - |

Advisory obligations are the design backlog: they are expected while
designing, so they never fail the default gate; a profile (rules.md 7)
may raise them (a release profile raising PLAN001 and PLAN003 to Error is
the "design complete" gate).

### 7.3 SYS015 (grimble-bind, extends binding.md 6)

| Id | Alias | Polarity | Severity | Condition |
|---|---|---|---|---|
| SYS015 | SYS-BEHAVIOR-FLOW | P+ | Error | consecutive step uses located in different nodes with no flow in that direction (6.5); Unresolved when a node is Unknown |

### 7.4 PM: the frob join (frob-pm; ids after PM036)

| Id | Alias | Severity | Condition |
|---|---|---|---|
| PM037 | PM-UNPLANNED-OBLIGATION | Advisory | an obligation of the graph JSON whose entity has no live ticket (not outcome wont-fix, invalid or duplicate) with `implements` to the entity or to one of its design ancestors (impl, scenario, goal chain) |
| PM038 | PM-IMPLEMENTS-DECLARED | Error | a ticket reaching `done` (close or land) while an entity it `implements` has `status_hi = declared`; Unresolved when `status` and `status_hi` differ or grimble is absent. Evaluated as the close guard `design_bound` (10.4) |
| PM039 | PM-DONE-UNTOUCHED | Warn | a ticket closed `done` whose landed diff touches none of the identities bound to the entities it implements |

## 8. U encoding (extends grmb-spec 9.2)

### 8.1 Locations

Entity anchors as grmb-spec 9.1 (`step/web_app.customer.enters_payment`).
Clause anchors add, on a scenario, `chain` (the main chain), the arm
anchor `arm[OWNER.STEP.VARIANT]` for the arm that matches a pair (a
`_` arm is `arm[OWNER.STEP._]`), and `handle[VARIANT]` for handle arms.

### 8.2 Encoding table

| Construct | U term | Sort | Notes |
|---|---|---|---|
| `system S { }` | `unit(kind=system, role=declaration)`; body `group(unordered)(items, clauses)` | decl | a unit and a containment prefix (a mount at S is the same scope) |
| `actor A : K` | `unit(kind=actor)`; sig `attr(name=kind)(unit; ref(K))` | decl | `ref(K)` is a Must edge into the actor-kind vocabulary (builtin plus packs) |
| actor `node N` | `attr(name=node)(unit; ref(N))` | decl | Must edge |
| `goal P as K { }` | `unit(kind=goal, role=extension)` of P's identity; sig `attr(name=dimension)(lit(ident, K))`; body `group(unordered)(variants)` | decl | a variant set is an extension part of the actor or goal it refines (grmb-spec 9.2 multi-part), so several blocks are one identity |
| goal variant `v requires X` | `unit(kind=goal, role=declaration)`; body `apply(kind=requires)(ref(X))` | decl, exp | Must edge per ref |
| `step O.n -> { ... }` | `unit(kind=step)`; sig `attr(name=owner)(ref(O) or lit(ident, system))` and `attr(name=outcome)(group(unordered)(apply(kind=variant)(lit(ident, v); ref(C)?)...))` | decl | the outcome is Sig: a new variant changes the Sig and Contract facets |
| `scenario s realizes G fails with { }` | `unit(kind=scenario)`; sig `apply(kind=realizes)(ref(G)...)`, `attr(name=fails)(group(unordered)(lit(ident)...))` | decl | |
| main chain | `attr(name=chain)(unit; group(ordered)(elements and links))` in the body | decl | ORDERED: a chain is a sequence |
| link `->` `-\|>` `-?>` | `apply(kind=seq\|try\|opt)(left; right)` | exp | right-nested |
| step element | `ref(step)` | exp | Must edge |
| `include s` (element) | `apply(kind=invoke)(ref(s))` | exp | distinct from the file `apply(kind=include)` |
| `e => { arms }` | `apply(kind=match)(e; group(unordered)(arms))` | exp | arms unordered (5.3) |
| arm `p -> c` | `apply(kind=arm)(pattern; chain)`; pattern `lit(ident, v)`, `ref(e) . lit(ident, v)` or `lit(wildcard)` | exp | |
| `handle { }` | `attr(name=handle)(unit; group(unordered)(arms))` | decl | |
| `end ok`, `end err(v)` | `apply(kind=end)(lit(ident, ok))`, `apply(kind=end)(apply(kind=err)(lit(ident, v)))` | exp | |
| `retry e max N else c` | `apply(kind=retry)(ref(e); lit(number, N); chain?)` | exp | |
| `impl e for s` | `unit(kind=impl)`; sig `apply(kind=realize)(ref(e); ref(s) or lit(any))` | decl | full name per 4.6 |
| realization `K n = SEL` | `attr(name=realization)(unit; group(unordered)(ref(K); lit(ident, n)?; apply(kind=select)))` | decl | `ref(K)` into the realization vocabulary; May edges from `select` as grmb-spec 9.2 |
| `requires page P`, `in node N` | `attr(name=requires_page)(unit; ref(P))`, `attr(name=in_node)(unit; ref(N))` | decl | Must edges |
| `page p` | `unit(kind=page)`; `attr(name=entry)` marker; `apply(kind=from)(ref(a))` | decl | |
| `title "t"` | `attr(name=title)(unit; lit(string))` | decl | Attr facet |
| `verified_by SEL for e.v` | `attr(name=verified_by)(unit; apply(kind=select); apply(kind=arm_ref)(ref(e); lit(ident, v))?)` | decl | Body facet |

Facets: Sig holds actor kind, step owner and outcome, scenario
`realizes` and `fails`, impl step and target, goal dimension; Body holds
chains, handles, arms, realizations, `requires`, `from`, `entry`,
`verified_by`; Attr holds `title`, `attr` and exceptions. Contract is the
Sig with names erased, so a step's Contract digest is its outcome type.

### 8.3 What `grimble fmt` guarantees for planning items

grmb-spec 9.3 applies, with: planning items print after templates in the
kind order system, actor, goal, step, scenario, impl, page; chains are
NEVER reordered (ordered group) and print one link per line with the link
token leading the line, continuation indent two spaces past the first
element; arms of a `=>` or `handle` are sorted by printed pattern with
`_` last, arrows aligned; a chain that ends with `}` prints no `;`.

## 9. Graph JSON additions (grimble.graph/1, check --json)

All additions are optional keys, so the majors stay `grimble.graph/1` and
`gob.sibling/1` (sibling-contract.md 4); sibling.json gains the `$defs`
and its strict producer schema is updated by P2.

Entity records (sibling-contract.md 3.7) gain, for planning kinds:

| Key | Type | Meaning |
|---|---|---|
| `status` | `declared` `bound` `verified` | from `lo` (5.8) |
| `status_hi` | same | from `hi`; equal to `status` unless a selector is May or Unknown |
| `level` | V-model level or null | 6.3 |
| `system` | anchor | the owning system |
| `plan` | object per kind | actor `{kind, node}`; goal `{dimension, parent, leaf, requires[]}`; step `{owner, outcome: [{variant, payload}]}`; scenario `{realizes[], fails_with, error_set[], collected: [{step, variant, handled_by}]}`; impl `{step, scenario (null for *), node, pages[]}`; page `{entry, from[]}` |
| `rollup` | object | goals, scenarios, systems: `{declared, bound, verified}` counts of the leaf impls below |

Top-level `obligations`: an array of `{rule, kind, anchor, detail}`,
one per PLAN obligation of 7.2 (kinds `unrealized_goal`,
`unimplemented_step`, `unbound_impl`, `unverified`, `uncovered_arm`),
sorted by anchor. It is listed whether or not the rule is enabled, so
frob's PM037 and `plan --from-design` see the full backlog.

`edges` kinds gain `realizes` (scenario to goal), `requires` (goal to
goal), `refines` (goal to parent goal), `succ` (step to step, with
`scenario`), `invokes` (scenario to scenario), `impl_of` (impl to step),
`impl_for` (impl to scenario), `requires_page`, `navigates` (page to
page), `actor_node`, `in_node`. `bindings` roles gain `realization` (with
`realization_kind`) and `verified_by`.

## 10. The frob join

grimble never reads tickets (D28). Status is layered: grimble computes
design status and obligations (5.8, 9); frob overlays the ledger.

### 10.1 The canonical link

The ticket's `implements` link with a `design:` anchor
(`implements design:impl/web_app.checkout.system.shows_total`) is the one
link between a ticket and a planning entity; frob validates it against
`grimble graph --json` as for every grimble entity (tickets.md 3,
grimble-model.md 7). A `frob:ticket` directive on a .grmb entity
(grmb-spec 8.2) records provenance (which ticket changed that hunk) and is
never read as the link (D131): one source of truth.

### 10.2 Overlay and rollup

Per entity frob derives `planned` (some live ticket implements it),
`in-progress` (one is in progress) and `done` (every live implementing
ticket is done, at least one exists), plus the test verdict of the bound
`verified_by` tests from evidence records (`passing`, `failing`,
`unknown`). Goal progress is the rollup over its subtree (scenarios,
impls); `grimble status` shows the design tree with bound and verified
counts, and `frob board` and the GUI show the overlay and burndown per
goal (points of tickets implementing entities in the goal subtree).

### 10.3 Rules

PM037-PM039 (7.4). Drift after done (a binding that empties after its
implementing ticket closed) is not a new rule: SYS004, SYS007 and SYS008
report it on the entity, and frob shows the implementing ticket next to
the finding.

### 10.4 Close guard `design_bound`

A named guard (tickets.md 5) in the default `[tickets.guards] close` set:
a ticket reaches `done` only if every planning entity it implements has
`status_hi` at least `bound`. If `status` and `status_hi` differ, or
grimble is absent, the guard is Unresolved and the close is refused with
the remedy to resolve the selector or close with another outcome. This is
"when tickets are completed, to code": a ticket that implements an impl
cannot be done while the impl binds nothing. A repository may remove the
guard from its set (it is not an integrity guard). The guard reads
`status_hi` (definitely declared) for the Error and treats the gap as
Unresolved, never as a pass.

### 10.5 `frob plan --from-design`

A planner verb: reads `grimble graph --json`, proposes tickets, never
edits the model.

- Mapping: goal (with a variant set or a leaf of an actor) -> `epic`;
  scenario -> `story`, parent the epic of its first realized goal; impl
  -> `task`, parent the story of its scenario (a `for *` impl: parent the
  story of the first scenario by name, `relates` to the others).
- Each ticket gets `implements design:<anchor>` and an idempotency key
  equal to the anchor, so a second run proposes only what is missing.
- Scope is seeded from the file part of the impl's realization and
  `verified_by` selectors (task) or the union of its children (story).
- Acceptance is seeded: a story gets one Given/When/Then per arm of its
  scenario (given the path to the step, when it yields the variant, then
  the arm's terminal); a task gets "the realization selectors resolve and
  the `verified_by` tests pass".
- `requires` becomes `blocked-by` between the goals' epics, and a
  scenario that includes another is blocked by the included one's story.
- Tickets are created unsized and unassigned: the normal definition of
  ready and the scrum gates (pm-enforcement.md) require points before
  `cycle assign`. Default output is the proposal (JSON envelope); `--apply`
  writes through the ledger.
- `--findings` turns each MDL022, MDL023 and SYS015 finding into a task
  that implements the scenario and `fixes` the finding fingerprint: a new
  variant becomes backlog.

## 11. Renderings

`grimble graph --mermaid` emits per scenario a sequence diagram
(participants are the actors plus the nodes of `node(st, s)`, messages
are `Succ` pairs, `=>` and handle arms are `alt` blocks, `retry` a `loop`
with its bound) and an activity diagram (arms as decision branches,
terminals as final nodes), and per system a use-case diagram (actors,
goals, `requires` as precedence, `include` between scenarios). crunk may
bind `ui` realizations to its components through sibling JSON; that seam
is named here and designed elsewhere.

## 12. Worked example: the mockup's web_app

Three files. The root declares the architecture and mounts the system.

```
// design/model.grmb
grimble = "2";
module shop;
include "web_app/*.grmb" as web_app;

system web_app { title "Web shop"; }

node frontend : authenticated { owns "src/frontend/**"; }
node backend  : trusted       { owns "api/**"; }
node payments : foreign       { kind external; }

flow f_ui_api  : frontend -> backend  { label Pii; }
flow f_api_ui  : backend  -> frontend { label Internal; }
flow f_api_pay : backend  -> payments { label Secret; }
flow f_pay_api : payments -> backend  { label Internal; }

contract decline_reason { shape "api/payments.py::DeclineReason"; }
```

```
// design/web_app/goals.grmb
grimble = "2";
part of shop;

actor customer : human;
actor admin : human;
actor payment_gateway : external { node payments; }

goal customer as action {
  browse_items { title "Browse items"; verified_by "tests/e2e/browse.spec.ts"; }
  place_order requires browse_items;
  track_order requires place_order;
}
goal customer.place_order as path { guest; account; }
goal admin as action { manage_catalogue; }
```

```
// design/web_app/customer_flow.grmb
grimble = "2";
part of shop;

step customer.lands;
step customer.navigates_to_products;
step customer.adds_to_cart;
step customer.submits_cart;
step customer.enters_payment -> { ok, declined(decline_reason), timeout };
step system.shows_total;
step system.confirms_order;
step system.queries_products -> { ok, no_item_found };
step system.reserves_stock -> { ok, out_of_stock };
step system.suggests_alternatives;

scenario browse realizes customer.browse_items {
  customer.lands
    -> customer.navigates_to_products
    -> system.queries_products
    -|> customer.adds_to_cart
    -> system.reserves_stock
    -|> end ok;
  handle {
    no_item_found -> system.suggests_alternatives -> end ok;
    out_of_stock -> end err(out_of_stock);
  }
  verified_by "tests/e2e/browse.spec.ts::out_of_stock*" for system.reserves_stock.out_of_stock;
}

scenario checkout realizes customer.place_order.guest, customer.place_order.account {
  customer.submits_cart
    -> system.shows_total
    -> customer.enters_payment => {
      declined -> retry customer.enters_payment max 3;
      ok -> system.confirms_order -> end ok;
      timeout -> end err(timeout);
    }
  verified_by "tests/e2e/checkout.spec.ts";
}

impl customer.submits_cart for * {
  requires page order_page;
  ui order_button = "src/frontend/components/order/OrderButton.tsx::OrderButton";
}
impl system.shows_total for checkout {
  handler = "api/orders.py::compute_total";
  in node backend;
  verified_by "tests/api/test_orders.py::test_total*";
}

page home { entry; ui = "src/frontend/pages/Home.tsx::Home"; }
page catalogue { from home; ui = "src/frontend/pages/Catalogue.tsx::Catalogue"; }
page order_page { from catalogue; ui = "src/frontend/pages/Order.tsx::OrderPage"; }
```

What grimble reports on this model (abridged):

- Typing. `checkout`: `Out(customer.enters_payment) = { ok, declined,
  timeout }`, all three arms present, exhaustive. `retry` defaults to
  `end err(declined)` after 3 retries, so `E(checkout) = { timeout,
  declined }` (inferred). `browse`: `Col = { (queries_products,
  no_item_found), (reserves_stock, out_of_stock) }`, both handled;
  `E(browse) = { out_of_stock }`.
- If someone adds `fraud_hold` to `customer.enters_payment`, `checkout`
  gets MDL022 naming `fraud_hold`; `frob plan --from-design --findings`
  files a task implementing `scenario/web_app.checkout`.
- Obligations. PLAN001 on `web_app.customer.track_order` and
  `web_app.admin.manage_catalogue` (unrealized leaves); PLAN003 on every
  step use without an impl (for example `(system.confirms_order,
  checkout)`); PLAN005 where `verified_by` is missing; PLAN006 on
  `checkout`'s `declined` and `timeout` arms.
- Pages. The `for *` impl requires `order_page`, so `Path(order_page) =
  { home, catalogue, order_page }` and the impl is `bound` only when all
  three pages and `OrderButton` resolve.
- Flow. `(system.shows_total, customer.enters_payment)` in `checkout`
  moves backend to frontend once `enters_payment` has a `ui` impl in
  frontend: `f_api_ui` exists, no SYS015.
- Status. `impl/web_app.checkout.system.shows_total` is `verified` when
  `compute_total` and its tests resolve; `scenario/web_app.checkout` stays
  `declared` while any of its step uses has no impl.

## 13. Worked example: firmware with device and timer actors

Actors answer the mockup's firmware question without special cases: a
timer tick and a sensor interrupt are event generators exactly as a
person is.

```
// design/fw/thermostat.grmb
grimble = "2";
part of fw;

system thermostat {
  title "Heater controller";

  actor tick : timer;
  actor temp_sensor : device { node adc; }
  actor user : human;

  goal tick as job { control_loop; telemetry; }
  goal user as action { set_target; }

  step tick.fires;
  step temp_sensor.signals_sample -> { ok, crc_error, timeout };
  step system.computes_duty;
  step system.drives_heater -> { ok, overcurrent };
  step system.trips_safety;
  step system.holds_last_duty;

  scenario control_loop realizes tick.control_loop fails with { overcurrent } {
    tick.fires
      -> temp_sensor.signals_sample
      -|> system.computes_duty
      -> system.drives_heater => {
        ok -> end ok;
        overcurrent -> system.trips_safety -> end err(overcurrent);
      }
    handle {
      crc_error -> retry temp_sensor.signals_sample max 2 else system.holds_last_duty -> end ok;
      timeout -> system.holds_last_duty -> end ok;
    }
    verified_by "fw/tests/control.rs::loop_*";
    verified_by "fw/tests/control.rs::overcurrent_trips" for system.drives_heater.overcurrent;
  }

  impl tick.fires for * { isr = "fw/src/timer.c::TIM2_IRQHandler"; in node core; }
  impl temp_sensor.signals_sample for * { isr = "fw/src/adc.c::ADC_IRQHandler"; }
  impl system.computes_duty for control_loop {
    handler = "fw/src/control.rs::compute_duty";
    in node core;
    verified_by "fw/tests/control.rs::duty_*";
  }
  impl system.drives_heater for control_loop {
    driver = "fw/src/heater.rs::Heater.set_duty";
    in node hal;
  }
}

node adc  : trusted { owns "fw/src/adc.c"; }
node core : trusted { owns "fw/src/control.rs"; owns "fw/src/timer.c"; }
node hal  : trusted { owns "fw/src/heater.rs"; }
flow f_adc_core : adc -> core { label Internal; }
flow f_core_hal : core -> hal { label Internal; }
```

- `Succ(control_loop)` holds `(tick.fires, temp_sensor.signals_sample)`
  (core to adc), `(signals_sample, computes_duty)` (adc to core) and
  `(computes_duty, drives_heater)` (core to hal). The second and third
  have flows; the first has none, so SYS015 fires: either the tick
  triggers the conversion and a `core -> adc` flow is declared, or the
  design is wrong. This is the check doing its job.
- `fails with { overcurrent }` makes `E(control_loop) = { overcurrent }`;
  a supervisor scenario that `include`s `control_loop` must match
  `overcurrent`.
- PLAN007 is quiet: `timer` and `device` steps have `isr`, `system` steps
  have `handler` or `driver` (the embedded pack lists `driver` as a
  handler kind). `user.set_target` is PLAN001.

## 14. UML mapping

| UML concept | Planning construct | Note |
|---|---|---|
| system boundary (use-case diagram) | `system` | interior prefix |
| actor | `actor NAME : KIND` | the only event generators |
| use case | goal leaf | variant of the actor's goal enum |
| use-case generalization | goal refinement (`goal G as K { ... }`) | OR refinement by enumeration |
| use-case precedence | `requires` | acyclic, transitive |
| include | `include S` in a chain | outcome is the included scenario's ending set |
| extend | `=>` arms and `handle` arms | an extension point is a step variant; exhaustiveness replaces the free-form extension condition |
| realization (use case to collaboration) | `scenario ... realizes G` | |
| activity diagram | scenario chain | arms are decisions, `end` is a final node, `retry` a bounded loop |
| sequence diagram | `Succ(s)` with `node(st, s)` | lifelines are actors and nodes |
| alt / opt / loop fragments | `=>` / `-?>` with handle / `retry ... max` | |
| exception handler | `handle` | |
| signal or operation result | step outcome | Zig error set, Rust enum |
| class, data type | `contract` (grmb-spec 4.3) | payload of a variant |
| component | `node` | |
| component realization | `impl ... for` | with pack realization kinds |
| deployment | out of scope | grmb-spec 14 |
| state machine | open question 1 | |

## 15. Milestone cut

| Id | Milestone | Content | Exit |
|---|---|---|---|
| P1 | grammar and well-formedness | lexer tokens and contextual words, parser for the seven items, MDL022-MDL031 including exhaustiveness and error-set typing, U encoding of section 8, fmt rules of 8.3, conformance corpus (`plan/` directories per rule and per construct), keyword list in grimble-model, rules.md MDL range note | corpus green; both worked examples load with only the documented findings |
| P2 | binding and status | realization and `verified_by` rows in B, status and status_hi (5.8), obligations, PLAN family registration and PLAN001-PLAN005, PLAN007-PLAN010, graph JSON additions (section 9) and sibling.json `$defs` | graph JSON of the examples validates against the strict schema |
| P3 | the frob join | `implements design:` validation for planning anchors, overlay (10.2), PM037-PM039, close guard `design_bound`, `frob plan --from-design` with `--apply` and `--findings` | a plan run on the web example is idempotent; a close is refused while an impl is declared |
| P4 | verification and coverage | `verified_by ... for` arm evidence, PLAN006, derived V-model levels and links (6.3) fed to the kernel closure with suppression | closure over a mixed vmodel and planning model reports one finding per root cause |
| P5 | renderings | `grimble graph --mermaid` sequence, activity and use-case diagrams | insta snapshots of both examples |
| P6 | behaviour to architecture | `node(st, s)` (6.4), PLAN009, SYS015 | the firmware example reports exactly the SYS015 of section 13 |

Order: P1 before everything; P2 before P3, P4, P5, P6; P3 to P6 may then
run in that order or in parallel.

## 16. Refinements of the brief, and open questions

### 16.1 Where the spec forced a change to the brief

1. `web_app::customer::place_order` is `web_app.customer.place_order`:
   `::` is a root anchor or pack qualifier only (grmb-spec 2.7).
2. The words are contextual, not reserved: grmb-spec 3.4 forbids a
   change that invalidates major-2 text, and a reserved `system` would
   (D125).
3. The actor kind `system` is `external`: `system` is a planning word,
   and `external` already names the core node kind.
4. The brief's `system.queries_products -|>` followed by `->` on the next
   line is one link: `-|>` is the link to the next element.
5. `retry` without exhaustion semantics would leave a path open, so it
   gets a defined end: `else`, defaulting to `end err(v)` (5.5).
6. grimble's `verified` means verification is bound; pass or fail is
   frob's overlay, because grimble never runs tests (D130).
7. "Schema bump" for the graph JSON is additive optional keys: the major
   stays 1 (sibling-contract.md 4).
8. SYS015 reads every step use with a known node, not only system steps
   (6.5).
9. Impls need full names (grmb-spec 9.2 has no anonymous units); `for *`
   uses the `_` segment (4.6).

### 16.2 Open questions

1. State machines for firmware: a `machine` entity with states as an
   enum and transitions as steps, checked for exhaustiveness the same way.
   A later extension.
2. Whether outcomes may be generic over a payload (`result(T)` reused by
   several steps), or whether each step names its variants.
3. Whether `retry` needs a time bound (`within 30 s`) in addition to a
   count, for timers and devices where a count is not the real budget.
4. Scenario per goal refinement (one for `guest`, one for `account`)
   versus one scenario with arms on a `path` step: both are expressible;
   which one `frob plan` and the coverage report should prefer.
5. Whether an actor may be a `vmodel` stakeholder (a `requirements`
   artifact's owner), giving traceability to who asked for a goal.
6. Whether the arm-coverage rule PLAN006 should be satisfied by a test
   that only names the scenario (path inferred from the test's own
   assertions), which needs a test-side directive.
