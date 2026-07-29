<!-- frob:doc src/frob/arch -->
# Design-Pattern and Design-Principle Traps: A Cited Practitioner Corpus

Status: living reference. Feeds T-0330 (arch SOLID / senior-designer checks),
T-0332 (hallmark->pattern + anti-pattern->escape recommender), and T-0341
(conformance). `docs/design/architecture-check-catalog.md` now exists and
its reconciliation is due; `docs/design/structural-linter-adversarial-
hardening.md` still does not -- there is nothing in-repo to reconcile
against for the latter beyond the T-0330/T-0332 ticket text quoted inline
below where a lesson updates the plan described there.

Method: built via the exhaustive-research frontier loop. Universe enumerated
to 21 nodes before any source-hunting (SOLID x5 + SOLID-as-a-whole, DRY/AHA,
YAGNI, inheritance-vs-composition, five GoF-overuse nodes, three
architecture-scale nodes, type-driven/functional-core, and a catch-all
sweep for anemic domain/god object/Law of Demeter/DI containers/repository
pattern). All 21 drained; see reconciliation table at the end.

Confidence key: **High** = named practitioner, primary source, durable URL,
widely cited by the field. **Medium** = credible author/venue but a single
voice or less load-bearing claim. **Folklore** = repeated widely but no
single citable origin found; flagged, not dressed up.

---

## 1. SOLID -- per-letter and as a whole

### 1.0 SOLID as a whole: "SOLID is not solid" / CUPID

- **Intended benefit**: five independent heuristics for OO maintainability,
  packaged as a memorable acronym.
- **The trap**: treating SOLID as *laws* rather than *heuristics that trade
  off against each other*. Applied mechanically, each letter can be
  "satisfied" while making the code worse, and teams cargo-cult the
  acronym instead of asking whether the code got simpler.
- **What practitioners learned**: Dan North (creator of BDD, "Introducing
  BDD") built an entire alternative -- CUPID (Composable, Unix-philosophy,
  Predictable, Idiomatic, Domain-based) -- specifically because he found he
  could refute every SOLID letter "with a straight face," and the
  alternative he kept arriving at was simply *write simple code*. He frames
  CUPID as *properties* to evaluate against, not *principles* to obey,
  because principles invite mechanical application. (dannorth.net,
  "CUPID: the back story", and his talk "SOLID is not solid" / "CUPID --
  for joyful coding".) **High** confidence -- primary author, durable blog,
  widely cited and debated (dev.to, InfraAsCode, Mozaic Works threads all
  respond directly to it).
- **Static hallmark**: none directly -- this is a meta-lesson. The
  actionable form is: any linter that flags "violates SRP/OCP/etc." as a
  hard error rather than an advisory is itself repeating the trap. This is
  the single most important design constraint for T-0330's severity model:
  SOLID checks must be advisory/waivable, never blocking, or the tool
  becomes the thing North is warning about.
- **Sources**: [CUPID: the back story](https://dannorth.net/blog/cupid-the-back-story/) (Dan North, primary); [CUPID vs. SOLID -- Mozaic Works](https://mozaicworks.com/blog/cupid-vs-solid) (secondary, credible consultancy); [How solid is SOLID -- reaction video](https://www.youtube.com/watch?v=latPK1FK3cQ).

### 1.1 SRP -- "one reason to change" is unfalsifiable in practice

- **Intended benefit**: isolate change so a modification to one concern
  doesn't ripple into unrelated code.
- **The trap**: "reason to change" has no operational definition, so SRP
  becomes whatever the reviewer wants it to mean. Taken to its logical
  extreme it justifies splitting every class into one class per method
  ("SRP-itis"), producing a maze of tiny classes that is harder to
  navigate than the "god class" it replaced.
- **What practitioners learned**: the LMAX Technology blog ("The Single
  Responsibility Principle (and what's wrong with it)") argues a "reason
  to change" can be *anything* -- is a bug fix a reason to change? -- and
  that the principle gives no rigorous way to decide what a
  "responsibility" is, leaving it entirely to individual judgment, which
  means two competent engineers will draw the boundary in different places
  and both cite SRP as justification. Independently, sklivvz ("I don't
  love the single responsibility principle") makes the same core
  complaint: SRP treats "one reason to change" as self-evidently better
  than "N reasons to change," when in reality "these things always change
  together for the business" is an equally valid modularization criterion
  that SRP has no vocabulary for. **Medium** confidence -- credible
  engineering-org blog (LMAX is a well-known low-latency trading
  engineering shop) and an independent named author making the same
  argument from a different angle; not as canonical as North/Metz but a
  real, substantive critique, not a listicle.
- **Static hallmark**: this is the inverse of most smells -- the danger
  signal is *not* a single metric but a **class-count-to-cohesion-drop
  ratio**: a refactor that increases file/class count without a
  corresponding decrease in cross-file call-graph coupling. A recommender
  should treat "N reasons to change" splits (classes that co-occur in
  every commit, per git blame/co-change history) as a signal *against*
  further SRP decomposition, not for it. This directly qualifies T-0330:
  an SRP check that counts responsibilities via heuristics (method count,
  LOC) without a co-change signal will false-positive on exactly the
  cohesive-but-multi-purpose classes that shouldn't be split.
- **Sources**: [The Single Responsibility Principle (and what's wrong with it) -- LMAX](https://technology.lmax.com/posts/the-single-responsibility-principle-and-what-s-wrong-with-it/); [I don't love the single responsibility principle -- sklivvz](https://sklivvz.com/posts/i-dont-love-the-single-responsibility-principle).

### 1.2 OCP -- premature extensibility hooks

- **Intended benefit**: extend behavior without modifying existing,
  already-tested code.
- **The trap**: building the extension point (strategy interface, plugin
  hook, abstract base) *before* a second concrete case actually exists.
  This is OCP collapsing into speculative generality -- the abstraction is
  built for a future that may never arrive, and it has ongoing cost
  (indirection, an extra file, a vtable to trace through) whether or not
  the second case shows up.
- **What practitioners learned**: even Robert C. Martin, OCP's most
  prominent modern advocate, wrote in his original Engineering Notebook
  column that "resisting premature abstraction is as important as
  abstraction itself" -- i.e., the OCP author himself flags premature
  application as the failure mode, not a strawman critics invented.
  thevaluable.dev's "Should We Follow The Open-Closed Principle?" makes
  the practical case explicit: prefer *flexibility* (code that's easy to
  change later) over *extensibility* (hooks built in advance for change
  that hasn't been asked for), because the latter is a bet you usually
  lose. **Medium** confidence for the secondary source; **High** for the
  Martin quote since it is the principle's own primary author qualifying
  it.
- **Static hallmark**: an interface/abstract-base with exactly one
  concrete implementation and no second implementation anywhere in the
  dependency graph, especially one introduced in the same commit as its
  sole implementer ("Impl-suffix singleton hierarchy"). This is a
  directly detectable structural signal: `count(implementations) == 1 AND
  age(interface) == age(only_impl)`.
- **Sources**: [The Open-Closed Principle (Engineering Notebook, Robert C. Martin, PDF)](http://objectmentor.com/resources/articles/ocp.pdf) (primary, canonical); [Should We Follow The Open-Closed Principle? -- thevaluable.dev](https://thevaluable.dev/open-closed-principle-revisited/).

### 1.3 LSP -- the rectangle/square problem is the canonical, load-bearing example

- **Intended benefit**: subtypes must be substitutable for their base type
  without surprising callers -- behavioral, not just signature, compatibility.
- **The trap**: modeling an "is-a" relationship from the *domain* (a
  square mathematically is a rectangle) instead of the *behavioral
  contract* (a Rectangle's contract lets width and height vary
  independently; a Square's can't). The inheritance looks obviously
  correct and still breaks every caller that assumes the base contract.
- **What practitioners learned**: this example, attributed across
  multiple independent write-ups (InfoWorld's "Exploring the Liskov
  Substitution Principle," DZone, and Barbara Liskov's own 1988 "Data
  Abstraction and Hierarchy" formulation of "what is wanted here is
  ... IS-A"), is now the standard teaching tool precisely because
  intuition about type hierarchies (from domain modeling) and behavioral
  substitutability (from contract preservation) diverge in exactly this
  case. The consistent fix practitioners converge on: prefer composition
  or a shared non-inheriting `Shape` interface over forcing an
  inheritance relationship the behavior doesn't support. **High**
  confidence -- this is the textbook example precisely because it recurs
  independently across every treatment of LSP, and the principle
  originates with Liskov herself.
- **Static hallmark**: a subclass that overrides a mutator/setter to
  narrow its post-condition (e.g. `setWidth` also mutates `height`), or
  that overrides a method to throw where the base method didn't
  (`NotSupportedException` overrides) -- both are grep-able:
  co-assignment of two fields in one setter that the base class assigns
  independently, or a method body whose only statement is `raise` inside
  an override.
- **Sources**: [Exploring the Liskov Substitution Principle -- InfoWorld](https://www.infoworld.com/article/2252806/exploring-the-liskov-substitution-principle.html); Barbara Liskov, "Data Abstraction and Hierarchy," SIGPLAN Notices 23,5 (1988) (primary, foundational, pre-dates the SOLID acronym itself).

### 1.4 ISP -- fat interfaces force dummy implementations

- **Intended benefit**: clients shouldn't depend on methods they don't use.
- **The trap**: a single "capability" interface accretes methods for every
  client that ever needed *anything*, forcing every implementer to stub
  out methods it can't meaningfully support (throwing
  `NotImplementedException`, or silently no-op-ing).
- **What practitioners learned**: the original Xerox printer example (from
  the ISP literature that predates SOLID's naming, cited consistently
  across oodesign.com, Tom Dalling's SOLID series, and reflectoring.io) --
  a `Job` interface with staple/print/fax/scan methods forces a
  print-only device to implement staple/fax/scan as no-ops. The uniform
  fix: split by *client usage pattern*, not by "logical" grouping of the
  underlying subject.
- **Static hallmark**: a method whose entire body is
  `throw NotSupportedException` / `raise NotImplementedError` / a bare
  `pass`/no-op, especially when this pattern recurs across multiple
  implementers of the same interface -- that is a fat-interface signal
  the recommender can flag directly (interface `I` needs splitting when
  >= 2 implementers each stub out a disjoint, non-overlapping subset of
  `I`'s methods).
- **Sources**: [Interface Segregation Principle -- oodesign.com](https://www.oodesign.com/interface-segregation-principle) (secondary but the standard reference incl. Xerox origin story); [SOLID Class Design: ISP -- Tom Dalling](https://www.tomdalling.com/blog/software-design/solid-class-design-the-interface-segregation-principle/).

### 1.5 DIP -- interface-per-implementation explosion

- **Intended benefit**: high- and low-level modules both depend on an
  abstraction, not on each other directly, so the low-level module can be
  swapped without touching the high-level one.
- **The trap**: mechanically wrapping every concrete class in an interface
  "for DIP" even when there is, and will only ever be, one implementation
  -- pure ceremony that adds an indirection hop with no actual inversion
  benefit (nothing is ever substituted). This compounds directly with the
  DI-container trap below: containers make it *cheap* to wire N interfaces,
  which removes the friction that would otherwise make an engineer ask
  "do I need this abstraction."
  Note: direct search for a named "interface explosion" essay came back
  general DIP explainer pages, not a single canonical practitioner post --
  flagging this sub-claim itself as **folklore/pattern-recognized-but-
  not-singly-cited**, though it is the same underlying phenomenon Ayende
  Rahien documents concretely for Abstract Factory (see 5.2) and ploeh
  documents for DI containers (see 5.6): interfaces created for
  hypothetical substitutability that never materializes.
- **Static hallmark**: an interface with exactly one implementer AND no
  test double/mock that substitutes a second implementation anywhere in
  the test suite -- if nothing, not even a test, ever exercises a second
  implementation, the "inversion" bought nothing. (Same detector shape as
  1.2's OCP hallmark -- DIP-for-a-single-impl and OCP-for-a-single-impl
  are structurally the same smell wearing different names.)
- **Sources**: [Dependency Inversion Principle -- Wikipedia](https://en.wikipedia.org/wiki/Dependency_inversion_principle) (definitional, not a trap source); cross-referenced against Ayende's Abstract Factory post and ploeh's DI-container post below, which document the concrete mechanism. **Folklore** flag noted above.

---

## 2. DRY and abstraction

### 2.1 Sandi Metz -- "the wrong abstraction is worse than duplication"

- **Intended benefit**: DRY (Don't Repeat Yourself) eliminates the
  maintenance hazard of two copies of the same logic drifting out of sync.
- **The trap**: Programmer A sees duplicate-looking code, extracts a
  shared abstraction. Programmer B later needs behavior that's *almost*
  the same but not quite, and rather than break the abstraction, adds a
  parameter and a conditional branch inside the shared code to handle the
  new case. Repeat this a few times and the "abstraction" is a tangle of
  flags and branches serving multiple unrelated call sites -- worse than
  if the duplication had simply been left alone.
- **What practitioners learned**: Sandi Metz, "The Wrong Abstraction"
  (sandimetz.com, 2016, following her 2014 RailsConf talk that originated
  the line): "duplication is far cheaper than the wrong abstraction," and
  her prescribed fix is *inline the abstraction back into every caller and
  let the duplication re-emerge* -- deliberately reversing the DRY
  extraction -- because re-introduced duplication shows you what the
  *right* abstraction actually is, whereas patching the wrong one forward
  only accretes more special cases. This is a **High**-confidence,
  extremely widely-cited primary source -- practically the canonical text
  on this trap. Worth noting the corpus also surfaced a substantive
  *rebuttal*: "Why I don't buy 'duplication is cheaper than the wrong
  abstraction'" (codewithjason.com) argues Metz's prescription undersells
  how expensive re-duplication is at scale and that the real skill is
  recognizing the wrong abstraction *before* extraction, not after --
  included here because a corpus that only cites the popular claim without
  its live rebuttal would itself be the kind of shallow coverage the user
  is filtering for.
- **Static hallmark**: a shared function/method whose parameter list has
  grown a boolean flag or an enum that branches its internal control flow
  by *caller identity* rather than by *domain logic* (e.g.
  `def render(self, is_admin_view: bool)`), especially when call sites
  pass a compile-time-constant literal for that flag -- that's dead
  giveaway evidence the flag exists to route between what should be two
  functions.
- **Sources**: [The Wrong Abstraction -- Sandi Metz](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction) (primary); [Why I don't buy "duplication is cheaper than the wrong abstraction" -- Code with Jason](https://www.codewithjason.com/duplication-cheaper-wrong-abstraction/) (rebuttal, credible working practitioner blog).

### 2.2 AHA / WET and premature abstraction

- **Intended benefit**: the corrective to 2.1 -- "Avoid Hasty Abstractions"
  (Kent C. Dodds's coinage, popularized in the React/frontend community)
  argues for staying duplicated ("Write Everything Twice/write
  Every Time" -- WET, the deliberate DRY-antonym) until a *third*
  occurrence proves the pattern is real, per the informal "rule of three."
- **What practitioners learned**: the AHA framing exists specifically
  because Metz's essay (2.1) was read by many teams as "DRY is bad," which
  overcorrects into never abstracting at all. AHA's actual claim is
  narrower and more useful: prefer duplication over the *wrong*
  abstraction, but that doesn't mean prefer duplication over *any*
  abstraction -- optimize for ease of change, and abstract once the shape
  is proven by repetition, not on the first sighting of similar code.
  **Medium** confidence -- well-known in the frontend community, Kent C.
  Dodds is a credible, widely-published practitioner (Epic React,
  Testing Library maintainer), but this is closer to a popularized
  heuristic than a single definitive essay with heavy independent
  citation the way Metz's is.
- **Static hallmark**: an extraction commit where the shared function is
  called from exactly 2 call sites at the moment of extraction (the
  "rule of three" is violated at the structural level -- a detector can
  literally count call sites at extraction time from git history).
- **Sources**: this node is reported at **Medium/folklore-adjacent**
  confidence -- AHA is widely referenced but a single canonical Dodds
  essay URL was not independently re-verified via WebFetch in this pass;
  flagging rather than asserting a specific link with unverified
  provenance.

---

## 3. YAGNI / speculative generality / gold-plating

- **Intended benefit**: don't build capability for requirements that
  haven't materialized -- every line of speculative code is maintenance
  burden paid before it's earned.
- **The trap**: "just in case" flexibility -- config options nobody sets,
  plugin systems with one plugin, parameters that are always passed the
  same value -- that reads as diligence but is actually cost with no
  offsetting benefit, and worse, it *hides* the actual requirements under
  a layer of generality, making the code harder to reason about for
  everyone who has to read past the unused flexibility to find the real
  logic.
- **What practitioners learned**: Kent Beck coined "You Aren't Gonna Need
  It" during the Chrysler C3 project in the late 1990s (documented
  history, not folklore -- multiple independent XP-era retrospectives
  converge on this origin). Martin Fowler named the code smell
  "Speculative Generality" in *Refactoring* (1999) as the concrete,
  detectable form YAGNI violations take in code, and later wrote a bliki
  entry laying out a four-part cost model: (1) the labor of building the
  unused feature, (2) the ongoing cost of the speculative code sitting in
  the tree complicating every future change until it's used or deleted,
  (3) delayed feedback because the effort went to speculation instead of
  what's actually needed now, and (4) the review/debugging tax that extra
  branches and extension points impose on unrelated changes. Fowler
  explicitly caveats that YAGNI only works *with* continuous refactoring
  and strong test coverage as a safety net -- without those, deferring
  design decisions just produces disorganized code, which is the
  counter-argument gold-plating advocates use. **High** confidence --
  Beck and Fowler are both primary, named, foundational sources.
- **Static hallmark**: a config field, constructor parameter, or
  interface method with exactly one call-site value across the entire
  codebase and test suite (a boolean that is always `True`, a strategy
  interface with exactly one registered strategy, a plugin hook with zero
  registered plugins) -- directly the same detector shape as OCP's
  hallmark (1.2), which is not a coincidence: YAGNI violations and
  premature-OCP hooks are the same code shape viewed from two angles.
- **Sources**: [YAGNI -- Martin Fowler (bliki)](https://enersys.co.th/en/insights/yagni-principle-software-engineering-2026) cross-referenced; canonical Fowler bliki entry on speculative generality is part of *Refactoring* (Addison-Wesley, 1999), primary published source; [Speculative Generality -- XP123](https://xp123.com/speculative-generality/) (secondary, William Wake's XP123 site, a long-running and credible XP-community reference).

---

## 4. Inheritance vs composition; fragile base class

- **Intended benefit**: inheritance promises reuse -- write the shared
  behavior once in a base class, get it for free in every subclass.
- **The trap**: the **fragile base class problem** -- subclasses depend
  not just on the base class's *public interface* but on its *undocumented
  internal call structure* (which methods call which other methods
  internally). A change to the base class's internals that preserves its
  public contract can still silently break every subclass that happened
  to depend on the old internal call order, because nothing in the
  contract promised that order wouldn't change. This makes refactoring
  the base class dangerous in a way that isn't visible from reading the
  base class alone -- you have to audit every subclass.
- **What practitioners learned**: Ted Kaminski (tedinski.com, "What's
  wrong with inheritance?") gives the precise mechanism: base classes
  specify their public interface but not a specification of *how their
  own methods use each other internally*, so subclasses end up depending
  on implementation accidents, and "almost any change in behavior could
  break subclass behavior." This is why "favor composition over
  inheritance" (GoF's own guidance, restated as a first-class principle by
  the wider community since) works: a component held by reference has an
  explicit, contractual interface with no hidden internal-call coupling --
  you can change its internals freely as long as the interface holds.
  **Medium-High** -- tedinski's is a substantive, technically precise
  independent treatment; the fragile-base-class term itself is decades-old
  and well-documented (traces to Mikhajlov & Sekerinski's 1998 formal
  treatment, not surfaced verbatim in this pass but the term's academic
  pedigree is well known and consistent with what tedinski documents).
- **Static hallmark**: a base-class method rewrite that changes which of
  its own other methods it calls (call-graph delta within the class)
  where subclasses override one of the *called* methods -- that's a
  structurally detectable break: `base.methodA()` used to call
  `self.methodB()`, now calls `self.methodC()` directly, and a subclass
  overrides `methodB` expecting it to still be in the call path. A
  call-graph-diff check on base-class internals versus subclass override
  sets is directly actionable for T-0330/T-0332's shared call-graph
  pillar.
- **Sources**: [What's wrong with inheritance? -- Ted Kaminski](https://www.tedinski.com/2018/02/13/inheritance-modularity.html) (Medium-High, substantive independent technical writing); [Fragile Base Class Problem: Composition over Inheritance -- Pratik Pandey](https://pratikpandey.substack.com/p/fragile-base-class-problem-composition) (Medium, corroborating secondary source).

---

## 5. GoF pattern overuse / cargo-culting

### 5.1 Singleton -- global state in a trenchcoat

- **Intended benefit**: guarantee exactly one instance of a class exists,
  with a well-known global access point.
- **The trap**: Singleton is a global variable with extra ceremony. It
  introduces shared mutable state accessible from anywhere, which breaks
  test isolation (state persists across tests unless manually reset,
  and tests can't run concurrently against the same singleton without
  interfering), hides a class's real dependencies (a method that secretly
  reaches into `Singleton.instance()` "lies" about what it needs when you
  read its signature), and forces every caller into the same lifecycle
  the singleton chose, removing the caller's ability to substitute a
  different instance in a different context (e.g. tests, multi-tenant
  configs).
- **What practitioners learned**: Michael Feathers (*Working Effectively
  with Legacy Code*, widely cited in multiple secondary sources found in
  this pass) documents specifically how Singletons defeat testability by
  making it impossible to substitute a fake without global-state
  workarounds. The GoF book itself (*Design Patterns*, Gamma/Helm/
  Johnson/Vlissides, 1994) is frequently invoked as having "warned against
  overuse" even as it canonized the pattern -- the corpus found this claim
  repeated consistently (GeeksforGeeks, Medium writeups) but did not
  independently re-verify the exact GoF book passage in this pass, so
  treat the "GoF warned against it" specific claim as **Medium**
  confidence pending primary-text verification, while the Feathers
  testability critique and Uncle Bob's "singleton is global state in
  disguise" framing are **High** confidence, well-attested, independently
  repeated critiques from named, credible sources.
- **Static hallmark**: a module-level or class-level mutable instance
  reached via a bare `getInstance()`/`instance()` accessor with no
  constructor-injection alternative anywhere in the codebase -- directly
  detectable as: class `X` has a static factory method returning a
  memoized instance, AND no test file constructs `X` directly (evidence
  that tests, too, are forced through the singleton).
- **Sources**: [The Singleton Anti-Pattern -- Gedeon Dominguez Toran, Medium](https://medium.com/@gedeon.dominguez/the-singleton-anti-pattern-3c8a46499f0d) (secondary, corroborating); Michael Feathers, *Working Effectively with Legacy Code* (Prentice Hall, 2004) (primary, referenced via multiple secondary sources -- not independently re-fetched this pass).

### 5.2 AbstractFactory / Factory explosion

- **Intended benefit**: decouple client code from concrete class
  construction, and let a whole *family* of related concrete classes be
  swapped together.
- **The trap**: reaching for Abstract Factory whenever *any* object
  construction is involved, even when there is only ever one family of
  products and no plausible second family on the horizon -- the pattern's
  entire value proposition (swap families) never gets exercised, and you
  pay for a factory-of-factories that a plain constructor call would have
  done identically.
- **What practitioners learned**: Ayende Rahien ("Design patterns in the
  test of time: Abstract Factory") -- a well-known, credible .NET/RavenDB
  architect who has written extensively and critically about pattern
  overuse -- documents that Abstract Factory is "prone to overuse,"
  specifically flagging that developers start using it "anytime you need
  to create objects" without asking whether interchangeable *families* of
  products actually exist in the problem; when there's only ever one
  implementation per interface, the factory adds verbosity with zero
  behavioral payoff. **High** confidence -- named, credible, widely-read
  practitioner author with direct primary-source commentary.
- **Static hallmark**: an `AbstractXFactory` / `IXFactory` interface with
  exactly one concrete factory implementer in the whole codebase --
  same shape as the OCP/DIP single-implementer hallmarks above (1.2, 1.5),
  reinforcing that this is one structural smell recurring under several
  pattern names.
- **Sources**: [Design patterns in the test of time: Abstract Factory -- Ayende Rahien](https://ayende.com/blog/159361/design-patterns-in-the-test-of-time-abstract-factory) (primary, named credible author); [Abuse of Abstract Factories -- Manning (Dependency Injection in .NET, 2nd ed. excerpt)](https://freecontent.manning.com/dependency-injection-in-net-2nd-edition-abuse-of-abstract-factories/) (secondary, book-excerpt, Mark Seemann's DI book is a standard reference in the .NET community).

### 5.3 Visitor -- rigid against new types (the Expression Problem)

- **Intended benefit**: add a new *operation* over a fixed family of
  types without touching any of the types themselves -- each new
  operation is one new Visitor class.
- **The trap**: the pattern's flexibility is asymmetric and often
  mis-sold as general-purpose. It buys ease of adding *operations* at the
  direct cost of making it hard to add *types* -- every new type in the
  hierarchy requires a new `visit` method on every existing Visitor
  implementation. Teams reach for Visitor by pattern-name recognition
  ("we're dispatching over a type hierarchy, GoF says Visitor") without
  checking whether their actual axis of change is types (in which case
  Visitor is precisely backwards) or operations (in which case it fits).
- **What practitioners learned**: this is formally named the **Expression
  Problem** in PL theory -- in a functional language, types are fixed and
  operations are easy to add; in an OO language with Visitor, operations
  are fixed and types are easy to add, but you can't have both without
  extra machinery. A named framing: "add a new operation? You are forced
  to edit an abstract base class and every implementation. Extend
  behavior? You're forced to touch code and rewrite classes you promised
  you'd never change" -- i.e. Visitor's promise of OCP-compliance is a lie
  along the type axis even as it delivers along the operation axis. The
  consensus practitioner guidance found across multiple independent
  writeups: use Visitor only on type hierarchies that are structurally
  frozen (e.g. a compiler's fixed AST node set, a fixed file-format's
  fixed record types) -- **Medium** confidence on the specific named
  sources found (blog-tier, not a single towering canonical essay), but
  **High** confidence on the underlying Expression Problem framing, which
  is a well-established PL-theory term with deep, independently
  verifiable literature (Wadler's original 1998 formulation, referenced
  consistently across the field even though not directly re-fetched this
  pass).
- **Static hallmark**: a `visit(NodeType)` method added to *every*
  existing `XVisitor` implementation in the same commit that introduces a
  new `NodeType` subclass -- a fan-out commit touching N files (one per
  existing visitor) for a single new type is the exact structural
  fingerprint of Visitor's type-axis rigidity, directly countable from
  commit history.
- **Sources**: [Your Class Hierarchy Is Not a Dumping Ground -- Use Visitor Design Pattern, Maxim Gorin (Medium)](https://maxim-gorin.medium.com/your-class-hierarchy-is-not-a-dumping-ground-use-visitor-design-pattern-87030dfac874); [Visitor Pattern Versus Multimethods](https://nice.sourceforge.net/visitor.html) (academic/language-design source, Nice language project, credible PL context); Expression Problem, folklore term traced to Philip Wadler's 1998 email to the java-genericity mailing list (widely cited in PL literature, not independently re-fetched this pass -- flagged accordingly).

### 5.4 Strategy/Observer over-eagerness and "pattern-itis": FizzBuzzEnterpriseEdition

- **Intended benefit**: Strategy decouples an algorithm family behind a
  common interface so it can vary at runtime; Observer decouples a
  subject from its dependents so notification doesn't require tight
  coupling.
- **The trap**: applying GoF patterns as a *default* engineering posture
  rather than in response to an actual, demonstrated need for the
  flexibility they buy -- producing systems where trivial logic (FizzBuzz)
  is buried under Strategy classes, Factory classes, dependency-injection
  wiring, and Visitor traversal, and a one-line change requires touching
  a dozen files. This is the community's own satirical self-critique --
  the project exists *because* practitioners recognized the pattern in
  real enterprise codebases and needed a name for it.
- **What practitioners learned**: `EnterpriseQualityCoding/
  FizzBuzzEnterpriseEdition` (open-source GitHub project, satire but
  functioning code, extremely widely referenced across the industry as
  shorthand for "pattern-itis") demonstrates concretely how Strategy +
  Factory + Visitor + Spring-style DI, applied reflexively to a
  three-line problem, produces something that "burns hundreds of
  developer-hours for even tiny changes." **High** confidence as a
  cultural/pedagogical artifact -- it is cited constantly across the
  industry specifically as the canonical cautionary tale, even though
  it's satire rather than a postmortem essay.
- **Static hallmark**: a Strategy interface (or Observer subject) with a
  runtime-selected implementation count of 1 (only ever one concrete
  strategy registered/selected across all call sites) -- again the same
  single-implementer detector as 1.2/1.5/5.2, which by this point in the
  corpus is clearly the single most common structural fingerprint across
  *all* GoF-overuse traps: **the pattern was applied where variability
  never materialized.**
- **Sources**: [FizzBuzzEnterpriseEdition -- GitHub/DeepWiki summary](https://deepwiki.com/EnterpriseQualityCoding/FizzBuzzEnterpriseEdition) (primary artifact, satirical but the code itself is the evidence); [Notes on Design Patterns -- vladris.com](https://vladris.com/blog/2020/12/10/notes-on-design-patterns.html) (secondary, credible independent commentary referencing the same phenomenon).

### 5.5 Observer -- the lapsed listener problem (memory leak by design)

- **Intended benefit**: a subject notifies an open-ended set of observers
  without knowing their concrete types, decoupling producer from
  consumers.
- **The trap**: the subject holds *strong* references to its observers by
  default. An observer that forgets to unsubscribe when it's done stays
  referenced forever, so it (and everything it in turn references) can
  never be garbage collected -- a leak that grows over the *application's*
  lifetime, not the observer's, making it exactly the kind of slow leak
  that's hard to notice in dev and shows up as a production incident
  after days of uptime.
- **What practitioners learned**: this is formally named the "lapsed
  listener problem" (documented independently on Wikipedia and multiple
  practitioner writeups), and the standard mitigation is weak references
  for the subject-to-observer edge, or an explicit, enforced
  unsubscribe-on-teardown contract. In Node.js/JS specifically,
  unreleased `EventEmitter` listeners are cited as "the main source of
  memory leaks" in that ecosystem, precisely because Observer (via
  event emitters) is the community's default idiom for decoupling, so its
  failure mode is disproportionately common there. **Medium-High** --
  well-documented, named phenomenon with a Wikipedia-level canonical
  description plus consistent independent corroboration, though no single
  named "practitioner essay" origin was surfaced in this pass.
- **Static hallmark**: a `subscribe`/`addListener`/`on()` call with no
  corresponding `unsubscribe`/`removeListener`/`off()` call reachable
  from the same object's teardown/destructor/cleanup path -- an
  asymmetric registration-without-matching-deregistration pair is
  directly greppable per subscriber class.
- **Sources**: [Lapsed listener problem -- Wikipedia](https://en.wikipedia.org/wiki/Lapsed_listener_problem) (definitional, widely corroborated); [What is a Memory Leak? How Memory Leaks Are Associated with the Observer Pattern -- Dev Corner, Medium](https://medium.com/@devcorner/what-is-a-memory-leak-how-memory-leaks-are-associated-with-the-observer-pattern-dbd12898f2b9) (secondary, corroborating).

### 5.6 Dependency-injection containers -- "magic" that hides invariants

- **Intended benefit**: automate the wiring of dependencies so
  constructors don't have to be assembled by hand at every call site.
- **The trap**: once a DI container is in place, it becomes *cheaper* to
  add another interface/abstraction than to ask whether one is needed --
  the container absorbs the friction that would otherwise make an
  engineer stop and think. The result: invariants that used to be visible
  at the constructor call site (this object needs exactly these three
  things, provided right here) get pushed out into container
  configuration/annotations, so you can no longer read a class's file and
  know what it needs -- you have to trace the container's registration
  graph, and you often can't even instantiate a class manually in a
  quick script or a REPL without first spinning up the whole container
  context.
- **What practitioners learned**: Yegor Bugayenko ("Dependency Injection
  Containers are Code Polluters," yegor256.com) -- a well-known, opinionated,
  widely-read OOP-purist practitioner blogger -- argues DI containers
  specifically pollute code by encouraging exactly the promiscuous
  interface-creation described in 1.5/5.2 above, because the container
  makes the *cost* of an extra abstraction invisible at the call site.
  Mark Seemann (ploeh blog, "When to use a DI Container," author of the
  standard reference book *Dependency Injection in .NET* excerpted in
  5.2) gives the more measured, still-critical framing: DI containers are
  a convenience for *large* object graphs, and for anything smaller,
  "Pure DI" (hand-wiring constructors) is not just acceptable but often
  clearer, because the wiring is visible, ordinary code instead of
  configuration. **High** confidence on both -- named, primary, widely-
  read, credible authors, one a book author on this exact topic.
- **Static hallmark**: a class whose constructor cannot be called with
  literal/inline arguments from a test file without invoking a container
  bootstrap function first -- i.e., zero test files in the suite
  construct the class via `new X(...)`/`X(...)` directly; all
  construction flows through a container/context resolve call. This is a
  direct, checkable proxy for "this class's dependencies are invisible
  without tracing the container."
- **Sources**: [Dependency Injection Containers are Code Polluters -- Yegor Bugayenko](https://www.yegor256.com/2014/10/03/di-containers-are-evil.html) (primary, named, prolific/credible author); [When to use a DI Container -- Mark Seemann (ploeh blog)](https://blog.ploeh.dk/2012/11/06/WhentouseaDIContainer/) (primary, named author of the standard .NET DI reference book).

---

## 6. Architecture-scale El Dorados

### 6.1 Clean / Hexagonal / Onion architecture overkill

- **Intended benefit**: isolate business logic from frameworks, databases,
  and UI behind ports/adapters, so the domain can be tested and evolved
  independent of infrastructure choices.
- **The trap**: applying the full layered-ports-and-adapters ceremony
  (use-case interactors, port interfaces, DTOs at every boundary,
  presenter/gateway layers) to small applications where infrastructure was
  never actually going to change -- turning a 3-file CRUD app into
  15 files across 5 layers for no realized benefit, with every trivial
  feature now requiring edits in multiple layers to thread a single field
  through.
- **What practitioners learned**: Three Dots Labs ("Is Clean Architecture
  Overengineering?") -- a well-regarded Go/software-architecture
  consultancy blog -- directly poses and answers the question practitioners
  actually argue about, concluding the pattern earns its cost only past a
  complexity threshold most small apps never reach. A widely-shared
  practitioner heuristic found independently across multiple sources in
  this pass: "if you've got fewer than five endpoints, Hex is overkill."
  James Michael Hickey's "Clean Architecture Disadvantages" makes the
  more general point that developers spend design time on architecture
  ceremony instead of shipping functionality, and that "adding layers and
  ports can make things more complex" even when the intent was
  simplicity. **Medium** confidence -- credible, named practitioner
  sources, though this corner of the corpus is closer to a live, ongoing
  community debate than a single settled essay (unlike Metz/Fowler/North
  above, no single author's take has become *the* canonical reference).
- **Static hallmark**: a "port" interface (e.g. `UserRepositoryPort`)
  with exactly one adapter implementation and no test double swapped in
  for it -- same single-implementer detector family as 1.2/1.5/5.2/5.4,
  now at the architecture-layer granularity rather than the class
  granularity. A useful additional signal specific to this trap: DTO/
  mapping-struct classes whose field lists are 1:1 identical to the
  domain entity they wrap (pure pass-through mapping with zero added or
  removed fields across every boundary crossing) indicate the layering
  isn't earning anything at that boundary.
- **Sources**: [Is Clean Architecture Overengineering? -- Three Dots Labs](https://threedots.tech/episode/is-clean-architecture-overengineering/) (primary, named consultancy with public engineering track record); [Clean Architecture Disadvantages -- James Michael Hickey](https://www.jamesmichaelhickey.com/clean-architecture/) (secondary, named practitioner author).

### 6.2 Microservices-when-you-needed-a-monolith

- **Intended benefit**: independent deployability, per-service scaling,
  and team-boundary alignment with service boundaries.
- **The trap**: adopting microservices *before* the domain's real service
  boundaries are known, paying the "microservices premium" (network
  calls where function calls used to be, distributed transactions,
  cross-service testing, deployment orchestration) for a system that
  hasn't yet grown large enough to need independent scaling or team
  isolation -- and getting the boundaries wrong anyway because you drew
  them before you understood the domain, which is *harder* to fix once
  it's crystallized into separately-deployed services with their own data
  stores.
- **What practitioners learned**: this is Martin Fowler's own
  "MonolithFirst" bliki entry (martinfowler.com) -- primary, canonical,
  extremely widely cited: "almost all the successful microservice
  stories have started with a monolith that got too big and was broken
  up, while almost all the cases where a system was built as a
  microservice system from scratch have ended up in serious trouble."
  His stated mechanism is exactly the boundary-discovery problem above:
  "even experienced architects working in familiar domains have great
  difficulty getting boundaries right at the beginning." Segment's
  published postmortem (InfoQ coverage of their own engineering writeup)
  is the concrete, numbers-backed case study: they split into 140+
  microservices, then consolidated back to a monolith, and their test
  suite runtime dropped from one hour to milliseconds, three engineers
  who'd been fighting service reliability moved back to product work, and
  shipped feature count rose from 32/year to 46/year post-consolidation.
  **High** confidence on both -- Fowler is the field's most-cited
  architecture writer for exactly this reason, and Segment's is a named
  company with a public, numbers-backed engineering postmortem, not an
  anonymous "we regret microservices" blog post.
- **Static hallmark**: not code-local (this is a system-architecture
  trap, not a single-repo structural one) -- the closest static proxy is
  *inter-service call graph density relative to service count*: N
  services where a large fraction of all cross-service calls are
  synchronous request/response chains more than 2 hops deep is a
  structural signal the "services" are really one distributed monolith
  that hasn't been allowed to be a monolith.
- **Sources**: [bliki: MonolithFirst -- Martin Fowler](https://martinfowler.com/bliki/MonolithFirst.html) (primary, canonical); [Why Segment Returned to a Monolith from Microservices -- InfoQ](https://www.infoq.com/news/2018/07/segment-microservices/) (primary company postmortem coverage, named company, numbers-backed).

### 6.3 Premature CQRS / event sourcing

- **Intended benefit**: CQRS (Command Query Responsibility Segregation)
  lets read and write models scale and evolve independently; event
  sourcing gives a full audit log and lets state be reconstructed from
  history rather than a single mutable row.
- **The trap**: adopting both patterns because they were encountered in a
  book or conference talk about how large companies operate, without a
  concrete problem (differing read/write scale requirements, a genuine
  audit/compliance need) that they solve -- for a simple CRUD domain, the
  result is 2-3x the code complexity and often *worse* latency (event
  replay, eventual consistency between the write and read models) than
  the direct-CRUD system it replaced, applied by a team with a fraction
  of the distributed-systems staffing the pattern assumes.
- **What practitioners learned**: a widely-corroborated cautionary essay
  found in this pass (Medium, "Event Sourcing Looked Perfect in the Book.
  Production Was a Nightmare.") makes the staffing-mismatch point
  concretely: the author's team had "4 backend developers and a product
  manager" attempting a pattern whose reference implementations assume
  "50 engineers per service and dedicated PhD-level distributed systems
  experts." The consistent practitioner guidance across multiple
  independent sources in this pass (HackerNoon's "Lessons Learned
  Building Distributed Systems with CQRS and Event Sourcing," Patrick Lee
  Scott) converges on a single gating question before adopting either
  pattern: "do I have a specific problem this solves" -- if you can't
  name a concrete driver (differing read/write scaling need, or a real
  audit-trail requirement), you don't yet need it. **Medium** confidence
  -- credible, substantive, first-person practitioner accounts, but this
  corner of the corpus (unlike 6.2's Fowler/Segment pairing) doesn't have
  one dominant, singularly-canonical source; it's a consistent chorus of
  independent postmortems rather than one authoritative essay.
- **Static hallmark**: an event store / event-sourced aggregate where the
  *current-state read path* still queries the event store directly
  (rather than a materialized read-model/projection) -- i.e., CQRS was
  adopted in name (separate command/write path) but the read side was
  never actually built, meaning the team is paying event-sourcing's full
  write-side complexity tax while getting none of CQRS's read-side
  benefit. Directly detectable: presence of an event-append write path
  with no corresponding projection/read-model table or cache being
  updated from it.
- **Sources**: [Event Sourcing Looked Perfect in the Book. Production Was a Nightmare. -- Medium](https://medium.com/lets-code-future/event-sourcing-looked-perfect-in-the-book-production-was-a-nightmare-04c15eb5cea8) (Medium confidence, named first-person account, publication venue is a personal/independent blog aggregator rather than a well-known engineering org, so treat as corroborating rather than singularly authoritative); [Lessons Learned Building Distributed Systems with CQRS and Event Sourcing -- Patrick Lee Scott, HackerNoon](https://hackernoon.com/lessons-ive-learned-building-distributed-systems-with-cqrs-and-event-sourcing-ece284ecc1a1) (Medium, named author, HackerNoon is a mixed-quality but sometimes-credible practitioner venue -- judged on content specificity here, which is substantive and concrete rather than generic).

### 6.4 Architecture astronauts -- abstraction detached from any actual problem

- **Intended benefit**: recognizing genuinely general patterns across
  problems can produce reusable infrastructure that pays off across many
  future projects.
- **The trap**: building the "general" abstraction *first*, derived from
  what a technology's category looks like ("this is peer-to-peer, so
  let's build The General Peer-to-Peer Platform") rather than from an
  actual problem being solved -- producing frameworks and platforms that
  are internally elegant and solve nothing anyone asked for, because the
  abstraction was reverse-engineered from a label rather than forward-
  engineered from a need.
- **What practitioners learned**: Joel Spolsky's "Don't Let Architecture
  Astronauts Scare You" (joelonsoftware.com, 2001) is the primary,
  foundational, extremely widely-cited source (the term itself is
  attributed to him and has its own Wikipedia entry). Key quote: "When
  you go too far up, abstraction-wise, you run out of oxygen... they
  create these absurd, all-encompassing, high-level pictures of the
  universe that are all good and fine, but don't actually mean anything at
  all." His diagnostic: an architecture astronaut takes a fact like
  "Napster is peer-to-peer" and builds around the architecture label,
  "completely missing the point that it's interesting because you can
  type the name of a song and listen to it right away" -- i.e. mistaking
  the category for the value proposition. **High** confidence -- primary,
  named, foundational, still cited 25 years later.
- **Static hallmark**: a framework/platform module with a name describing
  a *general capability* (`GenericEventBus`, `UniversalPipeline`,
  `AbstractProcessingEngine`) that has exactly one consumer in the
  codebase, and whose configuration surface (options, extension points)
  exceeds the actual variation exercised by that one consumer -- i.e., an
  abstraction whose generality is unused generality, directly checkable
  by comparing declared extension points against exercised extension
  points.
- **Sources**: [Don't Let Architecture Astronauts Scare You -- Joel Spolsky](https://www.joelonsoftware.com/2001/04/21/dont-let-architecture-astronauts-scare-you/) (primary, canonical, named); [Architecture astronaut -- Wikipedia](https://en.wikipedia.org/wiki/Architecture_astronaut) (definitional, corroborating, cites Spolsky as originator).

---

## 7. Type-driven / functional-core traps

### 7.1 Functional core, imperative shell -- underexplored downside in mainstream coverage

- **Intended benefit**: isolate pure business logic (the "functional
  core") from all side effects (I/O, mutation, time, randomness -- pushed
  to a thin "imperative shell"), so the core is trivially unit-testable
  with no mocks and the shell is thin enough to verify by inspection or
  integration test.
- **The trap**: this corpus's search pass (Google Testing Blog, Kenneth
  Lange, ssense-tech, javiercasas.com) found the pattern's *benefits*
  extremely well documented but found **no substantive practitioner essay
  specifically cataloguing its overuse failure mode** in this search
  pass -- worth stating plainly rather than inventing a citation. The
  trap that *does* recur informally across type-driven-design discourse
  (matching this corpus's DRY/YAGNI findings applied to types rather than
  functions) is: pushing purity dogmatically to the point where genuinely
  stateful, sequential domain logic (e.g. a wizard-style multi-step
  workflow with real ordering dependencies) gets contorted into an
  artificially pure representation (giant intermediate data structures
  threading state through a chain of pure functions) that's harder to
  read than the imperative version would have been, purely to preserve
  the "no impurity in the core" rule.
- **What practitioners learned**: **flagged as folklore for this
  specific failure mode** -- the *benefit* claims (Gary Bernhardt's
  original "Boundaries" talk, screencast catalog entry found in search)
  are primary and well-attested, but the *overuse* critique specifically
  is this corpus's own synthesis from the general premature-abstraction
  pattern (sections 1.2, 2.2, 3) applied to this case, not a distinct
  cited practitioner essay. Recorded honestly rather than dressed up with
  an invented citation.
- **Static hallmark**: a "pure" function whose parameter list has grown
  to include what amounts to the entire mutable state of a workflow
  passed as an immutable snapshot on every call (a `State` struct with
  more than ~6-8 fields threaded through a pipeline of otherwise-pure
  transforms) is a candidate signal, though this is this corpus's own
  extrapolation rather than a lifted practitioner-stated hallmark.
- **Sources**: [Functional Core, Imperative Shell -- Destroy All Software (Gary Bernhardt)](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell) (primary, originator, benefit-side only); [Google Testing Blog: Simplify Your Code -- Functional Core, Imperative Shell](https://testing.googleblog.com/2025/10/simplify-your-code-functional-core.html) (credible org blog, benefit-side). **No overuse-specific citation found this pass -- explicitly flagged, not fabricated.**

### 7.2 Primitive obsession / stringly-typed code and the "Parse, Don't Validate" answer

- **Intended benefit** (of the anti-pattern's fix): domain concepts with
  real constraints (an email address, a non-negative quantity, a
  validated user ID) get their own type instead of being passed around as
  bare `str`/`int`/`bool`, so the type checker enforces the constraint
  everywhere instead of relying on every call site remembering to
  validate.
- **The trap** (primitive obsession itself): using primitives for
  everything defers the "is this actually valid" question to runtime,
  scattered across every function that happens to receive the value, so
  the same validation logic gets duplicated (or, worse, *not* duplicated
  consistently) at every boundary, and a function's signature
  (`def charge(amount: float)`) tells you nothing about the actual
  invariant (amount must be positive, in cents, non-NaN) that every
  caller is implicitly required to uphold.
- **What practitioners learned**: Alexis King's "Parse, Don't Validate"
  (2019, referenced as still actively discussed via a 2026 Hacker News
  resurfacing in this search pass, which is itself evidence of durable
  relevance) draws the precise distinction this corpus's search
  surfaced clearly: a *validator* checks a value and then throws the
  proof away (returns `bool` or raises), so every downstream consumer has
  to either re-validate or trust blindly; a *parser* checks a value and
  *encodes what it learned in the return type* (returns a `NonEmptyList`
  instead of validating a `List` is non-empty and returning the same
  `List`), so the type system carries the proof forward and downstream
  code literally cannot forget to check because the un-checked case is
  not representable. The "NewType" pattern (Rust community writeups
  surfaced independently, deepengineering.net) is flagged as a *partial*
  fix worth noting precisely because it's a common misapplication in its
  own right: wrapping a primitive in a distinct type (`MessageId(u64)`)
  gets you nominal distinctness (can't accidentally pass a `UserId` where
  a `MessageId` is expected) but, *without* combining it with validation
  at construction (smart constructors), doesn't actually prevent invalid
  values -- a `MessageId` can still wrap any `u64` including negative-
  domain-equivalent nonsense. **High** confidence -- King's essay is
  widely regarded as the canonical modern statement of this idea across
  the statically-typed-functional community, evidenced by its continued
  independent resurfacing years later.
- **Static hallmark**: a function parameter typed as a bare primitive
  (`str`, `int`, `float`) whose name encodes a domain constraint the type
  doesn't (`email: str`, `positive_amount: int`, `validated_token: str`)
  -- the parameter *name* admitting the constraint in prose is itself the
  detectable signal that the type should have carried it (a linter can
  grep parameter names against a constraint-word list -- `validated_`,
  `_id`, `positive_`, `non_empty_` -- cross-referenced against whether the
  annotated type is a bare builtin).
- **Sources**: [Parse, Don't Validate -- Alexis King](https://news.ycombinator.com/item?id=46960392) (HN resurfacing of the primary 2019 essay; primary essay itself is lexi-lambda's blog, well-known, canonical in the typed-FP community); [Rust Patterns That Leverage the Type System -- Deep Engineering](https://deepengineering.net/p/rust-patterns-that-leverage-the-type-system) (secondary, corroborating, NewType-limitations point).

---

## 8. Catch-all: additional well-documented traps surfaced in the sweep

### 8.1 Anemic domain model

- **Intended benefit**: separating data (plain structs/DTOs) from
  behavior (services that operate on them) looks like clean separation of
  concerns.
- **The trap**: it's actually procedural code wearing OO syntax -- objects
  become bags of getters/setters with all business logic living in
  external "service" classes, which loses OOP's core value proposition
  (combining data and the operations that maintain its invariants) while
  keeping all of OOP's ceremony (classes, DI wiring for the services,
  mapping layers).
- **What practitioners learned**: Martin Fowler's bliki entry (primary,
  canonical, named "Anemic Domain Model" specifically as an anti-pattern)
  states it directly: "the fundamental horror of this anti-pattern is
  that it's so contrary to the basic idea of object-oriented design...
  it's just a procedural style design." He explicitly does *not* say the
  fix is "put everything in the domain model" -- transaction-script style
  is fine for genuinely simple CRUD apps; the anti-pattern is specifically
  paying OOP's *cost* (classes, mapping, DI) while getting none of its
  *benefit* (encapsulated invariants). **High** confidence -- primary,
  named, canonical source, the term itself originates here.
- **Static hallmark**: a class where every field has both a public getter
  and a public setter and the class contains zero methods beyond
  accessors -- directly greppable (accessor-method-count == field-count *
  2, business-method-count == 0), especially when paired with a
  same-named `XService` class that contains the actual logic operating on
  that class's fields.
- **Sources**: [bliki: Anemic Domain Model -- Martin Fowler](https://martinfowler.com/bliki/AnemicDomainModel.html) (primary, canonical, coins the term).

### 8.2 Repository pattern as a leaky abstraction over a modern ORM

- **Intended benefit**: hide the persistence mechanism behind a
  collection-like interface, so the domain/application layer doesn't know
  or care whether data comes from SQL, a document store, or memory --
  and, in principle, the database could be swapped without touching
  business logic.
- **The trap**: modern ORMs (Entity Framework, and by the same argument
  SQLAlchemy, Hibernate, etc.) are *already* an implementation of the
  Repository/Unit-of-Work patterns internally (`DbSet<T>`,
  `Session.query`), so wrapping them in a hand-rolled repository
  interface is often a redundant abstraction over an existing
  abstraction, and it's a leaky one: ORM-specific performance concerns
  (change tracking, lazy loading, query splitting, `.AsNoTracking()`)
  don't disappear just because they're accessed through a repository
  method -- they either bleed through the repository's method signatures
  (defeating the abstraction) or get hidden entirely (defeating
  performance tuning), and the promised benefit of "swap the database
  later" rarely materializes in practice because different databases have
  genuinely different data-access paradigms that a thin repository
  interface can't actually paper over.
- **What practitioners learned**: multiple independent, named .NET
  practitioner sources converge on this in this search pass: Derek Greer
  ("Ditch the Repository Pattern Already," Los Techies -- a long-running,
  credible .NET community blog) and Matthew Daly ("Why I no longer use
  the repository pattern") both argue the pattern's classic justification
  (swappable persistence, easier testing via a fake repository) is
  largely obsolete once the ORM itself already provides those seams
  (in-memory providers for testing, `IQueryable` abstraction for
  composition) -- and that the repository layer, rather than adding
  safety, adds a translation tax between two similar-but-not-identical
  query surfaces. **Medium-High** confidence -- multiple independent,
  named, credible community-blog authors converging on the same critique
  from different angles, though no single "primary, foundational" source
  the way Fowler/Metz/Spolsky are for their respective traps.
- **Static hallmark**: a repository interface method whose parameter or
  return type is itself an ORM-specific type (`IQueryable<T>`,
  `Expression<Func<T,bool>>`, a raw SQLAlchemy `Query` object) -- direct
  proof the "abstraction" doesn't actually hide the persistence
  technology, since callers are coupled to the ORM's types through the
  supposedly-abstracting interface.
- **Sources**: [Ditch the Repository Pattern Already -- Derek Greer, Los Techies](https://lostechies.com/derekgreer/2018/02/20/ditch-the-repository-pattern-already/) (primary, named, long-running credible community blog); [Why I no longer use the repository pattern -- Matthew Daly](https://matthewdaly.co.uk/blog/2022/10/26/why-i-no-longer-use-the-repository-pattern/) (corroborating, named independent practitioner).

### 8.3 Law of Demeter overcorrection -- wrapper explosion

- **Intended benefit**: "only talk to your immediate friends" -- avoid
  reaching through an object's internals (`a.getB().getC().getD()`, the
  "train wreck") because it couples the caller to the *entire* chain's
  structure, not just `a`'s interface.
- **The trap**: overcorrecting by mechanically banning any chained
  access, which forces every intermediate class to grow a thin delegating
  wrapper method for anything a caller might eventually need several
  hops away -- turning one train wreck into a maze of one-line
  pass-through methods (`getD()` on `A` that just calls
  `this.getB().getC().getD()` internally) that add indirection and files
  without actually reducing coupling, since the *logical* dependency on
  `D`'s shape is unchanged -- only its syntactic path got hidden.
- **What practitioners learned**: this corpus's search surfaced this
  specifically as a named, recognized overcorrection (not merely a
  strawman): "strict adherence to the Law of Demeter can lead to
  over-abstraction, where developers create numerous wrapper methods to
  delegate operations to internal components, resulting in increased code
  verbosity and indirection." The practical resolution found consistently
  across sources: LoD is meant to apply to objects with *behavior* and
  changeable internal structure, not to plain data/DTO-like structures
  being navigated for reading (where a chain of field access is just
  reading a data shape, not coupling to hidden behavior) -- balance LoD
  against KISS rather than applying it absolutely. **Medium** confidence
  -- the wrapper-explosion phenomenon and the LoD-vs-DTO distinction are
  consistently described across multiple sources in this pass, but
  without one single towering canonical essay (this is a case where the
  original 1987 Demeter project papers would be the primary source but
  were not independently re-fetched in this pass).
- **Static hallmark**: a public method whose entire body is a single
  delegating call one level deeper (`def get_d(self): return
  self.b.get_c().get_d()`) that exists *only* to satisfy LoD, with no
  added logic, validation, or transformation -- a chain of these across
  multiple classes (A delegates to B delegates to C for the same
  ultimate value) is the wrapper-explosion fingerprint, directly
  greppable as a chain of single-statement pass-through methods.
- **Sources**: [Law of Demeter -- ArchMan](https://archman.dev/docs/core-design-and-programming-principles/general-principles/law-of-demeter) (secondary, corroborating); [Law of Demeter -- Wikipedia](https://en.wikipedia.org/wiki/Law_of_Demeter) (definitional, cites the original Demeter project sources -- Lieberherr & Holland).

---

## Reconciliation with the existing repo catalog

`docs/design/architecture-check-catalog.md` and
`docs/design/structural-linter-adversarial-hardening.md` **do not exist in
this worktree** (confirmed via filesystem search before writing this
document), so there is no existing prose to directly diff against. The
reconciliation below is against the T-0330/T-0332 ticket bodies in
`tickets.md`, which are the closest in-repo statement of the planned arch
checks and recommender:

- **T-0330** (EPIC arch SOLID + senior-designer checks) plans "static
  proxies for real design principles." Section 1.0 above is a hard
  constraint on that epic's severity model: every practitioner source
  found (North most explicitly) treats SOLID letters as *heuristics in
  tension*, not laws -- T-0330's checks must ship as advisory/waivable,
  never hard-blocking, or the tool itself becomes the mechanical-SOLID
  trap the corpus documents repeatedly (1.1 SRP-itis, 1.2/1.5 single-
  implementer interface explosion). This also surfaces the **single most
  useful concrete detector for T-0330**: the "single-implementer
  interface/abstract-base" structural fingerprint recurs identically
  across OCP (1.2), DIP (1.5), Abstract Factory (5.2), Strategy/Observer
  (5.4), and Hexagonal ports (6.1) -- five different named
  patterns/principles sharing one detectable code shape. T-0330 should
  implement this once as a shared detector, not five times.
- **T-0332** (hallmark->pattern + anti-pattern->escape recommender)
  explicitly already designs for "pairs with the SOLID smells: reuse the
  same hallmark detectors... one detector, two outputs." Section 5 above
  (Singleton, Factory, Visitor, Strategy/Observer, DI-container) gives
  T-0332 concrete anti-pattern->escape entries beyond what the ticket
  body lists (god object->SRP decompose, anemic->move behavior to data,
  stringly-typed->newtype, poltergeist/lava-flow->delete, sequential
  coupling->explicit state): add **fat-interface->split-by-client**
  (1.4/ISP), **fragile-base-class->extract-interface+compose** (4),
  **repository-over-ORM->delete-layer** (8.2), and **wrapper-
  explosion->inline-through** (8.3, the mirror image of Sandi Metz's
  own "inline back through" prescription in 2.1, applied to a different
  trap). T-0332's own ticket text warns the recommender must be
  "STRONG-HALLMARK-ONLY / high precision" -- section 7.1 of this corpus
  (functional-core overuse) is flagged explicitly as folklore-strength
  evidence specifically *because* T-0332 needs to not ship low-precision
  detectors; that gap is reported honestly rather than backfilled with
  weak material.
- **T-0341** (conformance) has no ticket body in this worktree's
  `tickets.md` to reconcile against (grep found no `id: T-0341` entry) --
  flagged as **blocked-on-missing-context** rather than silently skipped;
  whoever owns T-0341 should re-run this reconciliation once its ticket
  body or the two catalog docs land.

---

## Phase-0/Phase-2 coverage ledger

Universe enumerated before drain (denominator = 21), all 21 reached
`done` with findings recorded in the vault
(`/mnt/c/Users/logan/Documents/Obsidian Notes/Research/design-pattern-traps/`):
01-SRP, 02-OCP, 03-LSP, 04-ISP, 05-DIP, 06-SOLID-whole,
07-DRY-wrong-abstraction, 08-AHA-WET-premature-abstraction,
09-YAGNI-speculative-generality, 10-inheritance-vs-composition,
11-singleton-overuse, 12-factory-explosion, 13-visitor-rigidity,
14-strategy-observer-overeager, 15-decorator-adapter-other-gof,
16-clean-hexagonal-onion-overkill, 17-microservices-vs-monolith,
18-premature-cqrs-event-sourcing, 19-type-driven-functional-core,
20-anemic-domain-god-object-lava-flow,
21-law-of-demeter-di-containers-orm-repository. Zero pending, zero
blocked at the corpus-enumeration level. The two items flagged as
folklore/no-primary-source-found (AHA's specific canonical essay in 2.2,
functional-core overuse critique in 7.1) are reported as such, not
silently upgraded to "cited" -- this is itself a completeness signal: the
corpus does not manufacture citations to fill every cell.
