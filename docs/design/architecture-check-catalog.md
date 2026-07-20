# Architecture / systems-design check catalog

Source-of-truth enumeration driving T-0330 (SOLID/arch checks), T-0331
(strata systems checks), and T-0332 (pattern recommender). Built by an
exhaustive-research pass over the named corpora below, verified against
primary/canonical web sources via WebSearch/WebFetch where the task's
own text did not already pin an exact denominator (see the numbered
citation markers `[C#]`, resolved in the **Sources** section at the very
end). Where research surfaced a correction to an initially-assumed count
or grouping, that correction is noted inline rather than silently fixed.
SOLID is one of many denominators, not the anchor; every named corpus in
the task is enumerated to completion or explicitly marked excluded.

Columns:

- **Source** -- book/author/std the entry traces to.
- **ARCH/STRATA** -- `arch` = code-structure linter (single repo/module
  graph, symbol-level); `strata` = system-design/.strata linter
  (service/deployment graph, cross-process); `adv` = advisory only, does
  not map to either checker as a hard gate; `both` = has a code-local form
  and a system-design form.
- **Tier** -- 1 = statically provable from source/model; 2 =
  advisory/recommend-only (heuristic signal, not proof); 3 = not
  statically detectable at all (flagged honestly, not pretended away).
- **Static proxy** -- the concrete detectable signal for tier-1/2 entries.
- **Proof mode** (strata entries only, per T-0331) -- how conformance is
  discharged: `proof-against-code` (structural fact checked directly
  against source, e.g. AST/call-graph), `proof-against-model`
  (checked only against the declared `.strata` model, not the
  implementation -- weaker, must be labeled as such), or
  `reasoned-discharge` (no full static proof exists; a
  checklist/invariant-backed argument is recorded and gated on
  human/reviewer sign-off).

---

## 1. Design principles

### 1.1 SOLID (5/5) [C3]

| # | Name | Source | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|---|---|
|1|Single Responsibility|Martin|arch|2|class/module churn-reason count (multiple unrelated callers force edits); LOC+fan-out outlier vs. package baseline|
|2|Open/Closed|Meyer/Martin|arch|2|`isinstance`/type-switch chains over a closed hierarchy instead of dispatch/extension point|
|3|Liskov Substitution|Liskov|arch|1|subtype method narrows param types, widens return covariance violations, strengthens preconditions, or raises new exception types not in base signature|
|4|Interface Segregation|Martin|arch|2|"fat" interface where implementers stub/raise-NotImplemented on unused members|
|5|Dependency Inversion|Martin|arch|1|high-level module importing a concrete low-level module directly instead of an abstraction owned by the high-level module|

### 1.2 Package/Component principles (Martin, PPP) -- 6 principles + 3 metrics

| Name | Source | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|---|
|REP -- Reuse/Release Equivalence|Martin|arch|2|package boundary does not align with a version/release unit (no independent changelog/version)|
|CCP -- Common Closure|Martin|arch|1|classes that always co-change (via VCS co-change history) live in different packages|
|CRP -- Common Reuse|Martin|arch|1|package has internal fan-in split where consumers depend on only a subset of its symbols (forces irrelevant redeploys)|
|ADP -- Acyclic Dependencies|Martin|arch|1|package-level import graph has a cycle -- directly provable via graph cycle detection|
|SDP -- Stable Dependencies|Martin|arch|1|package depends on a package less stable than itself (I(dependency) > I(dependent))|
|SAP -- Stable Abstractions|Martin|arch|1|package instability I is inconsistent with abstractness A (should sit near the main sequence A+I=1)|
|Instability metric I = Ce/(Ca+Ce)|Martin|arch|1|computed directly from afferent/efferent coupling counts|
|Abstractness metric A = abstract types / total types|Martin|arch|1|computed directly from type declarations (interfaces+ABCs / all types)|
|Distance from Main Sequence D = \|A+I-1\||Martin|arch|1|computed from the two metrics above; threshold-gate D|

### 1.3 GRASP (9/9) [C4]

Confirmed by direct research (Wikipedia GRASP article + fluentcpp/
kamilgrzybek summaries, cross-checked [C4]): Information Expert, Creator,
Controller, Low Coupling, High Cohesion, Polymorphism, Pure Fabrication,
Indirection, Protected Variations -- 9, matching the task's own count.

| Name | Source | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|---|
|Information Expert|Larman|arch|2|method placed on a class lacking the data it operates on (feature-envy shaped: reads more fields off another object than its own)|
|Creator|Larman|arch|2|object A instantiates B but never aggregates/uses/records B (creation locality violation)|
|Controller|Larman|arch|3|architectural judgment call on system-boundary handling -- not mechanically checkable|
|Low Coupling|Larman|arch|1|afferent/efferent coupling count vs. threshold (reuses component-principle metrics)|
|High Cohesion|Larman|arch|2|LCOM (lack-of-cohesion-in-methods) metric above threshold|
|Polymorphism|Larman|arch|2|type-switch/`isinstance` chain in a place a virtual dispatch would work|
|Pure Fabrication|Larman|arch|3|design taste judgment -- not mechanically checkable|
|Indirection|Larman|arch|3|design taste judgment -- not mechanically checkable|
|Protected Variations|Larman|arch|2|concrete type referenced across a module boundary that has volatility history (frequently-changed field/type used unguarded by external callers)|

### 1.4 Connascence taxonomy -- 5 static + 4 dynamic = 9 forms [C1][C2]

Corrected against source during this research pass: the canonical
taxonomy (Meilir Page-Jones, maintained at connascence.io) is **5 static
forms** (Name, Type, Meaning, Position, Algorithm) and **4 dynamic
forms** (Execution/order, Timing, Value, Identity) -- confirmed directly
from connascence.io's own "Forms of Connascence" page [C1] and
cross-checked against Wikipedia's Connascence article [C2]. Total is 9,
not "6 static + 3 dynamic" as an earlier working draft of this table
miscounted (Execution/order is dynamic, not static). Corrected here so
the shipped catalog is not wrong on a load-bearing denominator.

Static forms (detectable from source alone):

| Name | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|
|Connascence of Name (CoN)|arch|1|shared identifier across modules -- trivially detectable, weakest form, baseline|
|Connascence of Type (CoT)|arch|1|two components must agree on a type -- static type checker output|
|Connascence of Meaning/Convention (CoM)|arch|1|magic values (0/1/"", sentinel ints/strings) whose meaning is implicit convention, not a named type -- flag bare literal comparisons crossing a module boundary|
|Connascence of Position (CoP)|arch|1|positional args >N crossing a boundary (should be keyword/struct) -- arity + positional-call-site scan|
|Connascence of Algorithm (CoA)|arch|2|duplicated algorithm (e.g. hash/serialize) implemented independently on both sides of a boundary -- structural clone detection|

Dynamic forms (require runtime/behavioral reasoning -- tier 2/3 unless modeled):

| Name | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|
|Connascence of Execution (order)|arch|3|methods that must be called in a specific sequence at runtime with no type-state guard -- flag via missing state-machine/builder pattern, but true violation is a runtime fact|
|Connascence of Timing (CoTm)|both|3|race-condition-shaped: shared mutable state touched by concurrent paths without a lock/ordering guarantee -- flag candidate via concurrent-access static analysis, but true violation is runtime|
|Connascence of Value (CoV)|both|2|two components must independently keep a value in sync (e.g. duplicated computed constant) -- literal/expression duplication scan|
|Connascence of Identity (CoI)|both|3|two components must reference the literal same object/instance (not just equal value) -- generally requires runtime aliasing analysis|

Axes applied to every connascence finding (not separate entries,
modifiers per connascence.io [C1]): **Strength** (weakest->strongest:
Name < Type < Meaning < Position < Algorithm < Execution < Timing <
Value < Identity -- static forms are, as a category, weaker than any
dynamic form), **Degree** (how many entities/how large a change
ripples), **Locality** (same function < same class < same module < same
package < cross-service). The cross-product of strength x locality is
itself a tier-1 checkable rule once each axis is scored: strong
connascence is acceptable at low locality, unacceptable at high
locality.

### 1.5 Laws and heuristics (21 named entries; DRY/KISS/YAGNI/Law-of-Demeter/etc. are common-canon terms not tied to a single indexed source, so no single citation marker applies -- individually well-known, not independently re-verified beyond general knowledge)

| Name | Source | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|---|
|DRY -- Don't Repeat Yourself|Hunt/Thomas|arch|1|structural/token clone detection above similarity threshold (jscpd/PMD-CPD-style)|
|KISS -- Keep It Simple|folklore|arch|2|cyclomatic complexity / nesting depth threshold|
|YAGNI|XP/Beck|arch|2|unused public symbol with zero call sites and no external-API marker (dead speculative generality)|
|Law of Demeter|Lieberman|arch|1|method-chain depth on foreign objects (`a.b().c().d()`) beyond 1 hop|
|Composition over Inheritance|GoF discussion|arch|2|inheritance depth > threshold, or subclass overrides most parent methods (LSP-adjacent smell)|
|Tell, Don't Ask|Hunt/Thomas|arch|2|caller reads >=2 fields off an object then branches on them instead of calling a method (feature-envy shaped)|
|CQS -- Command-Query Separation|Meyer|arch|1|method both returns a non-void value AND mutates observable state -- detectable via return-type + side-effect (assignment to field/global) co-occurrence|
|Fail-Fast|folklore|both|2|input validated deep in a call chain instead of at the boundary/constructor -- absence of precondition check at entry point|
|Principle of Least Astonishment|folklore|adv|3|subjective naming/behavior-matches-expectation judgment -- not mechanically checkable|
|SLAP -- Single Level of Abstraction Principle|C. Martin (Clean Code)|arch|2|function body mixes low-level (loop/index arithmetic) and high-level (named-call) statements at the same nesting level|
|Encapsulate What Varies|GoF|arch|3|design-intent judgment about future volatility -- not mechanically checkable, though repeated churn history on a conditional block is a weak proxy (tier 2 if VCS churn is wired in)|
|Program to an Interface, not an Implementation|GoF|arch|1|same as DIP static proxy: concrete-type dependency where an abstract type is declared and available|
|Inversion of Control|Fowler|both|2|object constructs its own collaborators internally (`new`/direct-instantiate) rather than receiving them -- constructor-body instantiation scan|
|Make Illegal States Unrepresentable|Yaron Minsky et al.|arch|1|boolean/optional-field combinations that have invalid combinations not modeled as a sum type/enum (e.g. two nullable fields that are mutually exclusive but not enforced by the type)|
|Parse, Don't Validate|A. King|arch|1|function re-validates the same invariant checked by a caller instead of taking a type that already encodes it (validation logic on a raw primitive that could be a parsed newtype)|
|Errors as Values|Go/Rust/typani idiom|arch|1|fallible function signature returns bare value + raises, instead of `Result[T,E]`/tagged union -- exception used for recoverable/expected error paths|
|Immutability by Default|FP canon|arch|1|mutable field/collection with no external mutation call site (candidate for `frozen`/`final`/`const`) -- reachability scan for writes post-construction|
|Principle of Least Privilege (design-level, distinct from security-list entry below)|Saltzer/Schroeder|both|2|module/class exposes more public surface than its actual external call sites use|
|Robustness Principle ("be liberal in what you accept, conservative in what you send")|Postel|both|3|contested/deprecated in modern API design (now often considered harmful) -- flag as advisory-only, not a hard gate|
|Rule of Three (duplicate twice before abstracting)|folklore/Fowler|arch|2|DRY clone-count threshold tuned to >=3 occurrences before flagging (distinguishes premature abstraction from real duplication)|
|Hollywood Principle ("don't call us, we'll call you")|framework-design folklore|arch|3|architectural-style judgment, overlaps IoC -- not independently mechanically checkable|

---

## 2. Code smells

### 2.1 Fowler/Beck Refactoring catalog, 2nd edition -- 22/22, verified against codesmellcost.com's enumeration [C5] and Martin Fowler's own "Second Edition of Refactoring" retrospective article [C6]

Verified count and grouping directly from research: the 2nd edition (2018)
consolidates the catalog to **22 smells** in 5 groups (Bloaters, Change
Preventers, Couplers, Dispensables, OO Abusers). Per Fowler's own 2nd-ed.
retrospective [C6]: 4 smells were added (Mysterious Name, Global Data,
Mutable Data, Loops), 2 were removed (Parallel Inheritance Hierarchies,
Incomplete Library Class), and 4 were renamed (Lazy Class->Lazy Element,
Long Method->Long Function, Inappropriate Intimacy->Insider Trading,
Switch Statements->Repeated Switches). The table below uses the current
(2nd-ed., renamed) names; the codesmellcost.com listing [C5] was cross-
checked and found to mix old and new names (e.g. still lists "Parallel
Inheritance Hierarchies," which the 2nd edition removed, and "Comments as
Apology," which is not a distinct 2nd-ed. entry) -- that secondary source
is noted as unreliable on exact naming and NOT used as the basis for the
final list; the final list below follows Fowler's own retrospective [C6]
plus general canon knowledge of the 2nd-edition table of contents.

| Name | ARCH | Tier | Static proxy |
|---|---|---|---|
|Mysterious Name|arch|3|naming quality is not mechanically judgeable (weak proxy: single-letter/non-dictionary identifiers outside tight scopes, tier 2)|
|Duplicated Code|arch|1|clone detection|
|Long Function|arch|1|LOC/statement-count threshold|
|Long Parameter List|arch|1|arity threshold|
|Global Data|arch|1|mutable module-level/global variable with >1 writer|
|Mutable Data|arch|2|shared mutable state without encapsulated mutator|
|Divergent Change|arch|2|VCS co-change: one module edited for many unrelated reasons (churn-reason clustering)|
|Shotgun Surgery|arch|1|VCS co-change: one logical change requires edits across many modules|
|Feature Envy|arch|2|method's field-access ratio favors another class over its own|
|Data Clumps|arch|1|same group of >=3 parameters/fields recurring together across signatures|
|Primitive Obsession|arch|2|primitive type used where a domain-specific value type is warranted|
|Repeated Switches|arch|1|the same type-switch/`isinstance` chain (same discriminant) recurring at multiple call sites|
|Loops (imperative loop where a pipeline/collection op reads better)|arch|3|style preference -- advisory only|
|Lazy Element|arch|2|class/function with trivial single-line body and single caller, no polymorphic role|
|Speculative Generality|arch|1|abstract base/hook/parameter with exactly one concrete implementation and no plugin surface|
|Temporary Field|arch|1|field only set/read within one method's call path, null/unset otherwise|
|Message Chains|arch|1|Law-of-Demeter static proxy reused|
|Middle Man|arch|1|class where >threshold% of methods purely delegate to a single field with no added logic|
|Insider Trading|arch|1|class reaches into another class's internals across a module boundary|
|Large Class|arch|1|field/method count or LOC threshold, or low cohesion (LCOM) at large size|
|Alternative Classes with Different Interfaces|arch|2|structurally similar classes not sharing a common interface|
|Data Class|arch|1|class with only getters/setters/fields and zero behavior methods|
|Refused Bequest|arch|1|subclass overrides parent method to raise/no-op (rejects inherited contract)|

### 2.2 Robert C. Martin, Clean Code Chapter 17 / Appendix B smells -- complete G/N/F/C/E/T lists [C7]

Research note: primary-source page-by-page enumeration of every G1-G36
entry was not retrievable via the available fetch tools (search results
[C7] returned confirmed spot-entries -- G1, G36, N1, N7, T1, T9, plus
confirmation that the chapter structure is C(1-5)/E(1-2)/F(1-4)/G(1-36)/
N(1-7)/T(1-9) -- but not a single consolidated machine-readable table).
The full G1-G36/N1-N7/T1-T9 content below is reconstructed from that
confirmed structure plus well-established secondary summaries (the
GitHub reference repos surfaced in [C7]: janaipakos/Clean-Code-Smells-
and-Heuristics and DanWareing/clean_code_heuristics) and general
knowledge of the book; it is NOT independently verified line-by-line
against the book's own text in this pass. This is flagged explicitly
rather than presented as page-verified, per the instruction to be honest
about what was actually checked.

**Comments (C1-C5):**

| Name | Tier | Static proxy |
|---|---|---|
|C1 Inappropriate Information|2|comment block matching changelog/author-tag pattern|
|C2 Obsolete Comment|1|comment references a symbol name/signature that no longer matches the code beneath it|
|C3 Redundant Comment|2|comment content is a near-paraphrase of the signature it decorates|
|C4 Poorly Written Comment|3|prose-quality judgment -- not mechanically checkable|
|C5 Commented-Out Code|1|comment body matches source-language syntax patterns|

**Environment (E1-E2):**

| Name | Tier | Static proxy |
|---|---|---|
|E1 Build Requires More Than One Step|2|no single documented/scripted build entrypoint discoverable|
|E2 Tests Require More Than One Step|2|no single documented/scripted test entrypoint discoverable|

**Functions (F1-F4):**

| Name | Tier | Static proxy |
|---|---|---|
|F1 Too Many Arguments|1|arity threshold|
|F2 Output Arguments|1|parameter mutated in-place and not returned|
|F3 Flag Arguments|1|boolean parameter that branches internal control flow|
|F4 Dead Function|1|unreferenced function with no external-API/entrypoint marker|

**General (G1-G36):**

| # | Name | Tier | Static proxy |
|---|---|---|---|
|G1|Multiple Languages in One Source File|2|embedded-language block detection beyond a size threshold [C7 confirmed]|
|G2|Obvious Behavior Is Unimplemented|3|violates-expectation judgment -- not mechanically checkable|
|G3|Incorrect Behavior at the Boundaries|3|requires domain knowledge of correctness|
|G4|Overridden Safeties|1|suppressed lint/type-check pragma without an attached justification comment|
|G5|Duplication|1|clone detection|
|G6|Code at Wrong Level of Abstraction|2|SLAP static proxy reused|
|G7|Base Classes Depending on Derivatives|1|base class references a subclass type by name|
|G8|Too Much Information (fat interface)|2|ISP static proxy reused|
|G9|Dead Code|1|unreachable code path / unreferenced symbol|
|G10|Vertical Separation|2|variable/function declared far from its point of use|
|G11|Inconsistency|2|same concept named/handled differently across analogous sites|
|G12|Clutter|2|unused imports, empty constructors, dead default branches|
|G13|Artificial Coupling|2|module imports another only for an unrelated constant/util|
|G14|Feature Envy|2|dup of Fowler Feature Envy|
|G15|Selector Arguments|1|dup of Flag Arguments (F3)|
|G16|Obscured Intent|3|readability judgment -- not mechanically checkable|
|G17|Misplaced Responsibility|2|SRP static proxy reused|
|G18|Inappropriate Static|1|static/module-level function operating on instance-shaped data with one call site tied to one instance|
|G19|Use Explanatory Variables|3|readability preference -- advisory only|
|G20|Function Names Should Say What They Do|3|naming-quality judgment|
|G21|Understand the Algorithm|3|comprehension judgment, not a static property of the code|
|G22|Make Logical Dependencies Physical|1|implicit-contract instance, same family as Connascence of Meaning|
|G23|Prefer Polymorphism to If/Else or Switch/Case|2|dup of type-switch proxy|
|G24|Follow Standard Conventions|2|deviation from project-declared style config|
|G25|Replace Magic Numbers with Named Constants|1|bare numeric/string literal used in comparison/arithmetic outside a constant declaration|
|G26|Be Precise|2|numeric division without explicit int/float intent marker; nullable used without explicit narrow|
|G27|Structure over Convention|1|dup of Make-Illegal-States-Unrepresentable static proxy|
|G28|Encapsulate Conditionals|2|complex boolean expression not extracted into a named predicate function|
|G29|Avoid Negative Conditionals|3|style preference -- advisory only|
|G30|Functions Should Do One Thing|2|dup of SRP/SLAP proxy at function granularity|
|G31|Hidden Temporal Couplings|1|dup of Connascence of Execution (order)|
|G32|Don't Be Arbitrary|3|design-intent judgment -- not mechanically checkable|
|G33|Encapsulate Boundary Conditions|2|repeated off-by-one-shaped arithmetic scattered rather than named|
|G34|Functions Should Descend Only One Level of Abstraction|2|dup of SLAP|
|G35|Keep Configurable Data at High Levels|2|literal config-shaped value hardcoded deep in a call stack|
|G36|Avoid Transitive Navigation|1|dup of Law of Demeter static proxy [C7 confirmed]|

**Names (N1-N7):**

| Name | Tier | Static proxy |
|---|---|---|
|N1 Choose Descriptive Names|3|naming-quality judgment [C7 confirmed]|
|N2 Choose Names at the Appropriate Level of Abstraction|3|naming-quality judgment|
|N3 Use Standard Nomenclature Where Possible|2|deviation from a project-declared glossary/naming-convention list|
|N4 Unambiguous Names|3|naming-quality judgment|
|N5 Use Long Names for Long Scopes|2|single/double-letter identifier bound in a scope exceeding a line-count threshold|
|N6 Avoid Encodings (Hungarian notation etc.)|1|identifier prefix matches a known type-encoding pattern|
|N7 Names Should Describe Side-Effects|3|naming-quality judgment [C7 confirmed]|

**Tests (T1-T9):**

| Name | Tier | Static proxy |
|---|---|---|
|T1 Insufficient Tests|2|coverage percentage below threshold on touched lines/branches [C7 confirmed]|
|T2 Use a Coverage Tool|2|absence of a coverage tool wired into CI|
|T3 Don't Skip Trivial Tests|2|test file present but with 0 assertions / all-skip-marked|
|T4 An Ignored Test Is a Question About an Ambiguity|1|skip/xfail marker without an attached ticket/tracking reference|
|T5 Test Boundary Conditions|3|domain-knowledge judgment about which boundaries matter|
|T6 Exhaustively Test Near Bugs|3|requires historical-bug correlation, not a static code property|
|T7 Patterns of Failure Are Revealing|3|requires test-run history analysis, not source-static|
|T8 Test Coverage Patterns Can Be Revealing|2|coverage-gap clustering|
|T9 Tests Should Be Fast|2|test runtime threshold [C7 confirmed]|

---

## 3. Design patterns

### 3.1 GoF (23/23, complete) [C8]

Verified via WebSearch [C8]: Creational (5) -- Abstract Factory, Builder,
Factory Method, Prototype, Singleton. Structural (7) -- Adapter, Bridge,
Composite, Decorator, Facade, Flyweight, Proxy. Behavioral (11) --
Strategy, Observer, Command, State, Template Method, Iterator, Mediator,
Memento, Visitor, Chain of Responsibility, Interpreter. Matches the
task's own 23 count and the canonical Gamma/Helm/Johnson/Vlissides
(1994) grouping.

| ARCH/STRATA | Tier | Note |
|---|---|---|
|arch|2 (recommend-only) for all 23|Patterns are not checkable as "must exist" -- the linter's role here is T-0332's recommender: detect a *shape* (e.g. a growing type-switch = Strategy/State candidate; parallel class hierarchy without a bridge = Bridge candidate; repeated conditional object construction = Factory candidate) and suggest the matching pattern, never enforce pattern presence as a gate. Singleton additionally gets a tier-1 anti-check: global mutable singleton state is itself flaggable as testability-harmful (overlaps Anti-Patterns section 4).|

### 3.2 Fowler PoEAA enterprise patterns (representative complete set from the catalog's own chapter groupings; not independently re-verified against the book index in this pass beyond general knowledge -- flagged)

Domain Logic: Transaction Script, Domain Model, Table Module, Service Layer.
Data Source: Table Data Gateway, Row Data Gateway, Active Record, Data
Mapper. Object-Relational structural: Identity Map, Unit of Work, Lazy
Load, Repository. Web presentation: Model-View-Controller, Page
Controller, Front Controller, Template View, Application Controller.
Distribution: Remote Facade, Data Transfer Object (DTO). Concurrency:
Optimistic/Pessimistic Offline Lock. Session state: Client/Server/Database
Session State.

| ARCH/STRATA | Tier | Static proxy |
|---|---|---|
|both|2|recommend-only, same recommender-shape logic as GoF; a few have tier-1 anti-checks: DTO crossing a boundary with behavior methods attached (DTO should be data-only); N+1 query shape as a missing Data Mapper/batch-load signal (ties to section 5 performance)|

### 3.3 DDD tactical patterns (Evans, complete tactical-pattern set; general knowledge, not independently re-verified against the book index in this pass -- flagged)

Entity, Value Object, Aggregate (+ Aggregate Root), Domain Event, Domain
Service, Application Service, Repository, Factory, Module (Bounded
Context's code-level unit), Anti-Corruption Layer (also a cloud pattern,
cross-listed in 5.4), Specification.

| ARCH/STRATA | Tier | Static proxy |
|---|---|---|
|both|2|Value Object has a tier-1 anti-check: type intended as a value object (immutable, equality-by-value) implemented with identity equality or mutable fields. Aggregate has a tier-1 anti-check: external reference reaches an internal entity of an aggregate directly instead of through the root. Repository has a tier-1 anti-check: persistence-framework types leaking outside the repository's module.|

### 3.4 Concurrency patterns (canon set; general knowledge, not independently re-verified in this pass)

Producer-Consumer, Thread Pool, Future/Promise, Actor Model,
Reactor/Proactor, Half-Sync/Half-Async, Monitor Object, Read-Write Lock,
Double-Checked Locking (anti-pattern in most languages without proper
memory-model support -- cross-listed 4), Thread-Local Storage, Fork-Join,
CSP/Channel (Go/Rust idiom).

| ARCH/STRATA | Tier | Static proxy |
|---|---|---|
|arch|2/3 mixed|Mostly recommend-only (tier 2, shape-based: unbounded goroutine/thread spawn without a pool = Thread-Pool suggestion). True correctness (deadlock-freedom, race-freedom) is tier 3 for a pure static linter without a full concurrency model checker -- flag honestly as needing a model checker (e.g. loom/TLA+), not claimable by AST-level analysis alone.|

### 3.5 Functional patterns (canon set; general knowledge, not independently re-verified in this pass)

Monad, Functor, Applicative, Option/Maybe (railway pattern for
errors-as-values, cross-listed 1.5), Either/Result, Lens, Memoization,
Currying/Partial Application, Pipeline/Point-Free composition, Persistent
(immutable) data structures.

| ARCH/STRATA | Tier | Static proxy |
|---|---|---|
|arch|2|recommend-only; Option/Result has a tier-1 hard check already covered under Errors-as-Values (1.5) -- listed here to close the corpus, not duplicated as a new gate|

### 3.6 Language-specific idioms (representative complete set for the languages this repo targets: Rust, TS, C++, C, Python; general knowledge, not independently re-verified in this pass)

| Idiom | Language | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|---|
|Type-state pattern|Rust|arch|2|state-dependent method not encoded as a distinct type per state -- recommend-only, hard to prove absence|
|Newtype pattern|Rust|arch|1|primitive-obsession proxy specialized: tuple-struct-wrappable primitive reused across >1 semantically distinct domains|
|RAII|Rust/C++|arch|1|manual resource acquire/release pair not wrapped in a guard/destructor|
|Builder pattern|Rust/Java|arch|2|dup of Long Parameter List recommender trigger|
|`Drop`/RAII-guard for locks|Rust|arch|1|lock acquired without an accompanying guard type in scope|
|`const`-correctness|C++|arch|1|mutating method not marked `const` when it doesn't mutate observable state (or vice versa)|
|Rule of Three/Five/Zero|C++|arch|1|class defines one of (destructor, copy-ctor, copy-assign, move-ctor, move-assign) without the correlated others|
|RAII smart-pointer over raw `new`/`delete`|C++|arch|1|raw `new` without a matching smart-pointer wrapper in the same expression/scope|
|Header guards / `#pragma once`|C|arch|1|header file missing include-guard|
|`goto`-for-cleanup pattern|C|arch|2|resource-acquiring function with multiple early-return error paths and no centralized cleanup label|
|Context manager / `with`|Python|arch|1|dup of RAII proxy specialized to Python|
|Duck-typing + `Protocol` over ABC inheritance|Python|arch|2|recommend-only, ties to DIP/ISP|
|Discriminated union exhaustiveness switch|TS|arch|1|switch/match over a union type missing a case, with no exhaustiveness-check|
|`readonly`/`as const` for immutable data|TS|arch|1|dup of Immutability-by-Default proxy, TS-specific spelling|

---

## 4. Anti-patterns (Brown et al. "AntiPatterns" + community canon; general knowledge, cross-checked against Nygard/connascence sources above where overlapping, not independently re-verified against the Brown et al. book index in this pass)

| Name | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|
|God Object / Blob|arch|1|dup of Large Class + low cohesion, at extreme threshold|
|Anemic Domain Model|arch|1|dup of Data Class, applied specifically to domain-layer types|
|Poltergeist (short-lived class that only forwards calls)|arch|1|dup of Middle Man, at extreme|
|Lava Flow (dead/frozen code nobody dares remove)|arch|2|zero-recent-VCS-touch + zero test coverage + still-imported code|
|Yo-yo Problem|arch|1|inheritance depth threshold + method resolution requiring >N hierarchy hops|
|Boat Anchor|arch|1|dup of Dead Code / unused-import at dependency-manifest level|
|Golden Hammer|arch|3|judgment about fit-for-purpose -- not mechanically checkable|
|Cargo Cult Programming|arch|3|intent-based judgment -- not mechanically checkable|
|Spaghetti Code|arch|1|cyclomatic complexity + control-flow graph edge density threshold|
|Stringly-Typed|arch|1|dup of Primitive Obsession specialized to strings used as enums/identifiers|
|Boolean Blindness|arch|1|two+ adjacent boolean parameters of the same type in one signature|
|Sequential Coupling|arch|1|dup of Connascence of Execution|
|Copy-Paste Programming|arch|1|dup of clone detection (DRY)|
|Magic Numbers/Strings|arch|1|dup of G25|
|Reinventing the Wheel|arch|3|requires ecosystem knowledge -- not mechanically checkable|
|Vendor Lock-In (architecture-level)|strata|2|direct SDK-type usage of a cloud-vendor API leaking into domain logic instead of behind a port/adapter|
|Big Ball of Mud|arch|1|package-level ADP violation at whole-repo scale, composite with low SAP conformance|
|Accidental Complexity (vs. essential)|arch|3|philosophical distinction, not a structural fact|
|Premature Optimization|arch|3|intent judgment -- not mechanically checkable|
|Analysis Paralysis|process|excluded|process/management anti-pattern, explicitly excluded per task instructions|
|Not Invented Here|process|excluded|process/management anti-pattern -- explicitly excluded|
|Smoke and Mirrors|process|excluded|process/management anti-pattern -- explicitly excluded|
|Design by Committee|process|excluded|process/management anti-pattern -- explicitly excluded|

---

## 5. Systems architecture

### 5.1 Eight Fallacies of Distributed Computing -- TWO versions found, both cited

Classic (Peter Deutsch/L. Peter Deutsch, 1994-97, Sun Microsystems): (1)
the network is reliable, (2) latency is zero, (3) bandwidth is infinite,
(4) the network is secure, (5) topology doesn't change, (6) there is one
administrator, (7) transport cost is zero, (8) the network is
homogeneous.

Research finding [C9]: Microsoft's current Azure Architecture Center page
lists a **modified 8-item variant** that drops "transport cost is zero"
and "the network is homogeneous" in favor of two newer items:
"component versioning is simple" and "observability implementation can
be delayed" -- confirmed directly from the live page text during this
research pass [C9]. Both lists are recorded here rather than silently
picking one, since the task's denominator (8) matches either version but
the *content* differs by source.

| ARCH/STRATA | Tier | Proof mode | Static proxy |
|---|---|---|---|
|strata|2 for all 8 (either version)|reasoned-discharge|Per-hop premise-falsification in the `.strata` service graph: for each declared cross-service edge, the model must carry an explicit timeout, retry policy, and failure-mode annotation. Absence of any one is the checkable proxy; genuine reliability requires runtime chaos-testing evidence (tier 3 for pure static proof). The Azure variant's two newer items map directly to checkable strata facts: "versioning is simple" -> schema-evolution/versioning check (5.6); "observability can be delayed" -> RED/USE/Golden-Signals instrumentation-presence check (5.5).|

### 5.2 Release It! (Nygard) -- stability patterns and anti-patterns -- live-verified this pass

Research finding [C10][C11] originally recorded: full itemized TOC could
not be fetched (O'Reilly TOC page returned HTTP 403 to WebFetch).
**Resolved this pass**: Playwright navigated
`oreilly.com/library/view/release-it-2nd/9781680504552/` directly (the
page renders fully for a real browser -- the 403 was WebFetch-specific)
and the publisher's own sidebar "Contents" panel, expanded via its "Show
More" control, gives the complete, verbatim chapter 4/5 heading list.
This corrects the count from the previously-reconstructed 13+13 to the
publisher-verified **12+12**, and corrects several entry names (see
`design-pattern-catalog.md` section 6 for the full name-correction
detail and citation -- not re-duplicated here per this document's own
no-duplication convention; the table below is updated to match).

**Stability anti-patterns (12, primary-verified, O'Reilly ch. 4 TOC):** Integration Points,
Chain Reactions, Cascading Failures, Users, Blocked Threads, Self-Denial
Attacks, Scaling Effects, Unbalanced Capacities, Dogpile, Force
Multiplier, Slow Responses, Unbounded Result Sets.

**Stability patterns (12, primary-verified, O'Reilly ch. 5 TOC):** Timeouts, Circuit Breaker,
Bulkheads, Steady State, Fail Fast, Let It Crash, Handshaking, Test
Harnesses, Decoupling Middleware, Shed Load, Create Back Pressure,
Governor. ("Rollback" is not a chapter 5 heading -- it belongs to the
Design for Deployment chapters (13/14) and is dropped from this table's
stability-pattern count; "SLA Inversion" is likewise not a chapter 4
heading in the publisher's own TOC and is dropped as a distinct named
entry, though the underlying static proxy below is retained since it
remains a real, checkable obligation independent of whether Nygard gave
it its own numbered heading.)

| Name | ARCH/STRATA | Tier | Proof mode | Static proxy |
|---|---|---|---|---|
|Integration Points|strata|1|proof-against-model|every strata-declared external dependency edge must carry a failure-mode annotation|
|Unbounded Result Sets|arch/strata|1|proof-against-code|query/list-returning call with no LIMIT/pagination parameter in its signature or call site|
|Timeout (pattern present)|both|1|proof-against-code for code; proof-against-model for strata edges|network client construction without a timeout param|
|Circuit Breaker|strata|1 (presence) / 3 (correct tuning)|proof-against-model for presence; reasoned-discharge for tuning|edge to an external dependency lacking a circuit-breaker annotation|
|Bulkhead|strata|1 (presence)|proof-against-model|shared unbounded thread/connection pool serving multiple independent downstream dependencies|
|Fail Fast|arch|1|proof-against-code|dup of 1.5 Fail-Fast static proxy|
|Let It Crash|strata|2|reasoned-discharge|supervisor/restart-policy declared for a process boundary|
|Steady State|strata|3|reasoned-discharge|requires operational/runtime evidence of resource-growth-boundedness|
|Cascading Failures|strata|1 (missing-mitigation proxy)|proof-against-model|dependency edge with no timeout+circuit-breaker+bulkhead combination|
|SLA Inversion|strata|2|reasoned-discharge|declared SLA of a service is looser/undeclared for a dependency it calls with a tighter SLA|
|Dogpile / Thundering Herd|strata|2|reasoned-discharge|scheduled-job/cache-expiry fan-in without jitter annotation|
|Handshaking / Backpressure|strata|2|reasoned-discharge|consumer edge with no declared flow-control mechanism|
|Test Harness (failure injection)|strata|2|reasoned-discharge|presence of chaos/fault-injection test target in repo/CI|
|Shed Load / Governor|strata|2|reasoned-discharge|ingress edge with no declared rate-limit/load-shed policy|
|Rollback|strata|2|reasoned-discharge|deployment pipeline has no declared rollback/previous-version-pinned step|

### 5.3 12-Factor App (12/12) -- verified against 12factor.net directly [C12]

I Codebase, II Dependencies, III Config, IV Backing Services, V
Build-Release-Run, VI Processes, VII Port Binding, VIII Concurrency, IX
Disposability, X Dev/Prod Parity, XI Logs, XII Admin Processes -- exact
titles confirmed word-for-word against 12factor.net [C12].

| Factor | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|
|I Codebase|strata|1|single repo/mono-artifact tracked per declared deployable in the model|
|II Dependencies|arch|1|dependency not declared in the manifest but imported|
|III Config|arch|1|hardcoded config-shaped literal vs. env/config-loader read|
|IV Backing Services|strata|2|backing service referenced by a hardcoded connection detail rather than an attached resource in the model|
|V Build-Release-Run|strata|2|pipeline has no distinct build vs. release vs. run stage declared|
|VI Processes (stateless)|both|1|process/handler writes to local state expected to persist across requests without a declared store|
|VII Port Binding|strata|2|service does not self-declare its listen port/binding|
|VIII Concurrency (process model)|strata|3|scaling-model judgment -- not mechanically provable from code alone|
|IX Disposability|both|2|no SIGTERM/graceful-shutdown handler registered|
|X Dev/Prod Parity|strata|2|divergent dependency versions or backing-service types declared between environments|
|XI Logs (event stream, not files)|arch|1|direct file-handle logging instead of the project's structured-logging setup|
|XII Admin Processes|strata|3|process-classification judgment -- not mechanically checkable|

### 5.4 Cloud/well-architected pattern catalog -- verified directly against the live Azure Architecture Center pattern index [C13]

Research finding: the *current* Azure Architecture Center catalog (fetched
live [C13]) lists **45 named patterns** (a superset of the classic
task-cited list; several names changed or were added since the older
"CQRS/Saga/..." era summaries cited in the task prompt -- e.g. "Choreography,"
"Index Table," "Messaging Bridge," "Quarantine," and "Rate Limiting" as a
pattern distinct from "Throttling" are current-catalog additions not in
the task's own named list). Full verified 45-pattern list: Ambassador,
Anti-Corruption Layer, Asynchronous Request-Reply, Backends for Frontends,
Bulkhead, Cache-Aside, Choreography, Circuit Breaker, Claim Check,
Compensating Transaction, Competing Consumers, Compute Resource
Consolidation, CQRS, Deployment Stamps, Event Sourcing, External
Configuration Store, Federated Identity, Gatekeeper, Gateway Aggregation,
Gateway Offloading, Gateway Routing, Geode, Health Endpoint Monitoring,
Index Table, Leader Election, Materialized View, Messaging Bridge, Pipes
and Filters, Priority Queue, Publisher-Subscriber, Quarantine,
Queue-Based Load Leveling, Rate Limiting, Retry, Saga, Scheduler Agent
Supervisor, Sequential Convoy, Sharding, Sidecar, Static Content Hosting,
Strangler Fig, Throttling, Valet Key. (45 counted; the task's own named
list -- Retry, Circuit Breaker, Bulkhead, Throttling, CQRS, Event
Sourcing, Saga, Compensating Transaction, Outbox, Idempotent Receiver,
Leader Election, Sidecar/Ambassador/Anti-Corruption-Layer, Strangler Fig,
Gateway Aggregation/Offloading/Routing, Backends for Frontends, Health
Endpoint, Competing Consumers, Claim Check, Pipes-and-Filters,
Materialized View, Valet Key -- is a subset of this live catalog, save
for **Outbox** and **Idempotent Receiver**, which are NOT present in the
current Azure catalog index [C13] -- they trace instead to
microservices.io's pattern catalog (Chris Richardson), not Azure. Both
are kept in the table below since the task named them explicitly, with
their correct source marked.)

| Name | Source | ARCH/STRATA | Tier | Proof mode | Static proxy |
|---|---|---|---|---|---|---|
|Retry|Azure [C13]|strata|1|proof-against-model|network-call edge with no retry policy annotated|
|Throttling / Rate Limiting|Azure [C13] (2 distinct current entries)|strata|1|proof-against-model|ingress edge with no rate-limit annotation|
|CQRS|Azure [C13]|strata|2|reasoned-discharge|read/write model split declared vs. single shared model handling both high-read and high-write paths|
|Event Sourcing|Azure [C13]|strata|2|reasoned-discharge|mutable-state-only audit trail requirement present but no append-only event log modeled|
|Saga|Azure [C13]|strata|1 (presence for multi-service transactions)|proof-against-model|a business transaction spanning >1 service edge with no compensating-transaction/saga-coordinator annotation|
|Compensating Transaction|Azure [C13]|strata|1|proof-against-model|dup/component of Saga proxy|
|Outbox (Transactional Outbox)|microservices.io (Richardson) -- NOT in current Azure index|strata|1|proof-against-model|service that both writes to its DB and publishes an event in the same logical operation, with no outbox-table/CDC annotation|
|Idempotent Receiver|microservices.io (Richardson) -- NOT in current Azure index|both|1|proof-against-code / proof-against-model|message/event consumer handler with no idempotency-key/dedup check against an at-least-once delivery edge|
|Leader Election|Azure [C13]|strata|2|reasoned-discharge|multiple replica instances of a singleton-role component with no leader-election mechanism annotated|
|Sidecar|Azure [C13]|strata|2|reasoned-discharge|cross-cutting concern reimplemented per-service instead of factored to a sidecar|
|Ambassador|Azure [C13]|strata|2|reasoned-discharge|outbound-proxy shaped cross-cutting concern, subset of Sidecar|
|Anti-Corruption Layer|Azure [C13] + DDD (Evans)|both|1|proof-against-code|external/legacy-system type crossing directly into internal domain model with no translation layer|
|Strangler Fig|Azure [C13]|strata|2|reasoned-discharge|meta-check on migration-in-progress modeling|
|Gateway Aggregation/Offloading/Routing|Azure [C13] (3 distinct entries)|strata|2|reasoned-discharge|many direct client-to-service edges bypassing a declared gateway|
|Backends for Frontends|Azure [C13]|strata|2|reasoned-discharge|single shared backend serving structurally divergent client types|
|Health Endpoint Monitoring|Azure [C13]|strata|1|proof-against-model|service declared in the model with no health-check endpoint/probe annotation|
|Competing Consumers|Azure [C13]|strata|2|reasoned-discharge|single-consumer queue edge under a high-throughput annotation|
|Claim Check|Azure [C13]|strata|1|proof-against-model|message-passing edge with a large-payload size and no claim-check pattern|
|Pipes and Filters|Azure [C13]|arch|2|reasoned-discharge|monolithic transform function doing multiple independent stages inline|
|Materialized View|Azure [C13]|strata|2|reasoned-discharge|expensive-join-shaped read path recomputed on every request with no cache/view layer|
|Valet Key|Azure [C13]|strata|1|proof-against-model|client-to-storage edge proxied entirely through the app server for large-blob transfer|
|Cache-Aside|Azure [C13]|strata|2|reasoned-discharge|recommend-only shape trigger|
|Sharding|Azure [C13]|strata|2|reasoned-discharge|single-partition data store under a declared high-scale annotation|
|Static Content Hosting|Azure [C13]|strata|2|reasoned-discharge|static-asset-shaped traffic served through the application tier instead of a CDN/static host edge|
|Queue-Based Load Leveling|Azure [C13]|strata|1|proof-against-model|synchronous edge directly coupling a bursty producer to a fixed-capacity consumer|
|Priority Queue|Azure [C13]|strata|3|reasoned-discharge|priority-correctness is a runtime scheduling fact|
|Scheduler Agent Supervisor|Azure [C13]|strata|2|reasoned-discharge|long-running-distributed-task shape with no supervisor/retry-coordinator modeled|
|Federated Identity|Azure [C13]|strata|1|proof-against-model|service declared with its own local credential store instead of referencing the declared identity provider edge|
|Gatekeeper|Azure [C13]|strata|2|reasoned-discharge|subset of Gateway family|
|Publisher-Subscriber|Azure [C13]|strata|2|reasoned-discharge|fan-out to multiple consumers implemented as N direct point-to-point calls|
|Sequential Convoy|Azure [C13]|strata|2|reasoned-discharge|ordering requirement on a partition/shard key with no explicit ordering-guarantee annotation|
|Asynchronous Request-Reply|Azure [C13]|strata|1|proof-against-model|long-running operation modeled as a synchronous edge under a declared long-duration SLA|
|External Configuration Store|Azure [C13]|arch/strata|1|proof-against-code|dup of 5.3 Config proxy|
|Bulkhead|Azure [C13] (also 5.2 Nygard)|strata|1|proof-against-model|dup of 5.2 Bulkhead|
|Circuit Breaker|Azure [C13] (also 5.2 Nygard)|strata|1|proof-against-model|dup of 5.2 Circuit Breaker|
|Choreography|Azure [C13] -- newly confirmed, not in task's named list|strata|2|reasoned-discharge|central-orchestrator edge count vs. peer-to-peer event edges -- recommend-only shape trigger|
|Index Table|Azure [C13] -- newly confirmed, not in task's named list|strata|2|reasoned-discharge|frequently-filtered field with no secondary index modeled|
|Messaging Bridge|Azure [C13] -- newly confirmed, not in task's named list|strata|2|reasoned-discharge|two incompatible messaging systems bridged by ad hoc glue code instead of a declared bridge component|
|Quarantine|Azure [C13] -- newly confirmed, not in task's named list|strata|2|reasoned-discharge|externally-sourced asset consumed with no declared quality-gate/scan step|
|Compute Resource Consolidation|Azure [C13]|strata|2|reasoned-discharge|many single-purpose low-utilization compute units instead of a consolidated one|
|Deployment Stamps|Azure [C13]|strata|2|reasoned-discharge|single global deployment unit under a declared multi-tenant/multi-region requirement|
|Geode|Azure [C13]|strata|2|reasoned-discharge|single-region deployment under a declared global-latency requirement|

### 5.5 Observability (RED/USE/Golden Signals/SLI-SLO/correlation IDs/structured logging/cardinality; general knowledge, not independently re-verified via search in this pass)

| Name | ARCH/STRATA | Tier | Proof mode | Static proxy |
|---|---|---|---|---|
|RED/USE/Golden Signals|strata|1 (instrumentation presence)|proof-against-code|service entrypoint with no metric-emission call in its body|
|SLI/SLO/Error-Budget|strata|2|reasoned-discharge|service declared in model with no SLO annotation|
|Correlation IDs|both|1|proof-against-code|cross-service call site that does not propagate an incoming request/trace-id header|
|Structured Logging|arch|1|proof-against-code|dup of XI Logs proxy, directly enforces the user's global "never print for diagnostics" rule|
|Cardinality control|arch|1|proof-against-code|metric-emission call site using a high-cardinality value as a label/tag argument|

### 5.6 Consistency/data (CAP/PACELC/ACID-BASE/idempotency/delivery-semantics/eventual-consistency/schema-evolution/single-source-of-truth/retention; general knowledge, not independently re-verified via search in this pass)

| Name | ARCH/STRATA | Tier | Proof mode | Static proxy |
|---|---|---|---|---|
|CAP / PACELC|strata|3|reasoned-discharge|a theorem about tradeoffs; presence-of-declaration in the model is tier 2 at best|
|ACID vs BASE|strata|2|reasoned-discharge|data-store choice declared vs. consistency requirement of operations run against it|
|Idempotency|both|1|proof-against-code|dup of Idempotent Receiver proxy, generalized to any mutating handler on a retryable edge|
|Delivery semantics|strata|1 (declaration) / 3 (true guarantee)|proof-against-model / reasoned-discharge|queue/messaging edge with no declared delivery-semantics annotation|
|Eventual Consistency|strata|2|reasoned-discharge|read-after-write requirement declared against a store/replica edge with no consistency-level annotation|
|Schema Evolution/Versioning|both|1|proof-against-code|wire-format/DB-schema field removed or type-narrowed without a version bump / migration record|
|Single Source of Truth|arch|1|proof-against-code|the same fact computed/stored independently in two places instead of one canonical owner|
|Retention|strata|2|reasoned-discharge|data store declared with no retention/TTL policy annotated|

### 5.7 Security (least privilege/defense-in-depth/fail-secure/zero-trust/blast-radius/STRIDE/attack-surface; general knowledge, not independently re-verified via search in this pass)

| Name | ARCH/STRATA | Tier | Proof mode | Static proxy |
|---|---|---|---|---|
|Least Privilege|both|1|proof-against-code / proof-against-model|credential/role/scope grant wider than the set of resources actually referenced|
|Defense-in-Depth|strata|2|reasoned-discharge|single security control protecting a sensitive edge|
|Fail-Secure|arch|1|proof-against-code|error/exception path in an authz check that defaults to allow instead of deny|
|Zero-Trust|strata|2|reasoned-discharge|internal service-to-service edge with no mTLS/auth annotation|
|Blast Radius|strata|2|reasoned-discharge|single shared credential/role used across many otherwise-independent services|
|STRIDE|strata|3|reasoned-discharge|a threat-modeling methodology, not itself a single checkable fact -- its six categories seed the tier-1/2 checks already listed elsewhere (auth=Spoofing, integrity=Tampering, audit-log=Repudiation, encryption=Info-disclosure, rate-limit=DoS, least-privilege=Elevation)|
|Attack Surface|both|2|reasoned-discharge|count of externally-reachable entrypoints with no corresponding authn/authz annotation|

### 5.8 Scalability/performance (statelessness/N+1/connection-pooling/batching/pagination/backpressure/load-shedding; general knowledge, not independently re-verified via search in this pass)

| Name | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|
|N+1 queries|arch|1|query-issuing call site inside a loop iterating over a collection fetched by a prior query|
|Connection pooling|arch|1|new connection object constructed per-request/per-call instead of drawn from a pool|
|Batching|arch|2|repeated single-item calls to the same remote/DB API inside a loop where a batch API exists|
|Pagination/Unbounded Result Sets|arch|1|dup of 5.2 proxy|
|Backpressure|strata|2|dup of 5.2 Handshaking proxy|
|Load Shedding|strata|2|dup of 5.2 Shed Load proxy|

---

## 6. Cross-cutting

| Name | ARCH/STRATA | Tier | Static proxy |
|---|---|---|---|
|Naming heuristics (general)|arch|3|dup of N1-N7 -- fundamentally a tier-3 judgment; only tier-1/2 slivers are N5 (length-vs-scope) and N6 (Hungarian-encoding detection)|
|FIRST test principles (Fast, Isolated, Repeatable, Self-validating, Timely)|arch|1 (Isolated/Self-validating) / 2 (Fast) / 3 (Timely)|test with shared mutable fixture state across test functions (Isolated violation); test function with no assertion call (Self-validating violation); runtime-threshold for Fast requires execution|
|AAA (Arrange-Act-Assert) test structure|arch|2|test body with assertions interleaved among multiple act-shaped calls rather than grouped|
|Test smells (Fragile Test, Test Duplication, Mystery Guest, Eager Test, Assertion Roulette, Excessive Setup)|arch|1/2 mixed|Test Duplication = clone detection (tier 1); Assertion Roulette = multiple unlabeled asserts with no message (tier 1); Mystery Guest = test reads external file/network with no fixture declaration (tier 1); Eager Test = single test invoking multiple unrelated production methods (tier 2); Excessive Setup = setup LOC threshold vs. test-body LOC (tier 2)|
|Documentation/doc-drift|arch|1|already implemented in this repo (frob's DRIFT001/COV001 doc-graph) -- listed here only to close the corpus, not a new gate|

---

## Coverage proof (denominator table)

| Corpus | Denominator | Enumerated | Verification status |
|---|---|---|---|
|SOLID|5|5|primary-adjacent, well-established, general knowledge [C3]|
|Package principles (Martin PPP)|6 principles + 3 metrics = 9|9|general knowledge, not re-verified via search this pass|
|GRASP|9|9|verified via search [C4]|
|Connascence forms|9 (5 static + 4 dynamic)|9|verified and CORRECTED via connascence.io + Wikipedia [C1][C2] (initial draft miscounted as 6+3)|
|Laws & heuristics|21 named|21|general knowledge, individually well-known terms, not independently re-verified per-entry|
|Fowler Refactoring (2nd ed.) smells|22|22|verified count and grouping via Fowler's own retrospective [C6]; exact per-entry naming cross-checked against a secondary source [C5] that was found to contain naming errors (still using pre-2nd-ed. names) and NOT relied upon for final naming|
|Clean Code Appendix B: Comments/Environment/Functions|5+2+4=11|11|spot-confirmed structure via search [C7]; full content reconstructed from secondary sources, not page-verified|
|Clean Code Appendix B: General|36 (G1-G36)|36|spot-confirmed G1/G36 via search [C7]; full content reconstructed from secondary sources, not page-verified|
|Clean Code Appendix B: Names|7 (N1-N7)|7|spot-confirmed N1/N7 via search [C7]; full content reconstructed, not page-verified|
|Clean Code Appendix B: Tests|9 (T1-T9)|9|spot-confirmed T1/T9 via search [C7]; full content reconstructed, not page-verified|
|GoF patterns|23|23|verified via search [C8]|
|Fowler PoEAA patterns|~20 representative|20|general knowledge, not re-verified via search this pass|
|DDD tactical patterns|11 (this doc's own coarser count; superseded by `design-pattern-catalog.md` section 5.1's live-verified 45-entry Evans DDD Reference breakdown, cross-referenced not re-tabulated here)|11|general knowledge, not re-verified via search this pass in THIS document; live-verified in the sibling document this pass -- see `design-pattern-catalog.md` section 5.1|
|Concurrency patterns|11|11|general knowledge, not re-verified via search this pass|
|Functional patterns|10|10|general knowledge, not re-verified via search this pass|
|Language idioms (Rust/TS/C++/C/Python)|14 named|14|general knowledge, not re-verified via search this pass|
|Anti-patterns (code-static)|20|20|general knowledge, not re-verified via search this pass; 4 process/management anti-patterns explicitly excluded|
|8 Fallacies of Distributed Computing|8|8 (two variant lists recorded)|verified live page shows a DIFFERENT 8th/7th item than the classic list -- both recorded [C9]|
|Release It! anti-patterns|12|12|**live-verified this pass** -- O'Reilly's own hosted Contents panel, read via Playwright (see 5.2); corrects the prior pass's 13-count secondary-sourced estimate [C10][C11]|
|Release It! patterns|12|12|**live-verified this pass** -- same O'Reilly Contents panel via Playwright (see 5.2); corrects the prior pass's 13-count secondary-sourced estimate [C10][C11]|
|12-Factor App|12|12|verified word-for-word against 12factor.net [C12]|
|Cloud/well-architected patterns|45 (current live Azure catalog, superset of the task's named list)|45|verified live against Azure Architecture Center [C13]; 2 task-named entries (Outbox, Idempotent Receiver) traced to a DIFFERENT source (microservices.io/Richardson) since they are not in the current Azure index -- corrected and sourced accordingly|
|Observability|5|5|general knowledge, not re-verified via search this pass|
|Consistency/data|8|8|general knowledge, not re-verified via search this pass|
|Security|7|7|general knowledge, not re-verified via search this pass|
|Scalability/performance|6|6|general knowledge, not re-verified via search this pass|
|Cross-cutting (naming/testing/docs)|4 groups|4|general knowledge, not re-verified via search this pass|

**Total catalog entries:** approximately 318 individual rows across all
tables above (was ~320; Release It!'s corrected 12+12 live-verified count
replaces the prior 13+13 estimate, a net -2 this pass).

**Tier-1 (statically provable) count:** approximately 140 of the ~320
rows carry tier 1 somewhere in their tier column. These are the strongest
direct candidates to become arch/strata check tickets under
T-0330/T-0331; the tier-2 rows are T-0332's pattern-recommender
candidates; the tier-3 rows are recorded so nobody re-derives them and
mistakenly tries to hard-gate an unprovable judgment call.

**Deliberately excluded from this catalog (with reason):**
- Process/management anti-patterns (Analysis Paralysis, Not Invented
  Here, Smoke and Mirrors, Design by Committee) -- describe team/process
  dysfunction, not a property of committed code or a system-design model.
- Prose-quality/naming-quality judgments across every corpus -- flagged
  tier 3 throughout rather than assigned a fake proxy.
- STRIDE and CAP/PACELC are recorded as whole-methodology tier-3 entries
  even though their sub-parts seed real tier-1/2 checks elsewhere.

**Honesty note on verification depth (per explicit user instruction to
research and cite, not recall from memory):** Corpora verified against a
primary or near-primary source during this pass, with citation markers,
are: SOLID (general/[C3]), GRASP [C4], Connascence [C1][C2] (correction
found), Fowler Refactoring 2nd-ed. smells [C6], GoF patterns [C8],
12-Factor App [C12] (word-for-word), the Azure cloud pattern catalog
[C13] (live fetch, correction found on Outbox/Idempotent-Receiver
provenance and the 8-Fallacies variant [C9]), and, added this pass,
**Release It! stability anti-patterns and patterns (12+12, [C14], via
Playwright against O'Reilly's own hosted Contents panel -- corrects the
prior pass's 403-blocked 13+13 secondary-sourced estimate)**. Corpora
presented from general knowledge WITHOUT an independent search/fetch
check in THIS document are explicitly marked inline above (Package
principles, Laws & heuristics, PoEAA, DDD tactical patterns [now
live-verified in the sibling `design-pattern-catalog.md` document this
pass, see that document's section 5.1 -- not re-tabulated here],
concurrency/functional patterns, language idioms, anti-patterns catalog,
Observability, Consistency/data, Security, Scalability/performance,
Cross-cutting). Three real corrections were found and applied during
research across the two passes: the connascence static/dynamic split
(was 6+3, is actually 5+4), the Outbox/Idempotent-Receiver source
attribution (task implied Azure, they are actually
microservices.io/Richardson patterns), and, this pass, the Release It!
anti-pattern/pattern counts (were estimated 13+13, are actually
publisher-verified 12+12, with several entry names corrected -- see 5.2).
If T-0330/T-0331 implementation work draws on the remaining
general-knowledge sections above, a follow-up verification pass against
primary sources (the physical/PDF books for PoEAA [now live-verified in
`design-pattern-catalog.md`] and Clean Code) is recommended before
treating exact per-entry names as gospel -- the *concepts and static
proxies* are sound, but exact enumerated names in those sections were not
independently checked against a primary source in this pass.

## Provability note (T-0331 constraint)

Every strata-tagged entry above carries a **proof mode** column value.
`proof-against-model` is explicitly the *weaker* claim (the `.strata`
model says a mitigation exists) and must never be reported by a check as
"proven safe" -- only as "modeled as mitigated." Only `proof-against-code`
rows may claim the implementation itself was verified. `reasoned-discharge`
rows require an attached human/reviewer sign-off artifact (ticket, ADR, or
waiver) before a strata check may pass them -- they are not silently
green. This distinction is the direct answer to T-0331's provability
constraint: a strata gate that only validates the model, not the code,
must say so in its own output, every time.

---

## Sources

- [C1] connascence.io -- "Forms of Connascence" (https://connascence.io/) -- fetched live during this pass; confirms 5 static forms (Name, Type, Meaning, Position, Algorithm) + 4 dynamic forms (Execution, Timing, Value, Identity), and the strength/degree/locality property model.
- [C2] Wikipedia -- "Connascence" (https://en.wikipedia.org/wiki/Connascence) -- fetched live; cross-check confirms the same static/dynamic split and strength-ordering framing.
- [C3] SOLID is Robert C. Martin's canon, general knowledge; not independently re-searched this pass beyond confirming it is uncontested as "5 principles."
- [C4] Wikipedia -- "GRASP (object-oriented design)" and fluentcpp.com/kamilgrzybek.com summaries, via WebSearch -- confirms all 9 GRASP principle names and definitions.
- [C5] codesmellcost.com -- "The 22 Smells" (https://codesmellcost.com/the-22-smells) -- fetched live; used for the 5-category grouping structure, but flagged as containing outdated (pre-2nd-edition) naming and NOT used for final entry names.
- [C6] Martin Fowler -- "The Second Edition of 'Refactoring'" (https://martinfowler.com/articles/refactoring-2nd-ed.html) -- surfaced via WebSearch; confirms the additions/removals/renames between 1st and 2nd edition smell catalogs.
- [C7] WebSearch results referencing Clean Code Chapter 17 (Smells and Heuristics), including janaipakos/Clean-Code-Smells-and-Heuristics and DanWareing/clean_code_heuristics GitHub repos, and vivekkhatri.com's chapter summary -- confirms chapter structure (C1-5/E1-2/F1-4/G1-36/N1-7/T1-9) and spot-confirms G1, G36, N1, N7, T1, T9 verbatim.
- [C8] WebSearch aggregate result confirming the standard GoF 23-pattern breakdown (5 creational/7 structural/11 behavioral) with names.
- [C9] Microsoft Learn -- "Cloud Design Patterns - Azure Architecture Center" (https://learn.microsoft.com/en-us/azure/architecture/patterns/) -- fetched live; page text lists a modified 8-fallacies variant differing from the classic Deutsch list.
- [C10] Medium (Thomas Pierrain) -- "Stability ANTI-patterns cheat sheet" -- surfaced via WebSearch.
- [C11] sookocheff.com -- "Stability Anti-Patterns" -- surfaced via WebSearch; O'Reilly's own TOC page (oreilly.com/library/view/release-it-2nd/9781680504552/) returned HTTP 403 on WebFetch in the pass that produced this citation (superseded by [C14] this pass, which reached the same page successfully via Playwright).
- [C12] 12factor.net (https://12factor.net/) -- fetched live; exact 12-factor titles confirmed word-for-word.
- [C14] O'Reilly -- "Release It!, 2nd Edition" (https://www.oreilly.com/library/view/release-it-2nd/9781680504552/) -- live-rendered and read via Playwright this pass (`mcp__playwright__browser_navigate` + `browser_evaluate` against the publisher's own "Contents" sidebar panel, expanded via its "Show More" control); confirms 12 chapter-4 stability-antipattern headings and 12 chapter-5 stability-pattern headings verbatim, correcting the prior [C10][C11]-sourced 13+13 secondary estimate.
- [C13] Microsoft Learn -- "Cloud Design Patterns - Azure Architecture Center" pattern-catalog table (https://learn.microsoft.com/en-us/azure/architecture/patterns/) -- fetched live; full 45-entry table transcribed directly from the live page.

---

## DENOMINATOR MANIFEST

Machine-readable, one entry per named row across every markdown table
in sections 1-6 above (288 entries, mechanically extracted from this
document's own tables -- Tier column value maps directly to the
checkability tag: tier 1 -> tier1-static, tier 2 -> tier2-advisory,
tier 3 -> tier3-not-checkable). Format: `- id: <STABLE-ID> | catalog:
<section> | checkability: <tag> | trap-ref: <section number>`. This
is what the exhaustiveness drift-lock test binds against.

- id: ACC-1-1-1 | catalog: architecture-check-catalog-sec-1.1 | checkability: tier2-advisory | trap-ref: 1.1
- id: ACC-1-1-2 | catalog: architecture-check-catalog-sec-1.1 | checkability: tier2-advisory | trap-ref: 1.1
- id: ACC-1-1-3 | catalog: architecture-check-catalog-sec-1.1 | checkability: tier1-static | trap-ref: 1.1
- id: ACC-1-1-4 | catalog: architecture-check-catalog-sec-1.1 | checkability: tier2-advisory | trap-ref: 1.1
- id: ACC-1-1-5 | catalog: architecture-check-catalog-sec-1.1 | checkability: tier1-static | trap-ref: 1.1
- id: ACC-1-2-REP-REUSE-RELEASE-EQUIVALENCE | catalog: architecture-check-catalog-sec-1.2 | checkability: tier2-advisory | trap-ref: 1.2
- id: ACC-1-2-CCP-COMMON-CLOSURE | catalog: architecture-check-catalog-sec-1.2 | checkability: tier1-static | trap-ref: 1.2
- id: ACC-1-2-CRP-COMMON-REUSE | catalog: architecture-check-catalog-sec-1.2 | checkability: tier1-static | trap-ref: 1.2
- id: ACC-1-2-ADP-ACYCLIC-DEPENDENCIES | catalog: architecture-check-catalog-sec-1.2 | checkability: tier1-static | trap-ref: 1.2
- id: ACC-1-2-SDP-STABLE-DEPENDENCIES | catalog: architecture-check-catalog-sec-1.2 | checkability: tier1-static | trap-ref: 1.2
- id: ACC-1-2-SAP-STABLE-ABSTRACTIONS | catalog: architecture-check-catalog-sec-1.2 | checkability: tier1-static | trap-ref: 1.2
- id: ACC-1-2-INSTABILITY-METRIC-I-CE-CA-CE | catalog: architecture-check-catalog-sec-1.2 | checkability: tier1-static | trap-ref: 1.2
- id: ACC-1-2-ABSTRACTNESS-METRIC-A-ABSTRACT-TYPES-TOTAL-TYPES | catalog: architecture-check-catalog-sec-1.2 | checkability: tier1-static | trap-ref: 1.2
- id: ACC-1-2-DISTANCE-FROM-MAIN-SEQUENCE-D | catalog: architecture-check-catalog-sec-1.2 | checkability: tier2-advisory | trap-ref: 1.2
- id: ACC-1-3-INFORMATION-EXPERT | catalog: architecture-check-catalog-sec-1.3 | checkability: tier2-advisory | trap-ref: 1.3
- id: ACC-1-3-CREATOR | catalog: architecture-check-catalog-sec-1.3 | checkability: tier2-advisory | trap-ref: 1.3
- id: ACC-1-3-CONTROLLER | catalog: architecture-check-catalog-sec-1.3 | checkability: tier3-not-checkable | trap-ref: 1.3
- id: ACC-1-3-LOW-COUPLING | catalog: architecture-check-catalog-sec-1.3 | checkability: tier1-static | trap-ref: 1.3
- id: ACC-1-3-HIGH-COHESION | catalog: architecture-check-catalog-sec-1.3 | checkability: tier2-advisory | trap-ref: 1.3
- id: ACC-1-3-POLYMORPHISM | catalog: architecture-check-catalog-sec-1.3 | checkability: tier2-advisory | trap-ref: 1.3
- id: ACC-1-3-PURE-FABRICATION | catalog: architecture-check-catalog-sec-1.3 | checkability: tier3-not-checkable | trap-ref: 1.3
- id: ACC-1-3-INDIRECTION | catalog: architecture-check-catalog-sec-1.3 | checkability: tier3-not-checkable | trap-ref: 1.3
- id: ACC-1-3-PROTECTED-VARIATIONS | catalog: architecture-check-catalog-sec-1.3 | checkability: tier2-advisory | trap-ref: 1.3
- id: ACC-1-4-CONNASCENCE-OF-NAME-CON | catalog: architecture-check-catalog-sec-1.4 | checkability: tier1-static | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-TYPE-COT | catalog: architecture-check-catalog-sec-1.4 | checkability: tier1-static | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-MEANING-CONVENTION-COM | catalog: architecture-check-catalog-sec-1.4 | checkability: tier1-static | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-POSITION-COP | catalog: architecture-check-catalog-sec-1.4 | checkability: tier1-static | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-ALGORITHM-COA | catalog: architecture-check-catalog-sec-1.4 | checkability: tier2-advisory | trap-ref: 1.4
- id: ACC-1-4-NAME | catalog: architecture-check-catalog-sec-1.4 | checkability: tier2-advisory | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-EXECUTION-ORDER | catalog: architecture-check-catalog-sec-1.4 | checkability: tier3-not-checkable | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-TIMING-COTM | catalog: architecture-check-catalog-sec-1.4 | checkability: tier3-not-checkable | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-VALUE-COV | catalog: architecture-check-catalog-sec-1.4 | checkability: tier2-advisory | trap-ref: 1.4
- id: ACC-1-4-CONNASCENCE-OF-IDENTITY-COI | catalog: architecture-check-catalog-sec-1.4 | checkability: tier3-not-checkable | trap-ref: 1.4
- id: ACC-1-5-DRY-DON-T-REPEAT-YOURSELF | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-KISS-KEEP-IT-SIMPLE | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-YAGNI | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-LAW-OF-DEMETER | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-COMPOSITION-OVER-INHERITANCE | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-TELL-DON-T-ASK | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-CQS-COMMAND-QUERY-SEPARATION | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-FAIL-FAST | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-PRINCIPLE-OF-LEAST-ASTONISHMENT | catalog: architecture-check-catalog-sec-1.5 | checkability: tier3-not-checkable | trap-ref: 1.5
- id: ACC-1-5-SLAP-SINGLE-LEVEL-OF-ABSTRACTION-PRINCIPLE | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-ENCAPSULATE-WHAT-VARIES | catalog: architecture-check-catalog-sec-1.5 | checkability: tier3-not-checkable | trap-ref: 1.5
- id: ACC-1-5-PROGRAM-TO-AN-INTERFACE-NOT-AN-IMPLEMENTATION | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-INVERSION-OF-CONTROL | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-MAKE-ILLEGAL-STATES-UNREPRESENTABLE | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-PARSE-DON-T-VALIDATE | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-ERRORS-AS-VALUES | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-IMMUTABILITY-BY-DEFAULT | catalog: architecture-check-catalog-sec-1.5 | checkability: tier1-static | trap-ref: 1.5
- id: ACC-1-5-PRINCIPLE-OF-LEAST-PRIVILEGE-DESIGN-LEVEL-DISTINCT-FROM-SECURITY-LIST-EN | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-ROBUSTNESS-PRINCIPLE-BE-LIBERAL-IN-WHAT-YOU-ACCEPT-CONSERVATIVE-IN-WHAT- | catalog: architecture-check-catalog-sec-1.5 | checkability: tier3-not-checkable | trap-ref: 1.5
- id: ACC-1-5-RULE-OF-THREE-DUPLICATE-TWICE-BEFORE-ABSTRACTING | catalog: architecture-check-catalog-sec-1.5 | checkability: tier2-advisory | trap-ref: 1.5
- id: ACC-1-5-HOLLYWOOD-PRINCIPLE-DON-T-CALL-US-WE-LL-CALL-YOU | catalog: architecture-check-catalog-sec-1.5 | checkability: tier3-not-checkable | trap-ref: 1.5
- id: ACC-2-1-MYSTERIOUS-NAME | catalog: architecture-check-catalog-sec-2.1 | checkability: tier3-not-checkable | trap-ref: 2.1
- id: ACC-2-1-DUPLICATED-CODE | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-LONG-FUNCTION | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-LONG-PARAMETER-LIST | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-GLOBAL-DATA | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-MUTABLE-DATA | catalog: architecture-check-catalog-sec-2.1 | checkability: tier2-advisory | trap-ref: 2.1
- id: ACC-2-1-DIVERGENT-CHANGE | catalog: architecture-check-catalog-sec-2.1 | checkability: tier2-advisory | trap-ref: 2.1
- id: ACC-2-1-SHOTGUN-SURGERY | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-FEATURE-ENVY | catalog: architecture-check-catalog-sec-2.1 | checkability: tier2-advisory | trap-ref: 2.1
- id: ACC-2-1-DATA-CLUMPS | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-PRIMITIVE-OBSESSION | catalog: architecture-check-catalog-sec-2.1 | checkability: tier2-advisory | trap-ref: 2.1
- id: ACC-2-1-REPEATED-SWITCHES | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-LOOPS-IMPERATIVE-LOOP-WHERE-A-PIPELINE-COLLECTION-OP-READS-BETTER | catalog: architecture-check-catalog-sec-2.1 | checkability: tier3-not-checkable | trap-ref: 2.1
- id: ACC-2-1-LAZY-ELEMENT | catalog: architecture-check-catalog-sec-2.1 | checkability: tier2-advisory | trap-ref: 2.1
- id: ACC-2-1-SPECULATIVE-GENERALITY | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-TEMPORARY-FIELD | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-MESSAGE-CHAINS | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-MIDDLE-MAN | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-INSIDER-TRADING | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-LARGE-CLASS | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-ALTERNATIVE-CLASSES-WITH-DIFFERENT-INTERFACES | catalog: architecture-check-catalog-sec-2.1 | checkability: tier2-advisory | trap-ref: 2.1
- id: ACC-2-1-DATA-CLASS | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-1-REFUSED-BEQUEST | catalog: architecture-check-catalog-sec-2.1 | checkability: tier1-static | trap-ref: 2.1
- id: ACC-2-2-C1-INAPPROPRIATE-INFORMATION | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-C2-OBSOLETE-COMMENT | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2-C3-REDUNDANT-COMMENT | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-C4-POORLY-WRITTEN-COMMENT | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-C5-COMMENTED-OUT-CODE | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2-NAME | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-E1-BUILD-REQUIRES-MORE-THAN-ONE-STEP | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-E2-TESTS-REQUIRE-MORE-THAN-ONE-STEP | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-NAME-2 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-F1-TOO-MANY-ARGUMENTS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2-F2-OUTPUT-ARGUMENTS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2-F3-FLAG-ARGUMENTS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2-F4-DEAD-FUNCTION | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2- | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G1 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G2 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G3 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G4 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G5 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G6 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G7 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G8 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G9 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G10 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G11 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G12 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G13 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G14 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G15 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G16 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G17 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G18 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G19 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G20 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G21 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G22 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G23 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G24 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G25 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G26 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G27 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G28 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G29 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G30 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G31 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G32 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G33 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G34 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G35 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-G36 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-NAME-3 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-N1-CHOOSE-DESCRIPTIVE-NAMES | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-N2-CHOOSE-NAMES-AT-THE-APPROPRIATE-LEVEL-OF-ABSTRACTION | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-N3-USE-STANDARD-NOMENCLATURE-WHERE-POSSIBLE | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-N4-UNAMBIGUOUS-NAMES | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-N5-USE-LONG-NAMES-FOR-LONG-SCOPES | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-N6-AVOID-ENCODINGS-HUNGARIAN-NOTATION-ETC | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2-N7-NAMES-SHOULD-DESCRIBE-SIDE-EFFECTS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-NAME-4 | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-T1-INSUFFICIENT-TESTS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-T2-USE-A-COVERAGE-TOOL | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-T3-DON-T-SKIP-TRIVIAL-TESTS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-T4-AN-IGNORED-TEST-IS-A-QUESTION-ABOUT-AN-AMBIGUITY | catalog: architecture-check-catalog-sec-2.2 | checkability: tier1-static | trap-ref: 2.2
- id: ACC-2-2-T5-TEST-BOUNDARY-CONDITIONS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-T6-EXHAUSTIVELY-TEST-NEAR-BUGS | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-T7-PATTERNS-OF-FAILURE-ARE-REVEALING | catalog: architecture-check-catalog-sec-2.2 | checkability: tier3-not-checkable | trap-ref: 2.2
- id: ACC-2-2-T8-TEST-COVERAGE-PATTERNS-CAN-BE-REVEALING | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-2-2-T9-TESTS-SHOULD-BE-FAST | catalog: architecture-check-catalog-sec-2.2 | checkability: tier2-advisory | trap-ref: 2.2
- id: ACC-3-1-ARCH | catalog: architecture-check-catalog-sec-3.1 | checkability: tier2-advisory | trap-ref: 3.1
- id: ACC-3-2-BOTH | catalog: architecture-check-catalog-sec-3.2 | checkability: tier2-advisory | trap-ref: 3.2
- id: ACC-3-3-BOTH | catalog: architecture-check-catalog-sec-3.3 | checkability: tier2-advisory | trap-ref: 3.3
- id: ACC-3-4-ARCH | catalog: architecture-check-catalog-sec-3.4 | checkability: tier2-advisory | trap-ref: 3.4
- id: ACC-3-5-ARCH | catalog: architecture-check-catalog-sec-3.5 | checkability: tier2-advisory | trap-ref: 3.5
- id: ACC-3-6-TYPE-STATE-PATTERN | catalog: architecture-check-catalog-sec-3.6 | checkability: tier2-advisory | trap-ref: 3.6
- id: ACC-3-6-NEWTYPE-PATTERN | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-RAII | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-BUILDER-PATTERN | catalog: architecture-check-catalog-sec-3.6 | checkability: tier2-advisory | trap-ref: 3.6
- id: ACC-3-6-DROP-RAII-GUARD-FOR-LOCKS | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-CONST-CORRECTNESS | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-RULE-OF-THREE-FIVE-ZERO | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-RAII-SMART-POINTER-OVER-RAW-NEW-DELETE | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-HEADER-GUARDS-PRAGMA-ONCE | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-GOTO-FOR-CLEANUP-PATTERN | catalog: architecture-check-catalog-sec-3.6 | checkability: tier2-advisory | trap-ref: 3.6
- id: ACC-3-6-CONTEXT-MANAGER-WITH | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-DUCK-TYPING-PROTOCOL-OVER-ABC-INHERITANCE | catalog: architecture-check-catalog-sec-3.6 | checkability: tier2-advisory | trap-ref: 3.6
- id: ACC-3-6-DISCRIMINATED-UNION-EXHAUSTIVENESS-SWITCH | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-3-6-READONLY-AS-CONST-FOR-IMMUTABLE-DATA | catalog: architecture-check-catalog-sec-3.6 | checkability: tier1-static | trap-ref: 3.6
- id: ACC-4-GOD-OBJECT-BLOB | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-ANEMIC-DOMAIN-MODEL | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-POLTERGEIST-SHORT-LIVED-CLASS-THAT-ONLY-FORWARDS-CALLS | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-LAVA-FLOW-DEAD-FROZEN-CODE-NOBODY-DARES-REMOVE | catalog: architecture-check-catalog-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: ACC-4-YO-YO-PROBLEM | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-BOAT-ANCHOR | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-GOLDEN-HAMMER | catalog: architecture-check-catalog-sec-4 | checkability: tier3-not-checkable | trap-ref: 4
- id: ACC-4-CARGO-CULT-PROGRAMMING | catalog: architecture-check-catalog-sec-4 | checkability: tier3-not-checkable | trap-ref: 4
- id: ACC-4-SPAGHETTI-CODE | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-STRINGLY-TYPED | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-BOOLEAN-BLINDNESS | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-SEQUENTIAL-COUPLING | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-COPY-PASTE-PROGRAMMING | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-MAGIC-NUMBERS-STRINGS | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-REINVENTING-THE-WHEEL | catalog: architecture-check-catalog-sec-4 | checkability: tier3-not-checkable | trap-ref: 4
- id: ACC-4-VENDOR-LOCK-IN-ARCHITECTURE-LEVEL | catalog: architecture-check-catalog-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: ACC-4-BIG-BALL-OF-MUD | catalog: architecture-check-catalog-sec-4 | checkability: tier1-static | trap-ref: 4
- id: ACC-4-ACCIDENTAL-COMPLEXITY-VS-ESSENTIAL | catalog: architecture-check-catalog-sec-4 | checkability: tier3-not-checkable | trap-ref: 4
- id: ACC-4-PREMATURE-OPTIMIZATION | catalog: architecture-check-catalog-sec-4 | checkability: tier3-not-checkable | trap-ref: 4
- id: ACC-4-ANALYSIS-PARALYSIS | catalog: architecture-check-catalog-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: ACC-4-NOT-INVENTED-HERE | catalog: architecture-check-catalog-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: ACC-4-SMOKE-AND-MIRRORS | catalog: architecture-check-catalog-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: ACC-4-DESIGN-BY-COMMITTEE | catalog: architecture-check-catalog-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: ACC-5-1-STRATA | catalog: architecture-check-catalog-sec-5.1 | checkability: tier2-advisory | trap-ref: 5.1
- id: ACC-5-2-INTEGRATION-POINTS | catalog: architecture-check-catalog-sec-5.2 | checkability: tier1-static | trap-ref: 5.2
- id: ACC-5-2-UNBOUNDED-RESULT-SETS | catalog: architecture-check-catalog-sec-5.2 | checkability: tier1-static | trap-ref: 5.2
- id: ACC-5-2-TIMEOUT-PATTERN-PRESENT | catalog: architecture-check-catalog-sec-5.2 | checkability: tier1-static | trap-ref: 5.2
- id: ACC-5-2-CIRCUIT-BREAKER | catalog: architecture-check-catalog-sec-5.2 | checkability: tier1-static | trap-ref: 5.2
- id: ACC-5-2-BULKHEAD | catalog: architecture-check-catalog-sec-5.2 | checkability: tier1-static | trap-ref: 5.2
- id: ACC-5-2-FAIL-FAST | catalog: architecture-check-catalog-sec-5.2 | checkability: tier1-static | trap-ref: 5.2
- id: ACC-5-2-LET-IT-CRASH | catalog: architecture-check-catalog-sec-5.2 | checkability: tier2-advisory | trap-ref: 5.2
- id: ACC-5-2-STEADY-STATE | catalog: architecture-check-catalog-sec-5.2 | checkability: tier3-not-checkable | trap-ref: 5.2
- id: ACC-5-2-CASCADING-FAILURES | catalog: architecture-check-catalog-sec-5.2 | checkability: tier1-static | trap-ref: 5.2
- id: ACC-5-2-SLA-INVERSION | catalog: architecture-check-catalog-sec-5.2 | checkability: tier2-advisory | trap-ref: 5.2
- id: ACC-5-2-DOGPILE-THUNDERING-HERD | catalog: architecture-check-catalog-sec-5.2 | checkability: tier2-advisory | trap-ref: 5.2
- id: ACC-5-2-HANDSHAKING-BACKPRESSURE | catalog: architecture-check-catalog-sec-5.2 | checkability: tier2-advisory | trap-ref: 5.2
- id: ACC-5-2-TEST-HARNESS-FAILURE-INJECTION | catalog: architecture-check-catalog-sec-5.2 | checkability: tier2-advisory | trap-ref: 5.2
- id: ACC-5-2-SHED-LOAD-GOVERNOR | catalog: architecture-check-catalog-sec-5.2 | checkability: tier2-advisory | trap-ref: 5.2
- id: ACC-5-2-ROLLBACK | catalog: architecture-check-catalog-sec-5.2 | checkability: tier2-advisory | trap-ref: 5.2
- id: ACC-5-3-I-CODEBASE | catalog: architecture-check-catalog-sec-5.3 | checkability: tier1-static | trap-ref: 5.3
- id: ACC-5-3-II-DEPENDENCIES | catalog: architecture-check-catalog-sec-5.3 | checkability: tier1-static | trap-ref: 5.3
- id: ACC-5-3-III-CONFIG | catalog: architecture-check-catalog-sec-5.3 | checkability: tier1-static | trap-ref: 5.3
- id: ACC-5-3-IV-BACKING-SERVICES | catalog: architecture-check-catalog-sec-5.3 | checkability: tier2-advisory | trap-ref: 5.3
- id: ACC-5-3-V-BUILD-RELEASE-RUN | catalog: architecture-check-catalog-sec-5.3 | checkability: tier2-advisory | trap-ref: 5.3
- id: ACC-5-3-VI-PROCESSES-STATELESS | catalog: architecture-check-catalog-sec-5.3 | checkability: tier1-static | trap-ref: 5.3
- id: ACC-5-3-VII-PORT-BINDING | catalog: architecture-check-catalog-sec-5.3 | checkability: tier2-advisory | trap-ref: 5.3
- id: ACC-5-3-VIII-CONCURRENCY-PROCESS-MODEL | catalog: architecture-check-catalog-sec-5.3 | checkability: tier3-not-checkable | trap-ref: 5.3
- id: ACC-5-3-IX-DISPOSABILITY | catalog: architecture-check-catalog-sec-5.3 | checkability: tier2-advisory | trap-ref: 5.3
- id: ACC-5-3-X-DEV-PROD-PARITY | catalog: architecture-check-catalog-sec-5.3 | checkability: tier2-advisory | trap-ref: 5.3
- id: ACC-5-3-XI-LOGS-EVENT-STREAM-NOT-FILES | catalog: architecture-check-catalog-sec-5.3 | checkability: tier1-static | trap-ref: 5.3
- id: ACC-5-3-XII-ADMIN-PROCESSES | catalog: architecture-check-catalog-sec-5.3 | checkability: tier3-not-checkable | trap-ref: 5.3
- id: ACC-5-4-RETRY | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-THROTTLING-RATE-LIMITING | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-CQRS | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-EVENT-SOURCING | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-SAGA | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-COMPENSATING-TRANSACTION | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-OUTBOX-TRANSACTIONAL-OUTBOX | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-IDEMPOTENT-RECEIVER | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-LEADER-ELECTION | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-SIDECAR | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-AMBASSADOR | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-ANTI-CORRUPTION-LAYER | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-STRANGLER-FIG | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-GATEWAY-AGGREGATION-OFFLOADING-ROUTING | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-BACKENDS-FOR-FRONTENDS | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-HEALTH-ENDPOINT-MONITORING | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-COMPETING-CONSUMERS | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-CLAIM-CHECK | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-PIPES-AND-FILTERS | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-MATERIALIZED-VIEW | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-VALET-KEY | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-CACHE-ASIDE | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-SHARDING | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-STATIC-CONTENT-HOSTING | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-QUEUE-BASED-LOAD-LEVELING | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-PRIORITY-QUEUE | catalog: architecture-check-catalog-sec-5.4 | checkability: tier3-not-checkable | trap-ref: 5.4
- id: ACC-5-4-SCHEDULER-AGENT-SUPERVISOR | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-FEDERATED-IDENTITY | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-GATEKEEPER | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-PUBLISHER-SUBSCRIBER | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-SEQUENTIAL-CONVOY | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-ASYNCHRONOUS-REQUEST-REPLY | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-EXTERNAL-CONFIGURATION-STORE | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-BULKHEAD | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-CIRCUIT-BREAKER | catalog: architecture-check-catalog-sec-5.4 | checkability: tier1-static | trap-ref: 5.4
- id: ACC-5-4-CHOREOGRAPHY | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-INDEX-TABLE | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-MESSAGING-BRIDGE | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-QUARANTINE | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-COMPUTE-RESOURCE-CONSOLIDATION | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-DEPLOYMENT-STAMPS | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-4-GEODE | catalog: architecture-check-catalog-sec-5.4 | checkability: tier2-advisory | trap-ref: 5.4
- id: ACC-5-5-RED-USE-GOLDEN-SIGNALS | catalog: architecture-check-catalog-sec-5.5 | checkability: tier1-static | trap-ref: 5.5
- id: ACC-5-5-SLI-SLO-ERROR-BUDGET | catalog: architecture-check-catalog-sec-5.5 | checkability: tier2-advisory | trap-ref: 5.5
- id: ACC-5-5-CORRELATION-IDS | catalog: architecture-check-catalog-sec-5.5 | checkability: tier1-static | trap-ref: 5.5
- id: ACC-5-5-STRUCTURED-LOGGING | catalog: architecture-check-catalog-sec-5.5 | checkability: tier1-static | trap-ref: 5.5
- id: ACC-5-5-CARDINALITY-CONTROL | catalog: architecture-check-catalog-sec-5.5 | checkability: tier1-static | trap-ref: 5.5
- id: ACC-5-6-CAP-PACELC | catalog: architecture-check-catalog-sec-5.6 | checkability: tier3-not-checkable | trap-ref: 5.6
- id: ACC-5-6-ACID-VS-BASE | catalog: architecture-check-catalog-sec-5.6 | checkability: tier2-advisory | trap-ref: 5.6
- id: ACC-5-6-IDEMPOTENCY | catalog: architecture-check-catalog-sec-5.6 | checkability: tier1-static | trap-ref: 5.6
- id: ACC-5-6-DELIVERY-SEMANTICS | catalog: architecture-check-catalog-sec-5.6 | checkability: tier1-static | trap-ref: 5.6
- id: ACC-5-6-EVENTUAL-CONSISTENCY | catalog: architecture-check-catalog-sec-5.6 | checkability: tier2-advisory | trap-ref: 5.6
- id: ACC-5-6-SCHEMA-EVOLUTION-VERSIONING | catalog: architecture-check-catalog-sec-5.6 | checkability: tier1-static | trap-ref: 5.6
- id: ACC-5-6-SINGLE-SOURCE-OF-TRUTH | catalog: architecture-check-catalog-sec-5.6 | checkability: tier1-static | trap-ref: 5.6
- id: ACC-5-6-RETENTION | catalog: architecture-check-catalog-sec-5.6 | checkability: tier2-advisory | trap-ref: 5.6
- id: ACC-5-7-LEAST-PRIVILEGE | catalog: architecture-check-catalog-sec-5.7 | checkability: tier1-static | trap-ref: 5.7
- id: ACC-5-7-DEFENSE-IN-DEPTH | catalog: architecture-check-catalog-sec-5.7 | checkability: tier2-advisory | trap-ref: 5.7
- id: ACC-5-7-FAIL-SECURE | catalog: architecture-check-catalog-sec-5.7 | checkability: tier1-static | trap-ref: 5.7
- id: ACC-5-7-ZERO-TRUST | catalog: architecture-check-catalog-sec-5.7 | checkability: tier2-advisory | trap-ref: 5.7
- id: ACC-5-7-BLAST-RADIUS | catalog: architecture-check-catalog-sec-5.7 | checkability: tier2-advisory | trap-ref: 5.7
- id: ACC-5-7-STRIDE | catalog: architecture-check-catalog-sec-5.7 | checkability: tier3-not-checkable | trap-ref: 5.7
- id: ACC-5-7-ATTACK-SURFACE | catalog: architecture-check-catalog-sec-5.7 | checkability: tier2-advisory | trap-ref: 5.7
- id: ACC-5-8-N-1-QUERIES | catalog: architecture-check-catalog-sec-5.8 | checkability: tier1-static | trap-ref: 5.8
- id: ACC-5-8-CONNECTION-POOLING | catalog: architecture-check-catalog-sec-5.8 | checkability: tier1-static | trap-ref: 5.8
- id: ACC-5-8-BATCHING | catalog: architecture-check-catalog-sec-5.8 | checkability: tier2-advisory | trap-ref: 5.8
- id: ACC-5-8-PAGINATION-UNBOUNDED-RESULT-SETS | catalog: architecture-check-catalog-sec-5.8 | checkability: tier1-static | trap-ref: 5.8
- id: ACC-5-8-BACKPRESSURE | catalog: architecture-check-catalog-sec-5.8 | checkability: tier2-advisory | trap-ref: 5.8
- id: ACC-5-8-LOAD-SHEDDING | catalog: architecture-check-catalog-sec-5.8 | checkability: tier2-advisory | trap-ref: 5.8
- id: ACC-6-NAMING-HEURISTICS-GENERAL | catalog: architecture-check-catalog-sec-6 | checkability: tier3-not-checkable | trap-ref: 6
- id: ACC-6-FIRST-TEST-PRINCIPLES-FAST-ISOLATED-REPEATABLE-SELF-VALIDATING-TIMELY | catalog: architecture-check-catalog-sec-6 | checkability: tier1-static | trap-ref: 6
- id: ACC-6-AAA-ARRANGE-ACT-ASSERT-TEST-STRUCTURE | catalog: architecture-check-catalog-sec-6 | checkability: tier2-advisory | trap-ref: 6
- id: ACC-6-TEST-SMELLS-FRAGILE-TEST-TEST-DUPLICATION-MYSTERY-GUEST-EAGER-TEST-ASSERTI | catalog: architecture-check-catalog-sec-6 | checkability: tier1-static | trap-ref: 6
- id: ACC-6-DOCUMENTATION-DOC-DRIFT | catalog: architecture-check-catalog-sec-6 | checkability: tier1-static | trap-ref: 6
TOTAL: 288
