# The .grmb planning layer: semantics, binding, impl chains and ambient faults

Status: draft
Owner: grimble
Audience: rule author

Sections 12-15 of the [.grmb language specification](grmb-spec.md), moved here verbatim by ticket ~EBGD47R to keep that file under 2500 lines. The section numbers are unchanged, so a citation such as "12.8" or "14.7" names the section below. Sections 1-11 and 16-21 stay in the specification.

## 12. Planning semantics

Stated as relations over the model term, in the style of 10;
each failed condition names its rule (section 16).

### 12.1 Sets

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

### 12.2 Goals: refinement, precedence, realization, coverage

- `Req subset G x G` from `requires`; its transitive closure `Req+` must
  be irreflexive (MDL030). Consumers: `frob plan` orders tickets by it
  (blocked-by, 17.6), and `grimble status` shows it; no check reads it
  at run time (a goal is not a state).
- `Covers(s) = L intersect union { sub(g) | g in realizes(s) }`.
- EXHAUSTIVENESS: the scenarios form a match over the goal enum. A leaf
  `l` with `l not in Covers(s)` for every s is UNREALIZED: obligation
  `unrealized_goal`, rule PLAN001 (a planning obligation, not a parse
  error: the design is incomplete, not wrong). EXCEPT the leaves of a
  `one_of` group with at least one realized alternative: the group is
  satisfied (it rolls up with the join, 12.8), so its unrealized
  alternatives carry no obligation (neither PLAN001 nor PLAN005); a group
  with none realized is PLAN018 (D173).
- A scenario that realizes a goal with children covers the whole subtree
  like a binding `PlaceOrder(_)`; it hides a refinement added later, so it
  is PLAN002 (Warn), for the same reason as the `_` arm (MDL028).

### 12.3 Scenario typing

Let `e` range over chain elements. `Out(e)` is the step's outcome for a
step element and `Out(include s') = Eok(s') + E(s')` for an include
(12.4), where `Eok(s')` is `{ ok }` when some path of s' ends `end ok`,
else empty. A `sorry` element has `Out = Unknown` and adds no `Succ` pair
and no step use. A `sorry` element or terminal makes `E(s)` Unknown only
when `F(s)` is undeclared (a declared `fails with` bounds the hole,
12.4), and a terminal makes `Eok(s)` Unknown when no other path ends `end
ok`. An element with `Out = Unknown` (a `sorry` element, or an include of
a sorry-bodied scenario or of one whose `E` or `Eok` is Unknown) makes
every rule reading its outcome or a pair derived from it Unresolved at
that subject: MDL024, MDL022 after it, MDL023, MDL025 on the pairs it
collects and the handle arms over them, PLAN006 on its pairs, and
PLAN016, AMB004 on a retry targeting it; the set is Unknown as a whole
(D196, D197). A PAIR is `(e, v)` with `v in Out(e)`; patterns match
pairs.

Operators:

| Token | Meaning | Condition (else MDL024) | Effect | Rust / Zig analogue |
|---|---|---|---|---|
| `e -> c` | sequence | `Out(e) = { ok }` | none | plain call |
| `e -!> c` | continue on `ok`, collect the rest | `ok in Out(e)` | `Col += { (e, v) : v in Out(e) \ { ok } }` | `?` / `try` with an inferred error-set union |
| `e => { arms }` | immediate exhaustive match | every `v in Out(e)` matched (MDL022); every arm reachable (MDL025) | arms are typed recursively; nothing is collected by the match itself | `match` / `switch` |
| `handle { arms }` | end-of-scenario exhaustive match | 12.4 | | `catch \|e\| switch (e)` |
| `fails with { ... }` | declared error set | 12.4 | propagation | function returning `!T` / `Result` |
| `include s` | invoke a scenario as a step | include graph acyclic (MDL026) | `Out = Eok(s) + E(s)` | UML include, a call |
| `end ok`, `end err(v)` | terminal | `v in F(s)` if declared (MDL023) | adds to the ending set | `return` |
| `retry [e] max N [within T] [else c]` | bounded loop | 12.5 (MDL027) | | OTP restart intensity (E34) |

Arm matching. The arm for pair `(e, v)` in a `=>` block or a `handle`
is the most specific arm whose pattern matches it: a `pair` (`e.v`,
where `e` is written exactly as a chain element names the step or
included scenario, `customer.pays.declined`, and resolves by 5.3) beats
`v` beats `_`. A `pair` is the ONE spelling of a step-qualified variant:
in patterns, after `verified_by ... for`, and in arm anchors; `grimble
fmt` prints the shortest step reference that resolves (D172). Two arms of equal specificity matching one pair, and an arm that
matches no pair of the block's domain (an unknown variant, a variant not
collected, or one always taken by a more specific arm), are MDL025. Arm
order carries no meaning, so `grimble fmt` may sort arms (section 9). A
`_` arm is accepted and is MDL028 (Warn): it hides a variant added later,
which is exactly the design change this layer exists to propagate.

Chains are typed in one of two contexts: the MAIN chain and the arm
chains of `=>` blocks reachable from it collect into `Col(s)`; HANDLE arm
chains collect into `Colh(s)`.

### 12.4 Error sets, handle and propagation

- If `F(s)` is declared, the error set `E(s) = F(s)` and every
  `end err(v)` in s needs `v in F(s)` (MDL023). If undeclared,
  `E(s) = { v | end err(v) occurs in s }` plus Unknown when a `sorry`
  element or terminal occurs (12.3), counting the implicit ends of
  12.5 (Zig's inferred error set), and nothing propagates.
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

### 12.5 Retry

`retry [e] max N [within T] [else c]` appears only as the tail of an arm
chain (MDL027 elsewhere). It is the one bounded-repeat form; the ambient
policies of 15.1 use the same `max N [within T] else` grammar (D153; OTP
restart intensity, E34).

- TARGET. Omitted, e is the DEFAULT TARGET: for a `=>` arm, the element
  the arm matched; for a handle arm, the element that produced the matched
  pair (one element, else the target must be written: MDL027). Written, e
  must be on the chain path from the start of the main chain to the
  matched element, inclusive (`=>` arm), or precede on every path each
  element that produces a pair the arm matches (handle arm); otherwise
  MDL027. A written target equal to the default is printed without it.
  10 of 12 retries in the repository target the matched element (U2).
- BOUND. `N` is a number of at least 1; `max` is required (an unbounded
  loop is MDL027). `within T` (a time quantity) bounds the whole repeat
  in time as well: the `else` runs when either bound is reached first.
  grmb does not model time (19), so `within` is checked for its type
  (MDL009) and carried to renderings and `bound` claims, not evaluated.
- MEANING. Execution resumes at e; the arm's match is evaluated again; on
  the (N+1)-th arrival at this arm the `else` chain runs instead. Without
  `else`, the default is `end err(v)` where v is the arm pattern's variant,
  and it is never spelled (`grimble fmt` drops an `else end err(v)` equal
  to it); an arm whose pattern is `_` or `unknown` has no single variant, so it
  needs an explicit `else` (MDL027).
  The default end counts toward `E(s)`.
- NO PLACEHOLDER. A chain threads no value (only the outcome flows, and
  the matcher handles it), so grmb has no `$` or `_` placeholder for "the
  element just matched": the default target is the only shorthand (D154;
  E44 shows a placeholder token is contested even where values flow).

### 12.6 Paths, start, succession, termination

- A PATH of s is a sequence of elements from the first element of the
  main chain to a terminal, following links, `=>` arms and, after a
  collecting element, the handle arm that matches the collected pair;
  `include` is one element (its inside is the included scenario's path).
- START: the first element of the main chain is a step whose owner is an
  actor, or an include of a scenario that starts that way (MDL029). The
  TRIGGER is the actor of that first step through leading includes;
  includers are never consulted (D190). A leading `sorry` element or
  include of a sorry-bodied scenario gives an Unknown trigger: MDL029 is
  Unresolved for that scenario (a whole-body `sorry` has no trigger and no
  MDL029, 15.3); PLAN007 (on an impl) is Unresolved only when its kinds
  need the timer/device clause and no scenario using the step has a known
  other trigger, which would make the Warn definite (D199).
- `Succ(s) subset St x St`: `(a, b)` when b immediately follows a on some
  path of s, through a link, into the first element of a matched arm, or
  from a collecting element into the first element of the handle arm that
  matches its pair. Retry adds `(last element of the arm, e)`. `Succ` is
  what SYS015 (13.5) and the sequence rendering (section 17.7) read.
- TERMINATION: the grammar forces every chain to end in a terminal or a
  `=>` block, retries are bounded and the include graph is acyclic
  (MDL026), so every path is finite. MDL026 also reports a chain left
  unterminated by error recovery (a `hole`).

### 12.7 Pages

`Reach = { p | some From-path from a page in Entry reaches p }`. For an
impl clause `on page x`, `Path(x) = { p in Reach | x is reachable
from p by From }`, the pages on some navigation path from an entry to x.
`x not in Reach` is PLAN008 (Warn). The requirement is transitive: the
impl is `bound` only when every page in `Path(x)` is bound (12.8). This is
the mockup's "transitively requires home page, order browser".

### 12.8 Status

DESIGN STATUS is computed per planning entity in the order `declared <
bound < covered` (D151), from the `lo` of the selector answers (6.4); the
same computation over `hi` gives the high status. They differ only where a
selector is May or Unknown, and the JSON carries both as `status`
and `status_hi` (17.1).

- impl and page. `bound` iff the entity has at least one realization
  clause or waypoint (a flat impl is a one-waypoint chain, 14.1), every
  realization or waypoint resolves (a selector non-empty; a `route` or
  `topic` name when the adapter matches at least one site, Unknown
  otherwise, which lands in the high status only; D183), and (impl) every
  page in `Path(x)` of each `on page x` is bound. `covered` iff bound and
  it has OWN EVIDENCE (defined below).
- step use. `Impl(st, s)` is the specific impl, else the `for *` impl,
  else none (status `declared`).
- scenario. The meet of `status(Impl(st, s))` over the steps it uses and
  of every scenario it includes; over no step use and no include it is
  `declared` (the whole-body `sorry` and any all-`sorry` chain, D199);
  `covered` also needs OWN EVIDENCE.
- goal. A leaf: the meet over scenarios that cover it (none: `declared`),
  capped at `bound` without OWN EVIDENCE. An inner goal: the meet over its
  children and the same cap, except that a `one_of` group (exclusive or
  not) rolls up with the JOIN, "any one alternative holds" (D162, E29).
- system and actor: no status; rollup counts only.

`covered` means "verification is bound". OWN EVIDENCE is the set of the
entity's Evidence rows (8.3): one per test unit a `verified_by` selects
or a `frob:tests` names it on, one per `manual` clause, one unit counted
once; a `planned` clause adds none (D200, D202); "has OWN EVIDENCE" means
non-empty. grimble never runs tests (D130); only frob's overlay (17.3)
says `verified`: `covered` and every row passes (D201), verdicts `pass
fail inconclusive error` (SysML, E25) and `not-run`. A test row's verdict
is its latest frob record (frob/tickets.md 9), `inconclusive` when the records
in its WINDOW disagree (flaky, PM049): those whose stored entity
`body_digest` (frob stores the `grimble graph --json` value,
shared/sibling-contract.md 3.7, on each record) equals the current one, and
whose commit is the newest first-parent commit from HEAD that changed the
test unit's file or a descendant of it (a commit outside HEAD's history
is outside the WINDOW). An entity's "semantic digest" (PLAN022, PLAN052)
is that `body_digest` (D206, D207). Status: the record field is frob work
in ticket ~AMNDCCT; a record without it is outside every WINDOW and never
makes PM048's digests "differ".
A `manual` row instead passes when a passed attestation on a live ticket implementing the entity
or a design ancestor (PM037) carries its anchor
`kind/full-name/verified_by[i]` (9.1) as a fact, else `not-run` (D202).
Status: frob accepts that fact shape in ticket ~AMNDCCT; until then every
`manual` row is `not-run` (D203).

### 12.9 The Laws (rev 2, C10)

The gradual guarantee: adding a hole never turns a Pass elsewhere into a
Fail, and removing a `sorry` never does so without a named finding.

1. A model with holes never reports a vacuous Pass: unresolved subjects
   are Unresolved, not Pass (corpus f15).
2. Each level is optional (C1): a goals-only model reports PLAN001 and
   PLAN005, an impls-only model PLAN013, never an Error.
3. One finding per root cause (C11).
4. A rule that ships Advisory (C35) cannot fail the default gate.
5. Incremental re-check cost is bounded by the touched set (C33).

## 13. Planning binding, verification and the V-model

### 13.1 Binding

Realization clauses and waypoints add rows to B (10.2, binding.md 1.2)
with role `realization` and the clause's or waypoint's KIND (D183); `verified_by` adds rows with
role `verified_by`. Sources and ranks are those of 10.3 (a
`grimble:binds` directive naming an impl is rank 1). Nothing else changes:
an empty realization selector is SYS004, a changed bound body SYS007, a
rename SYS008, and `grimble ack` records them.

### 13.2 verified_by and arms

`verified_by SEL;` is the Evidence relation of 8.3 with the
planning entity as subject; `frob:tests <symref>` naming a planning entity
is the same relation from the test side. With `for STEP.VARIANT` on a
scenario, the evidence covers the arms whose pattern matches that pair
(a `=>` arm or a handle arm); the arm anchors are
`scenario/S.NAME/arm[OWNER.STEP.VARIANT]` (section 9.4). Evidence for a
pair is one fact wherever it is written: a `verified_by ... for PAIR` on
the scenario or on any waypoint of an impl of that step covers the arm and
every outcome-map entry that maps to that variant. A pair with no
covering evidence is ONE PLAN006 obligation (Advisory), whose detail
names the pair, the uncovered arm and map entries (D184). An `unknown` arm is not a coverage subject (it matches no
KNOWN pair, 15.4); a `_` arm is the covering arm of every known pair no
more specific arm takes, so each such pair is a PLAN006 subject anchored
on `arm[OWNER.STEP._]` whose detail names the PAIR (D191, D196).

### 13.3 Derived V-model

Each planning entity, and each flow and contract, is a V-model artifact by
construction. This table is the ONE pairing; its level vocabulary is that
of 4.5:

| Entity | Level | Paired test level of its `verified_by` (reading) | Derived link (the surface word, D164) |
|---|---|---|---|
| goal whose parent is an actor | `requirements` | `customer_test` (acceptance; may be a demo or review, `manual`) | - |
| goal whose parent is a goal | `requirement_spec` | `customer_test_plan` | `refines` its parent goal |
| scenario | `system_spec` | `system_integration_test_plan` (system or e2e) | `realizes` each goal in `realizes` |
| flow, contract | `system_design` | `subsystem_integration_test_plan` (integration or contract test) | - |
| page | `system_design` | `subsystem_integration_test_plan` | `on_page` from each impl naming it |
| impl, waypoint | `component_design` | `component_unit_test` (unit) | `impl_for` its scenario (`for *`: each scenario using the step), `impl_of` its step |
| system, actor, step | no level (context) | - | - |

The derived links are the edges of the graph JSON (17.1) under the same
names, so one fact has one name in the source, the V-model and the
export.

The kernel's closure rules (orphan requirement, unjustified design,
untested artifact, orphan test, trace cycle; ids open, 19) run over
`vmodel` entities and these derived artifacts together. One root cause,
one finding: for a planning entity the PLAN rule is reported (PLAN001 for
an orphan requirement leaf, PLAN010 for an unjustified scenario, PLAN005
for an untested artifact) and the kernel closure finding on the same
anchor is suppressed. A `vmodel` link may target a planning entity (a
`vmodel` design decision that `decides` a scenario).

The pairing is the DEFAULT reading of the trace, not a constraint (R2
verification, I1-I12): evidence whose own scope (a unit test cited as
acceptance evidence) differs from the paired level is PLAN050 (Advisory),
never an Error. Verification OBLIGATIONS are created when a level is
written: a `verified_by` that does not resolve yet is `planned`, and a
whole-body `sorry` (15.3) stands in for the evidence until tests exist. `grimble trace` shows goal,
scenario, waypoints and code with the paired verification state per row
(`uncovered` for no row, `planned` for a planned clause, and per row a
verdict of 12.8 from frob; flaky evidence is PM049 and shows as the
verdict `inconclusive`; suspect evidence is PLAN052, not a state).

### 13.4 Location of an impl

`node(i)` is the `in node` clause if present; otherwise `owner(u)`
(6.5) when all bound identities u of the impl's realizations
have one owner, else Unknown. A declared `in node` that differs from a
Must owner of a bound identity is PLAN009 (Warn). For a step of an actor
with `in node N`, `node` is N. For a step use, `node(st, s) = node(Impl(st,
s))`, or the actor's node. With a waypoint chain (14), each waypoint has
its own node (the owner of its bound identities); `node(i)` is then the
node of the FIRST waypoint (the entry), which is what SYS015 reads between
step uses, and an `in node` clause must agree with it (PLAN009); the hops
inside the chain use the per-waypoint nodes (14.2).

### 13.5 Behaviour implies data flow (SYS015)

For every `(a, b) in Succ(s)` with `node(a, s) = X`, `node(b, s) = Y`,
both known and `X != Y`, the model must declare a `flow` from X to Y
(direction matters: the behaviour moves data from X to Y). Missing is
SYS015 (Error, P+). A pair where either node is Unknown is Unresolved,
never clean. This is where the planning layer meets the node and flow
model, and the reason an impl names its node. The brief stated this for
consecutive system steps; a human step realized by a `ui` component in a
frontend node is the same data movement, so the rule reads every step use
with a known node.

## 14. Impl chains and required waypoints

An `impl` that only binds a step to one selector says nothing about HOW
the step reaches code. Rev 2 lets an impl carry an ORDERED CHAIN of
waypoints: the path a step takes from the user-visible entry to the last
effect, across layers and languages. The chain is a claim, checked
against the code graph; it is never a second copy of the code.

### 14.1 Syntax

```
impl customer.pays for checkout {
  chain {
    ui    pay_button = "src/Pay.tsx::PayButton";
    call  post_pay   = "src/api.ts::postPay";
    route pay_route  = "POST /orders/{id}/pay";
    call  charge     = "payments/client.py::charge" {
      PaymentDeclined, 402 => declined;
      TimeoutError => timeout;
      verified_by "tests/api/test_pay.py::test_declined" for customer.pays.declined;
    }
    store orders     = "db/orders.py::save";
  }
}
```

The grammar is `impl_cl` and `waypoint` of 11.1. A chain is an ORDERED
statement list (waypoint names unique per chain, MDL008): the order of the statements is the order of the path
(the U term is an ordered group, 9.5), so no arrow is needed between
waypoints and `->` keeps its single meaning (D152). A waypoint body holds
its OUTCOME MAP, one entry `SOURCE, ... => VARIANT;` per variant, read left
to right like an arm ("this failure becomes that variant"), with `_` on
the source side as the pattern for every other producible error; and its
own `verified_by` clauses. The right-hand side is a selector, except for
the two NON-CODE kinds, whose string is a name matched by the adapter:
`route` (`"METHOD /path"`, matched to server routes) and `topic` (a
channel name, matched to publish and subscribe sites); MDL005 never
applies to them (D178). Waypoint kinds are `ui`, `route`, `call`,
`store` plus the realization kinds of 11.7 (`handler`, `isr`, `driver`,
`topic`, ...). Flat realization clauses of 11.7 stay legal: a flat impl is
a one-waypoint chain.

### 14.2 Reach semantics

Adjacent waypoints `a`, `b` must be connected by REACH: b is reachable
from a over the CODE GRAPH (call edges and framework edges such as route
dispatch, event subscription, DI), not only by a direct call. Reach over
an unresolved edge is Unresolved (opaque-cone, binding.md), never a
silent pass.

- Per-hop `verified_by`: a waypoint may carry its own evidence (8.3). A
  clause with `for STEP.VARIANT` evidences one mapped arm.
- Hop reachability is checked per pair; a break reports PLAN031 at the
  first pair that fails.
- Cross-language hops. A `route` waypoint is matched to the client
  `call` waypoints that hit it by HTTP METHOD and ROUTE (path template
  after normalising parameters), between client call sites in one
  language and server routes in another. No call edge exists between
  them, which is exactly the transport gap R3 (14.7) names.
- Cross-node hop. A hop whose two waypoints sit in different nodes X and
  Y must be carried by a declared flow from X to Y; grimble finds it from
  the waypoints' nodes, exactly as SYS015 does between step uses (13.5),
  and a missing flow is SYS015. The hop never names the flow (the
  pre-cycle-1 `via FLOW` was never parsed and is MDL000): naming it
  restated what the model already says (Structurizr requires behaviour to
  instance declared relations without restating them, E26). When two
  flows from X to Y exist, the hop is carried by either.

### 14.3 Reuse, not new entities

Chains reuse entities and add none: ownership crossings read node `owns`
(R2), cross-node hops the `flow` found between the nodes (SYS015), effect
waypoints the `may` grants (CAP rules), payload types contracts, trust
crossings boundaries (R6), per-hop evidence `verified_by` (PLAN006). The
impl block owns only in-node waypoints and outcome maps: bind by
selector, never restate.

### 14.4 Outcome maps and fidelity

An outcome map entry `error type or status => variant` says which
code-level failure becomes which step variant. It is checked BOTH WAYS at the
fidelity of the binding (Exact, May, Unknown, from the error-flow facts of
ticket ~589WNWE):

- PLAN041 (Error): a PRODUCIBLE error of the waypoint's unit that no
  mapped source covers (unmapped producible error).
- PLAN042 (Warn): a mapped source the unit cannot produce, or a variant
  with no source (unproducible variant).

| Language | Error-set fidelity |
|---|---|
| Rust (closed enums) | Exact; `Box<dyn Error>`, `anyhow` Unknown; foreign non_exhaustive: Exact plus open remainder |
| Java | checked Exact upper bound; unchecked May |
| Swift, Zig | Exact (typed); untyped Unknown |
| Python, C#, Go (sentinels) | May, with a reason naming the widening cause |
| TypeScript | Unknown |
| C++ `noexcept` | an unverified claim, treated like a D121 claim |

Weak languages are NOT a tolerated gap. When a waypoint's error set
cannot be determined exactly (Python raise sets, TS throw), the check
reuses the opaque/Unresolved mechanism of binding.md: the cone is opaque
and a required Unresolved of PLAN041, anchored on the waypoint (`wp[..]`, 9.4), fails the
gate (PLAN011 stays the Advisory about a KNOWN failure no variant models;
D185). The DECLARED outcome map is the
explicit error-set claim, so every answer resting on it is CONDITIONAL
under D121 (clean in CI, Unresolved at release) until per-arm
`verified_by` tests exercise each mapped error (PLAN006, `uncovered_arm`,
13.2: one obligation per pair, however many entries map to it). A `_` source on an open set is the explicit `other` arm
(PLAN044 otherwise). Ambient types never enter an outcome map
(AMB005, 16.4).

### 14.5 `grimble trace` and pinning

`grimble trace STEP|SCENARIO` shows the DERIVED FULL PATH from goal to
scenario to waypoints to code, with the paired verification status (13.3).
The derived path is computed from the code graph, so it is longer than
the declared chain. Pinning is SUGGEST-ONLY: the tool suggests which
derived waypoints to add to a chain (the required set of 14.7), never
every hop, and a suggestion is never machine-applicable (C25).

### 14.6 File convention

Impl blocks may live anywhere in the system. The convention is a sibling
file `X.impl.grmb` next to `X.grmb`: design (goals, steps, scenarios) in
one file, code bindings in the other. `grimble fmt` does not move items;
PLAN040 (Advisory, off by default) notes an impl in a design file when a
sibling `.impl.grmb` exists.

### 14.7 Required waypoints

For each step use, the DERIVED CODE CONE is the code reached from the
step's entry up to the next step's entry or the actor's return, over call
and framework edges, across ALL routes. A chain is complete when it
contains every REQUIRED waypoint of the cone:

| Id | Required waypoint | Why |
|---|---|---|
| R1 | entry: the actor-kind specific handler (`ui` for human, `handler` for external, `isr` for device, timer callback) | where the step starts |
| R2 | ownership crossing: between two nodes that `owns` the units | architecture boundary |
| R3 | transport gap: a hop with no call edge (HTTP, RPC, queue, IPC, FFI, DB) | the edge the graph cannot see |
| R4 | effect site of a granted capability atom (`may`) | the checked side effect |
| R5 | error origin of each non-ok variant, and of any producible unmapped escaping error | outcome map anchor |
| R6 | boundary-entity crossing (trust) | security review point |
| R7 | hand-off continuity to the next step | the chain meets the next step's entry |

VERBOSITY IS A FUNCTION OF DECLARED NODE GRANULARITY: a system declared
as one node has no R2 or R3; splitting it into nodes adds exactly the
crossings between them. Coarse models stay short by construction.

## 15. Ambient faults, holes, unknown and open sets

### 15.1 Policy

Ambient-fault handling is always on; there is no pedantic profile (D147).
Every system declares ONE ambient-fault policy (AMB001 otherwise);
scenarios inherit it and may override it. A fault inside an included
scenario is handled by the policy of the OUTERMOST (triggered) scenario,
which is the one an ambient `retry` re-runs; an included scenario's own
`ambient` applies only when it is itself triggered (D192). Every scenario
counts as triggered (there is no included-only marker; an Unknown or
absent trigger, 12.6, changes nothing here), so the policies applying to
a scenario are its own override, else the system's, plus the override of
every scenario that transitively includes it (D197). There is no `ignore`
value, so no scenario skips the class. A policy may carry its own
fault-injection evidence in a body (AMB008 otherwise):

```
system web_app {
  ambient restart max 3 within 60 s else escalate {
    verified_by "tests/fault/test_restart.py";
  }
  scenario batch_export { ambient terminate; ... }
}
```

Vocabulary (the `policy` production of 11.1): `escalate`, `terminate`
(the safe default and the AMB001 quick-fix), and `retry` or `restart`
with the bounded-repeat tail `max N [within T] else POLICY` that scenario
retries share (12.5, D153). The two differ in what survives (D182): an
ambient `retry` re-runs the faulting scenario from its first SYSTEM step
with state kept (actor steps are never repeated: the event already
happened), so PLAN016 reads it and its repeated path is every system step
of every scenario it applies to (15.1: the scenarios without an override
and their includes, or the override's scenario and its includes); an ambient `restart` restarts the node or
process with state lost and re-enters at the triggering event, so PLAN016
does not read it (nothing is re-executed against kept state) and AMB009
does. This is OTP's restart intensity `MaxR` within
`MaxT` with escalation to the parent (E34). `escalate` in a scenario
hands the fault to its system's policy; `escalate` in a system's policy
hands it out of the model (to the runtime or the operator), the model's
"parent". One policy covers every ambient class; the classes (`exhausted`,
`defect`, `interrupted`, `killed`, closed and owned by grimble) are the
adapter's vocabulary for deciding what is ambient (15.2), not surface
syntax (D177).

### 15.2 Rules of the ambient class

- A `_` arm NEVER matches an ambient class; ambient arms never propagate
  into `fails with`; they travel their own path (escalation).
- The per-language adapter decides which raised types are ambient (Python
  `MemoryError`, `RecursionError` handled as ordinary only if declared,
  `KeyboardInterrupt`, `SystemExit`, `CancelledError`; Java `Error`; Rust
  panic and alloc failure; Go fatal errors). C++ `noexcept` is an
  unverified claim.
- Exhaustion that the language reports as an ordinary error (Zig
  OutOfMemory) may be a declared domain variant only when the step says so.

Idempotency is a per-STEP fact (the trailing `idempotent` of 11.5), not a
per-step policy. Containment (who restarts what) attaches to the system;
the scenario override is the reaction half. There is no per-node or
per-class override (D177).

### 15.3 `sorry` (D142)

Lean-style `sorry` with the debt keys of section 7 (`because=`, `until=`,
`ticket=` as a string, `owner=`; all optional) is the one incompleteness
primitive (E33, E53). It is legal in exactly the three positions the
grammar of 11.1 gives it: a chain element, a terminal (an arm body,
`declined => sorry because="policy TBD";`), and the whole body of a
scenario, impl or page (`impl buyer.pays for pay sorry;`, the `body`
production; actors, goal variants and steps have no `sorry` body, D197). It is NOT a
U `hole` (9.5): `grimble fmt` prints it and the MDL rules judge the text
around it (a match whose arm is a `sorry` is still checked for
exhaustiveness); only taint and `grimble status --sorry` treat it as a
hole (D180). It checks with PLAN015 (Warn; Error under a release
profile) and TAINTS every dependent entity. `grimble status --sorry` lists
the entities that transitively rest on a sorry, like Lean `#print axioms`.

A WHOLE-BODY `sorry` (`scenario s realizes g sorry;`, `impl x for s
sorry;`) stands for the body (D189): it satisfies the body's
required-clause rules (MDL026, MDL029 and MDL031 do not fire on it; it
has no trigger, so PLAN007 has no subject); the entity's design status is
`declared`; its own obligations are suppressed in favour of the one
PLAN015 (12.9 law 3): PLAN005 for a scenario, PLAN004 and PLAN005 for an
impl or page (PLAN003 and PLAN006 belong to step uses and pairs and are
not affected, D194). Its header is not a hole: `realizes` still covers
its goals (12.2; they are `declared` by the meet of 12.8 and tainted),
and PLAN002, PLAN010, PLAN027 and MDL006 run. On a scenario, a main chain
of one `sorry` terminal is the whole-body form whatever other members the
body holds (`verified_by`, `ambient` stay); fmt prints it as `sorry;`
first, encoded as in 9.5 (D196, D197). An includer types it by 12.3:
`Out(include s)` is Unknown as a whole (its `Eok` is Unknown even with
`fails with`), so MDL022-025 there are Unresolved, never a Pass (law 1);
there is no per-arm split (D198). It replaces `todo` and `draft` (C8, C9;
sugar is open, 19).

### 15.4 `_` and `unknown` (D140)

`_` hides variants (MDL028, Warn). `unknown` is legal only when every
KNOWN variant has an arm; a code-side failure that only the `unknown`
arm would receive is PLAN011 with that arm in its detail (D193). `unknown` as a lone arm is MDL032. Outcome sets are `closed`
by default and `open` for externally owned outcomes (MDL033: an `open`
match needs `unknown` or `_`).

### 15.5 Goal groups (D141)

Goal groups default to `all`; `one_of { ... }` selects one alternative,
with an `exclusive` flag (MDL034 when alternatives overlap under
`exclusive`; PLAN018 when no alternative is realized). A `one_of` group
rolls up with the join (12.8, D162). There are no AND/OR formulas.

### 15.6 Further rev 2 additions

- `non_goal NAME;` is deliberately out of scope; realizing it is PLAN027 (C23).
- Budgets are `bound` claims (4.4, D158); unproven they are CLAIM003
  (the retired PLAN024, PLAN025 are in 16.2).
- `grimble explain RULE` prints root cause and fix kinds (`suggest`, `safe`,
  `machine`; bind suggestions are never `machine`; C12, C25).
