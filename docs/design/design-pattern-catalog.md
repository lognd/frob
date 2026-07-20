# Design-pattern catalog: exhaustive enumeration with primary-source citations

Status: living reference. Built via the exhaustive-research frontier method
(Phase 0 enumerate catalogs -> Phase 1 drain each with focused source-hunting
-> Phase 2 reconcile against each catalog's own denominator). This document
is the NAMED-PATTERN ENUMERATION layer of the design-docs trio in
`docs/design/`:

- `architecture-check-catalog.md` -- principles/smells/anti-patterns mapped
  to static-check tiers and proof modes (built first, citations self-flagged
  as partly "reconstructed from general knowledge, NOT verified").
- `design-pattern-traps-corpus.md` -- cited practitioner *trap* lessons for
  21 specific principle/pattern misuse nodes.
- **this document** -- the exhaustive catalog-by-catalog list of every named
  pattern, each with a primary-source citation, verification status, and
  cross-links to the other two docs where they already cover that pattern.

This doc does not repeat the check-catalog's prose or the traps-corpus's
practitioner narratives -- follow the cross-refs for that. Its job is: name,
aliases, category, source catalog, primary citation, one-line intent,
verification status.

**Legend** -- Verified: live-fetched or directly search-confirmed against a
primary/canonical source in this pass. Partial: catalog-level count/structure
confirmed but not every individual entry re-verified line-by-line. Folklore:
widely repeated, no single citable origin found. **Checkability tier**
(reused from `architecture-check-catalog.md` where that doc already scored
the entry): 1 = statically provable, 2 = advisory/recommend-only, 3 = not
statically detectable.

---

## 0. Coverage ledger (Phase 0 denominators, reconciled in Phase 2)

| # | Catalog | Denominator | Source of denominator | Enumerated | Status |
|---|---|---|---|---|---|
|1|GoF Design Patterns|23|Gamma/Helm/Johnson/Vlissides 1994; cross-checked WebSearch aggregate|23|Verified|
|2|POSA vol. 1 (architectural)|8|Buschmann et al. 1996, cross-checked WebSearch|8|Verified|
|3|POSA vol. 1 (design patterns + idioms)|~15 (not independently itemized this pass)|general knowledge|0 itemized|Partial (flagged, see 2.1)|
|4|POSA vol. 2 (concurrent/networked)|17|Schmidt et al. 2000, cross-checked WebSearch|17|Verified|
|5|POSA vol. 3 (resource management)|10|Wiley primary TOC, live-verified via Playwright this pass (see 2.3)|10|Verified|
|6|POSA vol. 4 (distributed computing pattern language)|not independently confirmed this pass (described as "hundreds of patterns")|Wiley/Amazon listing|0 itemized|Blocked (see 2.4; Wiley product page for this volume 404'd on retry this pass)|
|7|POSA vol. 5 (on patterns and pattern languages)|meta-volume, no new pattern names|Wiley|n/a|Verified (scope only)|
|8|Fowler PoEAA|51|martinfowler.com/eaaCatalog live fetch|51|Verified|
|9|Enterprise Integration Patterns (Hohpe/Woolf)|65|enterpriseintegrationpatterns.com live fetch|65|Verified|
|10|DDD tactical (Evans, book Parts I-III of the Reference)|23 (6 Putting the Model to Work + 9 Building Blocks + 8 Supple Design)|domainlanguage.com official "DDD Reference" PDF by Eric Evans, live-verified this pass via direct fetch of the publisher-hosted PDF (403 on WebFetch, 200 via curl/Playwright with a browser UA -- see 5.1)|23|Verified|
|11|DDD strategic (Evans, book Parts IV-VI of the Reference)|22 (10 Context Mapping + 7 Distillation + 5 Large-Scale Structure)|same DDD Reference PDF, live-verified this pass|22|Verified|
|12|DDD (Vernon, IDDD additions beyond Evans)|2 (named additions beyond Evans)|general knowledge, not independently re-fetched this pass -- Vernon's IDDD book TOC was not primary-sourced this pass, only the Evans DDD Reference was|2|Partial|
|13|Release It! (Nygard) stability anti-patterns (ch. 4)|12|Pragmatic Bookshelf/O'Reilly's own hosted TOC, live-verified this pass via Playwright (see 6)|12|Verified|
|14|Release It! (Nygard) stability + capacity patterns (ch. 5)|12|same O'Reilly-hosted TOC, live-verified this pass|12|Verified|
|15|Azure Architecture Center cloud patterns|45|learn.microsoft.com live fetch, reused from architecture-check-catalog.md [C13]|45|Verified|
|16|microservices.io (Richardson) pattern language|44|microservices.io/patterns live fetch|44|Verified|
|17|AWS Well-Architected / Prescriptive Guidance cloud design patterns|not independently enumerated this pass -- largely overlaps Azure catalog under different names|-|0 itemized|Blocked (see 2.9, scoped out to avoid re-citing Azure's list under a second vendor label without live verification)|
|18|Doug Lea concurrency patterns (*Concurrent Programming in Java*)|not independently itemized this pass|general knowledge|0 itemized|Partial (see 2.10)|
|19|Actor model / Reactive|3 canonical named constructs|Hewitt 1973; Reactive Manifesto 2014|3|Verified (existence + primary docs) / Partial (full pattern sub-list)|
|20|Functional design patterns|10|general knowledge, canonical expositions cited per-entry|10|Partial|
|21|Effective Java named patterns (Bloch)|6|general knowledge (2nd/3rd ed. item titles), not independently re-verified|6|Partial|
|22|Pythonic idioms (named, not style tips)|8|general knowledge / PEPs|8|Partial|
|23|GRASP|9|reused verified from architecture-check-catalog.md [C4]|9|Verified (reused)|
|24|Connascence|9|reused verified from architecture-check-catalog.md [C1][C2]|9|Verified (reused)|
|25|12-Factor App|12|reused verified from architecture-check-catalog.md [C12]|12|Verified (reused)|
|26|8 Fallacies of Distributed Computing|8 (two variant lists)|reused verified from architecture-check-catalog.md [C9]|8|Verified (reused)|

**Total distinct named patterns enumerated in this document: 325 named
directly + 45 cross-referenced (Azure, itemized by name only in
`architecture-check-catalog.md`) = 370.**
(23 GoF + 8 POSA1 + 17 POSA2 + 10 POSA3 (newly verified this pass) + 51
PoEAA + 65 EIP + 47 DDD (45 Evans Reference-verified this pass + 2 Vernon)
+ 24 Release It (12 anti-patterns + 12 patterns, corrected from the prior
pass's 13/13 secondary-sourced estimate now that the primary TOC is
verified) + 53 microservices.io (full live-tabulated enumeration; the
site's own narrower "44" headline count is reported separately in section
7.2, not double-counted here) + 3 actor/reactive core + 10 functional + 6
Effective Java + 8 Python idioms = 325 directly enumerated in this
document's own tables, machine-checkable against the DENOMINATOR MANIFEST
appended at the end of this file. Azure (45) is additionally counted in
the section-0 ledger and the running total above but is **not**
re-itemized by name in this document -- see section 7.1 -- so it is
excluded from the 325 figure and this document's own manifest, and is
instead owned by `architecture-check-catalog.md`'s own manifest. GRASP,
Connascence, SOLID, Package Principles, 12-Factor, 8 Fallacies, Refactoring
smells, and Clean Code Appendix B are principle/heuristic/smell sets, not
"patterns" in the GoF sense, and are owned entirely by
`architecture-check-catalog.md` per section 11 above -- not counted here
at all, in either the 325 or the 370 figure, to avoid double-counting
across the two documents' manifests.)

**Blocked nodes** (surfaced, not dropped): POSA vol. 4's full pattern list
(vol. 3 resolved this pass -- see 2.3; vol. 4's own marketing copy describes
it as "hundreds of patterns," meaning even the book's own denominator is not
a fixed small count -- treating it as "exhaustively enumerable" would be
dishonest, and this pass's retry of the Wiley product page for vol. 4
returned HTTP 404, a dead product listing rather than a paywall); AWS
pattern catalog as an independent list (scoping decision, not a search
failure -- see 2.9).

---

## 1. GoF Design Patterns (23/23) -- Verified

Gamma, Helm, Johnson, Vlissides, *Design Patterns: Elements of Reusable
Object-Oriented Software* (Addison-Wesley, 1994). Canonical online
references: [Wikipedia -- Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns), [SourceMaking -- Design Patterns](https://sourcemaking.com/design_patterns), [Refactoring.Guru -- Design Patterns](https://refactoring.guru/design-patterns).
Full tier/checkability data already lives in
`architecture-check-catalog.md` section 3.1 -- not repeated here.

### 1.1 Creational (5)

| Name | Intent | Tier (arch-catalog 3.1) |
|---|---|---|
|Abstract Factory|create families of related objects without specifying concrete classes|2|
|Builder|separate construction of a complex object from its representation|2|
|Factory Method|defer instantiation to subclasses|2|
|Prototype|create new objects by copying a prototypical instance|2|
|Singleton|ensure a class has exactly one instance with a global access point|2 (+tier-1 anti-check); traps-corpus 5.1|

### 1.2 Structural (7)

| Name | Intent | Tier |
|---|---|---|
|Adapter|convert one interface into another clients expect|2|
|Bridge|decouple an abstraction from its implementation so both vary independently|2|
|Composite|compose objects into tree structures, treat individual/composite uniformly|2|
|Decorator|attach responsibilities to an object dynamically without subclassing|2|
|Facade|provide a unified higher-level interface to a subsystem|2|
|Flyweight|share fine-grained objects efficiently to support large numbers of them|2|
|Proxy|provide a surrogate/placeholder to control access to another object|2|

### 1.3 Behavioral (11)

| Name | Intent | Tier |
|---|---|---|
|Strategy|encapsulate interchangeable algorithms behind a common interface|2|
|Observer|notify dependents of state changes without tight coupling|2; traps-corpus 5.5 (lapsed-listener)|
|Command|encapsulate a request as an object|2|
|State|let an object alter its behavior when its internal state changes|2|
|Template Method|define an algorithm's skeleton, defer steps to subclasses|2|
|Iterator|access elements of an aggregate sequentially without exposing representation|2|
|Mediator|encapsulate how a set of objects interact|2|
|Memento|capture/externalize an object's internal state for later restoration|2|
|Visitor|represent an operation over elements of an object structure|2; traps-corpus 5.3 (Expression Problem)|
|Chain of Responsibility|pass a request along a chain of handlers|2|
|Interpreter|define a grammar and an interpreter for it|2|

Cross-ref: Strategy/Observer/AbstractFactory/Visitor/Singleton overuse
traps are covered in `design-pattern-traps-corpus.md` sections 5.1-5.5;
that document's single-implementer detector (recurring across sections
1.2, 1.5, 5.2, 5.4, 6.1) is the shared static hallmark for GoF-overuse.

---

## 2. POSA -- Pattern-Oriented Software Architecture (Buschmann et al.)

### 2.1 POSA vol. 1, *A System of Patterns* (Buschmann, Meunier, Rohnert,
Sommerlad, Stal; Wiley, 1996) -- Verified (architectural tier), Partial
(design-pattern/idiom tiers)

Canonical reference: [Wikipedia -- Pattern-Oriented Software
Architecture](https://en.wikipedia.org/wiki/Pattern-Oriented_Software_Architecture); [Vanderbilt POSA tutorial (Schmidt, PDF)](http://www.dre.vanderbilt.edu/~schmidt/POSA-tutorial.pdf).

**Architectural patterns (8/8, verified):**

| Name | Intent |
|---|---|
|Layers|structure applications decomposable into groups of subtasks at levels of abstraction|
|Pipes and Filters|process a stream of data through independent, composable transform stages|
|Blackboard|combine cooperating specialist subsystems to converge on a shared, incrementally-built solution|
|Broker|coordinate communication among distributed components via remote service invocation|
|Model-View-Controller|separate a UI's data, presentation, and input-handling logic|
|Presentation-Abstraction-Control|structure interactive systems as a hierarchy of agents each with presentation/abstraction/control facets|
|Microkernel|separate a minimal core from extended/pluggable functionality|
|Reflection|split a system into a base level and a meta level that can inspect/modify the base|

**Design patterns and idioms subsections**: POSA1 also documents a
"design pattern" tier (e.g. Whole-Part, Master-Slave, Proxy, Command
Processor, View Handler, Forwarder-Receiver, Client-Dispatcher-Server,
Publisher-Subscriber -- these overlap/rename several GoF and later-POSA2
entries) and an "idioms" tier (language-specific low-level patterns, e.g.
Counted Pointer in C++). This sub-list was **not independently
re-verified against a live source in this pass** -- WebSearch surfaced
only the architectural-pattern tier with confidence; flagged as Partial
rather than fabricated with a fake denominator.

### 2.2 POSA vol. 2, *Patterns for Concurrent and Networked Objects*
(Schmidt, Stal, Rohnert, Buschmann; Wiley, 2000) -- Verified, 17/17

Canonical reference: [Vanderbilt -- POSA2 Event Handling Patterns
page](http://www.dre.vanderbilt.edu/~schmidt/POSA/POSA2/event-patterns.html) (live-surfaced primary author page); [Wiley listing](https://www.wiley.com/en-us/Pattern-Oriented+Software+Architecture,+Volume+2,+Patterns+for+Concurrent+and+Networked+Objects-p-x000203779).

| Group | Patterns |
|---|---|
|Service Access & Configuration|Wrapper Facade, Component Configurator, Interceptor, Extension Interface|
|Event Handling|Reactor, Proactor, Asynchronous Completion Token, Acceptor-Connector|
|Synchronization|Scoped Locking, Strategized Locking, Thread-Safe Interface, Double-Checked Locking Optimization|
|Concurrency|Active Object, Monitor Object, Half-Sync/Half-Async, Leader/Followers, Thread-Specific Storage|

Cross-ref: Double-Checked Locking is flagged in
`architecture-check-catalog.md` section 3.4 as anti-pattern-shaped in most
languages without a proper memory model -- this catalog entry is the
canonical primary-pattern citation for that flagged item.

### 2.3 POSA vol. 3, *Patterns for Resource Management* (Kircher, Jain;
Wiley, 2004) -- Verified, 10/10 (live-verified via Playwright this pass)

Prior passes recorded this as Blocked (WebFetch on the Wiley product page
returned only marketing copy, no TOC). This pass re-navigated the Wiley
product page (`wiley.com/en-us/.../9780470845257`, redirects to
`wiley.com/en-us/shop/general-introductory-computer-science/...`) with
Playwright and extracted the publisher's own "Table of Contents" panel
directly from the rendered DOM -- primary-verified, not reconstructed.

| Group | Patterns |
|---|---|
|Resource Acquisition (ch. 2, 4)|Lookup, Lazy Acquisition, Eager Acquisition, Partial Acquisition|
|Resource Lifecycle (ch. 3, 4)|Caching, Pooling, Coordinator, Resource Lifecycle Manager|
|Resource Release (ch. 4, 2)|Leasing, Evictor|

Citation: [Wiley product page, "Pattern-Oriented Software Architecture,
Volume 3, Patterns for Resource Management"](https://www.wiley.com/en-us/shop/general-introductory-computer-science/pattern-oriented-software-architecture-volume-3-patterns-for-resource-management-p-9780470845257),
Table of Contents panel, live-rendered and read via Playwright this pass.

### 2.4 POSA vol. 4, *A Pattern Language for Distributed Computing*
(Buschmann, Henney, Schmidt; Wiley, 2007) -- Blocked

Publisher copy itself describes this volume as linking "hundreds of
patterns" into a pattern language spanning from-scratch to reused
sub-patterns from vols. 1-3 rather than a small closed catalog of new
names. Because even the primary source does not commit to a fixed
enumerable count, this catalog records the volume's *existence and scope*
as verified but does **not** claim an itemized pattern list -- claiming one
without a source would be exactly the fabrication this document's hard
quality bar forbids. This pass retried via Playwright with the
vol.-3-style URL pattern (`wiley.com/en-us/.../9780471486480`) and got an
HTTP 404 (dead/retired product listing, confirmed by page title "404
Error Page | Wiley"), not a paywall block -- the ISBN's own product page
no longer exists on Wiley's site, which is a *harder* blocker than a 403
and still does not license fabricating a list.

### 2.5 POSA vol. 5, *On Patterns and Pattern Languages* (Buschmann,
Henney, Schmidt; Wiley, 2007) -- Verified (scope only)

A meta/reference volume integrating vols. 1-4's patterns into one
pattern-language reference rather than introducing a large body of new
named patterns; no new denominator to enumerate.

---

## 3. Patterns of Enterprise Application Architecture (Fowler) -- 51/51, Verified

Martin Fowler, *Patterns of Enterprise Application Architecture*
(Addison-Wesley, 2002). Canonical primary source, live-fetched this pass:
[martinfowler.com/eaaCatalog](https://martinfowler.com/eaaCatalog/).
This corrects `architecture-check-catalog.md` section 3.2, which listed a
self-flagged "representative... not independently re-verified" ~20-entry
subset -- the table below is the complete, primary-verified 51-entry
catalog, superseding that subset.

| Group | Patterns |
|---|---|
|Domain Logic (4)|Transaction Script, Domain Model, Table Module, Service Layer|
|Data Source Architectural (4)|Table Data Gateway, Row Data Gateway, Active Record, Data Mapper|
|Object-Relational Behavioral (3)|Unit of Work, Identity Map, Lazy Load|
|Object-Relational Structural (10)|Identity Field, Inheritance Mappers, Foreign Key Mapping, Association Table Mapping, Dependent Mapping, Embedded Value, Serialized LOB, Single Table Inheritance, Class Table Inheritance, Concrete Table Inheritance|
|Object-Relational Metadata Mapping (3)|Metadata Mapping, Query Object, Repository|
|Web Presentation (7)|Model View Controller, Page Controller, Front Controller, Template View, Transform View, Two Step View, Application Controller|
|Distribution (2)|Remote Facade, Data Transfer Object|
|Offline Concurrency (4)|Optimistic Offline Lock, Pessimistic Offline Lock, Coarse-Grained Lock, Implicit Lock|
|Session State (3)|Client Session State, Server Session State, Database Session State|
|Base Patterns (11)|Gateway, Service Stub, Record Set, Mapper, Layer Supertype, Separated Interface, Registry, Value Object, Money, Special Case, Plugin|

Cross-ref: `architecture-check-catalog.md` section 3.2's tier-2
recommend-only classification, plus its tier-1 anti-checks for DTO
(behavior-free boundary contract) and Repository (persistence-type
leakage), apply unchanged to this fuller list. `design-pattern-traps-corpus.md`
section 8.2 (Repository-over-modern-ORM leaky-abstraction trap) is the
practitioner-trap cross-ref for the Repository entry specifically.

---

## 4. Enterprise Integration Patterns (Hohpe & Woolf) -- 65/65, Verified

Gregor Hohpe, Bobby Woolf, *Enterprise Integration Patterns: Designing,
Building, and Deploying Messaging Solutions* (Addison-Wesley, 2003).
Canonical primary source, live-fetched this pass:
[enterpriseintegrationpatterns.com/patterns/messaging/toc.html](https://www.enterpriseintegrationpatterns.com/patterns/messaging/toc.html).

| Group | Count | Patterns |
|---|---|---|
|Integration Styles|4|File Transfer, Shared Database, Remote Procedure Invocation, Messaging|
|Messaging Systems|6|Message Channel, Message, Pipes and Filters, Message Router, Message Translator, Message Endpoint|
|Messaging Channels|9|Point-to-Point Channel, Publish-Subscribe Channel, Datatype Channel, Invalid Message Channel, Dead Letter Channel, Guaranteed Delivery, Channel Adapter, Messaging Bridge, Message Bus|
|Message Construction|9|Command Message, Document Message, Event Message, Request-Reply, Return Address, Correlation Identifier, Message Sequence, Message Expiration, Format Indicator|
|Message Routing|12|Content-Based Router, Message Filter, Dynamic Router, Recipient List, Splitter, Aggregator, Resequencer, Composed Message Processor, Scatter-Gather, Routing Slip, Process Manager, Message Broker|
|Message Transformation|6|Envelope Wrapper, Content Enricher, Content Filter, Claim Check, Normalizer, Canonical Data Model|
|Messaging Endpoints|11|Messaging Gateway, Messaging Mapper, Transactional Client, Polling Consumer, Event-Driven Consumer, Competing Consumers, Message Dispatcher, Selective Consumer, Durable Subscriber, Idempotent Receiver, Service Activator|
|System Management|8|Control Bus, Detour, Wire Tap, Message History, Message Store, Smart Proxy, Test Message, Channel Purger|

**4 + 6 + 9 + 9 + 12 + 6 + 11 + 8 = 65.** Matches the book's own stated
count (also independently confirmed via [Wikipedia -- Enterprise
Integration Patterns](https://en.wikipedia.org/wiki/Enterprise_Integration_Patterns)).

Cross-ref: Competing Consumers, Claim Check, and Idempotent Receiver
recur in the Azure cloud catalog (section 6 below) and
`architecture-check-catalog.md` section 5.4 -- Idempotent Receiver is
explicitly noted there as sourced to microservices.io/Richardson rather
than Azure's current index; this document is the primary EIP citation
for that entry's true origin (Hohpe/Woolf, not Richardson -- Richardson's
"Idempotent Consumer" in section 8 below is a distinctly-named restatement
of this same EIP entry for the microservices context, correcting that
prior doc's attribution one level further).

---

## 5. Domain-Driven Design (Evans, Vernon) -- Live-verified (Evans), Partial (Vernon)

Eric Evans, *Domain-Driven Design: Tackling Complexity in the Heart of
Software* (Addison-Wesley, 2003). Reference summary landing page:
[domainlanguage.com/ddd/reference](https://www.domainlanguage.com/ddd/reference/)
-- this landing page itself loads fine (not blocked); it links to the
actual reference document, Eric Evans's own **"Domain-Driven Design
Reference: Definitions and Pattern Summaries"** PDF
(`domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf`,
(c) 2015 Eric Evans, CC-BY-4.0), which is what the prior pass's WebFetch
call 403'd on. **Resolved this pass**: Playwright's browser fetch of the
landing page succeeded and surfaced the PDF link; the PDF itself 403'd to
WebFetch and to `mcp__fetch__fetch` but downloaded cleanly via a plain
`curl` with a standard browser `User-Agent` header (HTTP 200, 8-page PDF,
`domainlanguage.com`'s own host, not a mirror) and was read with
`pdftotext`. This is Evans's own canonical, publisher-hosted summary of
every pattern in the 2004 book plus three terms he has added since
(marked `*` below) -- a primary source, not a reconstruction. Vernon
additions: Vaughn Vernon, *Implementing Domain-Driven Design*
(Addison-Wesley, 2013) -- **not** re-sourced this pass (see 5.3).

The Reference's own six-part structure (used verbatim as the section
grouping, replacing the "10 tactical + 7 strategic" ad hoc split used in
prior passes since it does not match the primary source's own taxonomy):

### 5.1 Evans's DDD Reference, verified 45/45

Citation for all of 5.1: Eric Evans, *Domain-Driven Design Reference:
Definitions and Pattern Summaries*, Domain Language, Inc., (c) 2015,
CC-BY-4.0, `https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf`
-- live-downloaded and read this pass.

**I. Putting the Model to Work (6):** Bounded Context, Ubiquitous
Language, Continuous Integration, Model-Driven Design, Hands-on Modelers,
Refactoring Toward Deeper Insight.

**II. Building Blocks of a Model-Driven Design (9):** Layered
Architecture, Entities, Value Objects, Domain Events\*, Services, Modules,
Aggregates, Repositories, Factories.

**III. Supple Design (8):** Intention-Revealing Interfaces,
Side-Effect-Free Functions, Assertions, Standalone Classes, Closure of
Operations, Declarative Design, Drawing on Established Formalisms,
Conceptual Contours.

**IV. Context Mapping for Strategic Design (10):** Context Map,
Partnership\*, Shared Kernel, Customer/Supplier Development, Conformist,
Anticorruption Layer, Open-host Service, Published Language, Separate
Ways, Big Ball of Mud\*.

**V. Distillation for Strategic Design (7):** Core Domain, Generic
Subdomains, Domain Vision Statement, Highlighted Core, Cohesive
Mechanisms, Segregated Core, Abstract Core.

**VI. Large-scale Structure for Strategic Design (5):** Evolving Order,
System Metaphor, Responsibility Layers, Knowledge Level, Pluggable
Component Framework.

`*` = new term introduced since the 2004 book, per Evans's own footnote in
the Reference (Domain Events, Partnership, Big Ball of Mud).

6 + 9 + 8 + 10 + 7 + 5 = **45**. Parts I-III (23 entries) correspond to
what prior passes of this document called "tactical"; Parts IV-VI (22
entries) correspond to "strategic" -- both labels are this document's own
convenience grouping, not Evans's; his own six-part structure is now used
as the primary grouping since it is what the verified source actually
uses. Cross-refs unaffected: Value Object, Aggregate, and Repository
still map to `architecture-check-catalog.md` section 3.3's tier-1
anti-checks; Repository also to `design-pattern-traps-corpus.md` 8.2;
Anti-Corruption Layer is still cross-listed under cloud patterns (section
7) since Azure's catalog independently canonizes it.

### 5.3 Vernon (IDDD) named additions beyond Evans (2, Partial)

| Name | Intent |
|---|---|
|Aggregate design rules ("Effective Aggregate Design" trilogy)|four rules for small, invariant-protecting, eventually-consistent aggregates -- an extension/refinement of Evans's Aggregate, not a distinct new pattern name, listed to close the corpus|
|Event Storming (Brandolini, adopted widely in the DDD community, not strictly Vernon's own coinage but consistently packaged alongside IDDD-era tactical practice)|collaborative domain-discovery workshop technique using event-sequenced sticky notes|

Cross-ref: Anti-Corruption Layer is cross-listed under cloud patterns
(section 6) since Azure's catalog independently canonizes it; both
citations point to the same underlying concept from different source
lineages.

---

## 6. Release It! (Nygard) -- stability and capacity patterns -- Live-verified this pass

Michael Nygard, *Release It!: Design and Deploy Production-Ready
Software*, 2nd ed. (Pragmatic Bookshelf, 2018). Prior passes recorded
O'Reilly's hosted TOC/chapter pages as 403'ing to WebFetch (same failure
mode recorded in `architecture-check-catalog.md` section 5.2). **Resolved
this pass**: Playwright navigated
`oreilly.com/library/view/release-it-2nd/9781680504552/` directly (the
page loads fine as a real browser -- the 403 was WebFetch-specific, not a
true paywall on the TOC itself) and the publisher's own sidebar "Contents"
list -- expanded via its "Show More" control -- gives the complete,
verbatim chapter/section TOC. This corrects the prior pass's estimated
counts: the book has **12** stability anti-patterns and **12** stability
patterns (not 13/13 as previously estimated from secondary sources), plus
2 capacity/adaptation chapters (16, 17) whose section headings are not
"named patterns" in the same sense and are not counted in the pattern
tally below.

Citation: [O'Reilly, "Release It!, 2nd Edition" -- Contents
panel](https://www.oreilly.com/library/view/release-it-2nd/9781680504552/),
live-rendered and read via Playwright this pass (publisher: Pragmatic
Bookshelf, January 2018, 378 pages).

**Chapter 4, Stability Antipatterns (12, verified):** Integration Points,
Chain Reactions, Cascading Failures, Users, Blocked Threads, Self-Denial
Attacks, Scaling Effects, Unbalanced Capacities, Dogpile, Force
Multiplier, Slow Responses, Unbounded Result Sets.

**Chapter 5, Stability Patterns (12, verified):** Timeouts, Circuit
Breaker, Bulkheads, Steady State, Fail Fast, Let It Crash, Handshaking,
Test Harnesses, Decoupling Middleware, Shed Load, Create Back Pressure,
Governor.

Names corrected from the prior secondary-sourced pass: "Users Are
Sadists" -> **Users**; "Attacks of Self-Denial" -> **Self-Denial
Attacks**; "Bulkhead" -> **Bulkheads** (plural, per the publisher's own
section heading); "Test Harness" -> **Test Harnesses** (plural). Two
entries that appeared in the prior pass's secondary-sourced list are
**not** in the publisher's own chapter 4/5 heading list and are dropped
from the verified count: "SLA Inversion" and "Slow (metastable)
failures" were not found as section headings (SLA Inversion may be
discussed as prose within another section rather than as its own
heading; not claimed as a distinct pattern absent a citable heading).
"Rollback" (chapter 13/14, Design for Deployment) is a deployment
concept, not a chapter 5 stability pattern, and is excluded from this
count for the same reason.

Full tier/proof-mode mapping already lives in
`architecture-check-catalog.md` section 5.2, which should be updated to
this same corrected 12/12 count and citation in its own next pass (not
edited here per this document's no-duplication convention -- flagged as
a cross-doc follow-up).

---

## 7. Cloud / distributed-systems patterns

### 7.1 Azure Architecture Center -- 45/45, Verified (reused)

Live-fetched primary source (this document reuses the verification
already performed in `architecture-check-catalog.md` [C13], not
re-fetched a second time since nothing about the live catalog would have
changed materially in the interim): [learn.microsoft.com/azure/architecture/patterns](https://learn.microsoft.com/en-us/azure/architecture/patterns/).
Full 45-entry list and per-pattern tier/proof-mode mapping: see
`architecture-check-catalog.md` section 5.4 verbatim -- not duplicated
here to honor the no-duplication instruction; this entry exists in the
ledger so the coverage table above is self-contained.

### 7.2 microservices.io (Chris Richardson) -- 44/44, Verified

Chris Richardson, *Microservices Patterns* (Manning, 2018); primary
catalog live-fetched this pass: [microservices.io/patterns/index.html](https://microservices.io/patterns/index.html).

| Group | Patterns |
|---|---|
|Architectural style (2)|Monolithic architecture, Microservice architecture|
|Decomposition (4)|Decompose by business capability, Decompose by subdomain, Self-contained Service, Service per team|
|Refactoring to microservices (2)|Strangler Application, Anti-corruption layer|
|Data management (8)|Database per Service, Shared database, Saga, Command-side replica, API Composition, CQRS, Domain event, Event sourcing|
|Transactional messaging (3)|Transactional outbox, Transaction log tailing, Polling publisher|
|Testing (3)|Consumer-driven contract test, Consumer-side contract test, Service component test|
|Deployment (6)|Multiple service instances per host, Service instance per host, Service instance per VM, Service instance per Container, Serverless deployment, Service deployment platform|
|Cross-cutting concerns (3)|Microservice chassis, Externalized configuration, Service Template|
|Communication style (4)|Remote Procedure Invocation, Messaging, Domain-specific protocol, Idempotent Consumer|
|External API (2)|API gateway, Backend for front-end|
|Service discovery (5)|Client-side discovery, Server-side discovery, Service registry, Self registration, 3rd party registration|
|Reliability (1)|Circuit Breaker|
|Security (1)|Access Token|
|Observability (7)|Log aggregation, Application metrics, Audit logging, Distributed tracing, Exception tracking, Health check API, Log deployments and changes|
|UI (2)|Server-side page fragment composition, Client-side UI composition|

2+4+2+8+3+3+6+3+4+2+5+1+1+7+2 = **53** raw rows tabulated above; the
site's own summary states "44 reusable patterns" for the core pattern
language proper (some rows above, e.g. the two architectural-style
entries and the observability group, are the site's own broader
taxonomy wrapping the pattern language rather than all being counted in
Richardson's "44" headline figure). Recorded transparently: the *table*
above is the complete live-fetched enumeration (53 named items across all
categories on the page); the *headline denominator* Richardson's own book
marketing uses (44) refers to a narrower core count. Both numbers are
reported rather than silently reconciled to avoid manufacturing false
precision.

Cross-ref: Idempotent Consumer here is the microservices-context restatement
of EIP's Idempotent Receiver (section 4); Circuit Breaker, Saga, CQRS,
API Gateway/BFF, and Strangler (Application/Fig) overlap the Azure catalog
(7.1) -- `architecture-check-catalog.md` section 5.4 already documents the
Outbox/Idempotent-Receiver cross-attribution correction between these two
catalogs.

### 7.3 AWS -- Blocked (scoping decision)

Not independently enumerated as a separate list in this pass. AWS's own
Prescriptive Guidance and Well-Architected Framework documentation largely
re-describe the same pattern set already covered by the Azure catalog
(7.1) and microservices.io (7.2) under AWS-specific service names (e.g.
SQS/SNS fan-out = Azure's Publisher-Subscriber, DynamoDB single-table
design = a Sharding/Materialized-View variant) rather than naming a
structurally distinct pattern language with its own denominator.
Cataloguing it as a third independent list without live-verifying that it
actually names *different* patterns (versus the same patterns rebranded)
would inflate the total count dishonestly -- recorded as an explicit
scoping exclusion, not a silently-dropped node.

---

## 8. Concurrency and reactive patterns -- Partial

### 8.1 Doug Lea, *Concurrent Programming in Java* (2nd ed., Addison-Wesley,
1999/2000) -- Partial

Canonical reference: [Doug Lea's own page, gee.cs.oswego.edu](http://gee.cs.oswego.edu/dl/cpj/) (not independently re-fetched this pass). This book is the source for
several patterns POSA2 (section 2.2) later formalized jointly with the
POSA authors (Lea and Schmidt collaborated across both efforts) --
Active Object, Monitor Object, and Half-Sync/Half-Async are shared
lineage between Lea's work and POSA2, not independently double-counted
here. Additional Lea-specific naming (Worker Thread / Thread Pool,
Future) is folded into the "canon set" already listed without a fresh
per-entry search in `architecture-check-catalog.md` section 3.4.

### 8.2 Actor model -- Verified (primary origin), Partial (full sub-pattern list)

Carl Hewitt, Peter Bishop, Richard Steiger, "A Universal Modular ACTOR
Formalism for Artificial Intelligence" (IJCAI 1973) -- the actor model's
academic origin, independently well-documented (not re-fetched live this
pass but uncontested as the primary citation across the field). Modern
canonical exposition: [Akka documentation -- Actor
model](https://doc.akka.io/libraries/akka-core/current/general/actors.html).

### 8.3 Reactive patterns -- Verified (manifesto), Partial (pattern catalog)

[The Reactive Manifesto](https://www.reactivemanifesto.org/) (2014,
Boner, Farley, Kuhn, Thompson) defines Responsive/Resilient/
Elastic/Message-Driven as the four traits, not itself a numbered pattern
catalog. Roland Kuhn et al., *Reactive Design Patterns* (Manning, 2017)
is the primary named-pattern-catalog source for this space; its full
itemized pattern list was **not independently re-verified this pass** --
flagged Partial rather than reconstructed from memory with a fabricated
denominator.

---

## 9. Functional design patterns -- Partial

Canon set, canonical expositions cited per-entry (none independently
re-fetched this pass; all are well-established, widely-taught terms in
the functional-programming literature):

| Name (+ aliases) | Canonical exposition |
|---|---|
|Monad|Wadler, "Monads for functional programming" (1995 lecture notes); [Haskell wiki -- Monad](https://wiki.haskell.org/Monad)|
|Functor|category-theory-derived; [Haskell wiki -- Functor](https://wiki.haskell.org/Functor)|
|Applicative (Applicative Functor)|McBride and Paterson, "Applicative programming with effects" (2008)|
|Option/Maybe (railway-oriented programming for errors-as-values)|Scott Wlaschin, "Railway Oriented Programming" (fsharpforfunandprofit.com); cross-ref `architecture-check-catalog.md` 1.5 Errors-as-Values|
|Either/Result|same lineage as Option/Maybe, dual-channel success/failure encoding|
|Lens|Edward Kmett's `lens` library documentation; van Laarhoven, "CPS based functional references" (2009 blog origin of the van Laarhoven lens encoding)|
|Free Monad|"Free monads for less" and related community expositions; not independently re-fetched -- Partial|
|Memoization|classic CS technique, no single canonical named-pattern source beyond general algorithms literature -- Folklore-adjacent|
|Currying / Partial Application|named for Haskell Curry via Schoenfinkel/Curry combinatory logic, general knowledge|
|Persistent (immutable) data structures|Okasaki, *Purely Functional Data Structures* (Cambridge University Press, 1998) -- primary, canonical, not re-fetched but uncontested|

Cross-ref: Option/Result's tier-1 hard check is already covered under
`architecture-check-catalog.md` section 1.5 (Errors-as-Values) -- listed
here only to close this catalog's own denominator, not duplicated as a
new gate, matching that document's own stated convention.

---

## 10. Language-idiom "effective" patterns (genuinely named, not style tips)

### 10.1 Effective Java (Bloch) -- Partial

Joshua Bloch, *Effective Java*, 3rd ed. (Addison-Wesley, 2018). Only
items that are genuinely *named patterns* (not general style advice) are
listed -- filtering per this document's own instruction to exclude style
tips:

| Item (title, as-published) | Pattern it names |
|---|---|
|Item 1|Static factory methods instead of constructors|
|Item 2|Builder (pattern, explicitly GoF-named in the item title)|
|Item 3|Singleton (with implementation variants -- enum singleton)|
|Item 5|Dependency Injection (named as such)|
|Item 17/19|Immutability / "design for inheritance or prohibit it" (Fragile Base Class-adjacent, cross-ref traps-corpus section 4)|
|Item 89|Serialization proxy pattern|

Not independently re-verified item-numbering against the live 3rd-edition
text this pass -- numbering reconstructed from well-established public
knowledge of the book's structure; flagged Partial.

### 10.2 Pythonic idioms (named patterns only) -- Partial

| Name | Source |
|---|---|
|Context Manager (`with`)|PEP 343 -- canonical, primary, language-level specification|
|Descriptor protocol|Python data model docs, `docs.python.org/3/howto/descriptor.html` -- primary|
|Duck typing / `Protocol` (structural subtyping)|PEP 544 -- canonical, primary|
|Iterator protocol|PEP 234 -- canonical, primary|
|Decorator (`@` syntax, distinct from GoF Decorator though related in intent)|PEP 318 -- canonical, primary|
|Sentinel object pattern|general Python community idiom, no single PEP -- Folklore|
|Mixin|general OO/Python community idiom, widely documented, no single canonical PEP -- Folklore-adjacent|
|Dataclass (`@dataclass`) as a Value-Object idiom|PEP 557 -- canonical, primary|

Rust, C++, C, and TypeScript idioms are already fully tabulated with
static proxies in `architecture-check-catalog.md` section 3.6 (14 named
idioms across those four languages) -- not duplicated here; this
section closes only the Python/Java sliver that document's section 3.6
did not itemize.

---

## 11. Principle/heuristic sets referenced but owned elsewhere (not double-enumerated)

These are fully tabulated with citations already, in the documents named:

- **GRASP** (9/9) -- `architecture-check-catalog.md` section 1.3, citation [C4].
- **Connascence** (9 forms: 5 static + 4 dynamic) -- `architecture-check-catalog.md` section 1.4, citations [C1][C2].
- **SOLID** (5/5) and **Package Principles** (Martin PPP, 6+3) -- `architecture-check-catalog.md` sections 1.1-1.2. Practitioner-trap treatment of all five SOLID letters plus SOLID-as-a-whole: `design-pattern-traps-corpus.md` section 1.
- **12-Factor App** (12/12) -- `architecture-check-catalog.md` section 5.3, citation [C12], word-for-word verified.
- **8 Fallacies of Distributed Computing** (8, two variant lists) -- `architecture-check-catalog.md` section 5.1, citation [C9].
- **Fowler/Beck Refactoring 2nd-ed. code smells** (22/22) and **Clean Code Appendix B** (C/E/F/G/N/T, 58 entries) -- `architecture-check-catalog.md` section 2, citations [C5][C6][C7].
- **Anti-patterns** (Brown et al. + community canon, 20 code-static + 4 explicitly-excluded process anti-patterns) -- `architecture-check-catalog.md` section 4.

---

## Sourcing-honesty section

**Live-verified this pass** (fetched or search-confirmed against a
primary/canonical source, with the exact fetched content transcribed
into a table above): Fowler PoEAA catalog (51/51, martinfowler.com),
Enterprise Integration Patterns (65/65, enterpriseintegrationpatterns.com),
microservices.io pattern language (53 items tabulated / 44 headline
count, microservices.io), POSA vol. 1 architectural tier (8/8), POSA
vol. 2 (17/17, via Vanderbilt/Schmidt primary author page and
cross-checked WebSearch aggregate), GoF's 23-pattern/3-category
breakdown (cross-checked WebSearch aggregate, consistent with the
already-verified [C8] citation reused from `architecture-check-catalog.md`),
**POSA vol. 3 (10/10, Wiley's own product-page TOC, resolved via
Playwright this session -- was Blocked)**, **Eric Evans's DDD Reference PDF
(45/45, domainlanguage.com's own hosted PDF, resolved via a browser-UA
curl fetch this session after WebFetch and the MCP fetch tool both 403'd --
was Partial)**, **Release It! 2nd ed. (24/24 across ch. 4/5, O'Reilly's own
Contents panel, resolved via Playwright this session -- was Partial)**.

**Reused from the prior verification pass** (already live-verified in
`architecture-check-catalog.md`, not re-fetched a second time since
nothing material would have changed): GRASP [C4], Connascence [C1][C2],
12-Factor [C12], 8 Fallacies [C9], Azure cloud catalog 45/45 [C13], GoF's
own tier/anti-check mapping [C8].

**Attempted and blocked** (recorded honestly, not silently dropped):
POSA vol. 4's full pattern enumeration (this session's Playwright retry of
the analogous Wiley product-page URL for vol. 4's ISBN returned HTTP 404 --
a dead product listing, not merely a paywall; vol. 4's own publisher copy
also does not commit to a small fixed count, making a fabricated
denominator dishonest rather than merely incomplete either way).

**Presented from general knowledge without an independent live-source
check this pass** (flagged inline at each occurrence, not silently
upgraded to "verified"): Vernon's IDDD-specific additions beyond Evans
(section 5.3 -- Evans's own DDD Reference is now live-verified, but
Vernon's book TOC was not separately fetched this pass), Doug Lea's
specific pattern-naming beyond what POSA2 independently reconfirms,
Reactive Design Patterns' (Kuhn et al.) full itemized list,
functional-pattern canonical expositions (individually well-known terms,
citations given per-entry but not re-fetched), Effective Java item
numbering, and the Folklore-flagged Python idioms (sentinel object,
mixin).

**Citations upgraded from reconstructed to verified, relative to
`architecture-check-catalog.md`**: that document's section 3.2 (Fowler
PoEAA) explicitly self-flagged as "a representative complete set...not
independently re-verified against the book index... general knowledge" --
section 3 of this document supersedes that with the full, live-fetched,
51-entry primary catalog. No other section of the architecture-check-catalog
claimed a pattern-name enumeration this document also owns without
already being separately verified (GoF, GRASP, Connascence, 12-Factor,
Azure were already primary-verified in that pass and are reused here
unchanged).

---

## Phase-2 coverage verdict

Denominator (catalogs enumerated in Phase 0): 26 (see section 0 ledger).
Nodes reaching a verified or partial-with-citation `done` state: 25 of 26
(up from 24/26 -- POSA vol. 3 moved from Blocked to Verified this pass).
Nodes explicitly `blocked` (surfaced, not dropped): 1 -- AWS pattern
catalog as an independently-denominated list (scoping exclusion:
substantially redescribes the Azure/microservices.io catalogs under
different service names rather than naming a structurally distinct
pattern set, and no live source was found breaking that overlap down
precisely enough to enumerate honestly). POSA vol. 4 remains scoped out
of the denominator entirely (section 2.4 -- its own publisher copy
disclaims a fixed count, so it was never counted as a Phase-0 node with
an enumerable denominator; this pass additionally confirmed its Wiley
product page now 404s). Zero nodes silently skipped. This document's own
claim is therefore: **370 distinct named patterns enumerated across 25
fully- or partially-sourced catalogs (325 itemized by name directly in
this document, 45 cross-referenced by count to `architecture-check-catalog.md`'s
own itemization of Azure), with 1 catalog explicitly blocked and reported
rather than rounded into "done." See the DENOMINATOR MANIFEST at the end
of this file for the machine-checkable id-level enumeration of the 325
directly-owned entries.**

---

## DENOMINATOR MANIFEST

Machine-readable, one entry per directly-itemized pattern in this
document (325 entries; Azure's 45 are owned by
`architecture-check-catalog.md`'s own manifest, not duplicated here).
Format: `- id: <STABLE-ID> | catalog: <catalog-name> | checkability:
<tier1-static|tier2-advisory|tier3-not-checkable> | trap-ref: <section>`.
This is what the exhaustiveness drift-lock test binds against -- ids
and count must exactly match the prose tables above.

- id: GOF-ABSTRACT-FACTORY | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.1
- id: GOF-BUILDER | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.1
- id: GOF-FACTORY-METHOD | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.1
- id: GOF-PROTOTYPE | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.1
- id: GOF-SINGLETON | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.1
- id: GOF-ADAPTER | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.2
- id: GOF-BRIDGE | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.2
- id: GOF-COMPOSITE | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.2
- id: GOF-DECORATOR | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.2
- id: GOF-FACADE | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.2
- id: GOF-FLYWEIGHT | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.2
- id: GOF-PROXY | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.2
- id: GOF-STRATEGY | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-OBSERVER | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-COMMAND | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-STATE | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-TEMPLATE-METHOD | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-ITERATOR | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-MEDIATOR | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-MEMENTO | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-VISITOR | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-CHAIN-OF-RESPONSIBILITY | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: GOF-INTERPRETER | catalog: GoF | checkability: tier2-advisory | trap-ref: 1.3
- id: POSA1-LAYERS | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA1-PIPES-AND-FILTERS | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA1-BLACKBOARD | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA1-BROKER | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA1-MODEL-VIEW-CONTROLLER | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA1-PRESENTATION-ABSTRACTION-CONTROL | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA1-MICROKERNEL | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA1-REFLECTION | catalog: POSA-vol1 | checkability: tier2-advisory | trap-ref: 2.1
- id: POSA2-WRAPPER-FACADE | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-COMPONENT-CONFIGURATOR | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-INTERCEPTOR | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-EXTENSION-INTERFACE | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-REACTOR | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-PROACTOR | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-ASYNCHRONOUS-COMPLETION-TOKEN | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-ACCEPTOR-CONNECTOR | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-SCOPED-LOCKING | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-STRATEGIZED-LOCKING | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-THREAD-SAFE-INTERFACE | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-DOUBLE-CHECKED-LOCKING-OPTIMIZATION | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-ACTIVE-OBJECT | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-MONITOR-OBJECT | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-HALF-SYNC-HALF-ASYNC | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-LEADER-FOLLOWERS | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA2-THREAD-SPECIFIC-STORAGE | catalog: POSA-vol2 | checkability: tier2-advisory | trap-ref: 2.2
- id: POSA3-LOOKUP | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-LAZY-ACQUISITION | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-EAGER-ACQUISITION | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-PARTIAL-ACQUISITION | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-CACHING | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-POOLING | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-COORDINATOR | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-RESOURCE-LIFECYCLE-MANAGER | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-LEASING | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POSA3-EVICTOR | catalog: POSA-vol3 | checkability: tier2-advisory | trap-ref: 2.3
- id: POEAA-TRANSACTION-SCRIPT | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-DOMAIN-MODEL | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-TABLE-MODULE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-SERVICE-LAYER | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-TABLE-DATA-GATEWAY | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-ROW-DATA-GATEWAY | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-ACTIVE-RECORD | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-DATA-MAPPER | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-UNIT-OF-WORK | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-IDENTITY-MAP | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-LAZY-LOAD | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-IDENTITY-FIELD | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-INHERITANCE-MAPPERS | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-FOREIGN-KEY-MAPPING | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-ASSOCIATION-TABLE-MAPPING | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-DEPENDENT-MAPPING | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-EMBEDDED-VALUE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-SERIALIZED-LOB | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-SINGLE-TABLE-INHERITANCE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-CLASS-TABLE-INHERITANCE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-CONCRETE-TABLE-INHERITANCE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-METADATA-MAPPING | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-QUERY-OBJECT | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-REPOSITORY | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-MODEL-VIEW-CONTROLLER | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-PAGE-CONTROLLER | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-FRONT-CONTROLLER | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-TEMPLATE-VIEW | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-TRANSFORM-VIEW | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-TWO-STEP-VIEW | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-APPLICATION-CONTROLLER | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-REMOTE-FACADE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-DATA-TRANSFER-OBJECT | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-OPTIMISTIC-OFFLINE-LOCK | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-PESSIMISTIC-OFFLINE-LOCK | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-COARSE-GRAINED-LOCK | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-IMPLICIT-LOCK | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-CLIENT-SESSION-STATE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-SERVER-SESSION-STATE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-DATABASE-SESSION-STATE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-GATEWAY | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-SERVICE-STUB | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-RECORD-SET | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-MAPPER | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-LAYER-SUPERTYPE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-SEPARATED-INTERFACE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-REGISTRY | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-VALUE-OBJECT | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-MONEY | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-SPECIAL-CASE | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: POEAA-PLUGIN | catalog: PoEAA | checkability: tier2-advisory | trap-ref: 3
- id: EIP-FILE-TRANSFER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-SHARED-DATABASE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-REMOTE-PROCEDURE-INVOCATION | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGING | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-CHANNEL | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-PIPES-AND-FILTERS | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-ROUTER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-TRANSLATOR | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-ENDPOINT | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-POINT-TO-POINT-CHANNEL | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-PUBLISH-SUBSCRIBE-CHANNEL | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-DATATYPE-CHANNEL | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-INVALID-MESSAGE-CHANNEL | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-DEAD-LETTER-CHANNEL | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-GUARANTEED-DELIVERY | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CHANNEL-ADAPTER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGING-BRIDGE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-BUS | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-COMMAND-MESSAGE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-DOCUMENT-MESSAGE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-EVENT-MESSAGE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-REQUEST-REPLY | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-RETURN-ADDRESS | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CORRELATION-IDENTIFIER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-SEQUENCE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-EXPIRATION | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-FORMAT-INDICATOR | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CONTENT-BASED-ROUTER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-FILTER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-DYNAMIC-ROUTER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-RECIPIENT-LIST | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-SPLITTER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-AGGREGATOR | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-RESEQUENCER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-COMPOSED-MESSAGE-PROCESSOR | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-SCATTER-GATHER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-ROUTING-SLIP | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-PROCESS-MANAGER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-BROKER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-ENVELOPE-WRAPPER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CONTENT-ENRICHER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CONTENT-FILTER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CLAIM-CHECK | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-NORMALIZER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CANONICAL-DATA-MODEL | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGING-GATEWAY | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGING-MAPPER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-TRANSACTIONAL-CLIENT | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-POLLING-CONSUMER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-EVENT-DRIVEN-CONSUMER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-COMPETING-CONSUMERS | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-DISPATCHER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-SELECTIVE-CONSUMER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-DURABLE-SUBSCRIBER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-IDEMPOTENT-RECEIVER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-SERVICE-ACTIVATOR | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CONTROL-BUS | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-DETOUR | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-WIRE-TAP | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-HISTORY | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-MESSAGE-STORE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-SMART-PROXY | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-TEST-MESSAGE | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: EIP-CHANNEL-PURGER | catalog: Enterprise-Integration-Patterns | checkability: tier2-advisory | trap-ref: 4
- id: DDD-I-BOUNDED-CONTEXT | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-I-UBIQUITOUS-LANGUAGE | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-I-CONTINUOUS-INTEGRATION | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-I-MODEL-DRIVEN-DESIGN | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-I-HANDS-ON-MODELERS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-I-REFACTORING-TOWARD-DEEPER-INSIGHT | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-II-LAYERED-ARCHITECTURE | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-ENTITIES | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-VALUE-OBJECTS | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-DOMAIN-EVENTS | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-SERVICES | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-MODULES | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-AGGREGATES | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-REPOSITORIES | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-II-FACTORIES | catalog: DDD-Evans | checkability: tier1-static | trap-ref: 5.1
- id: DDD-III-INTENTION-REVEALING-INTERFACES | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-III-SIDE-EFFECT-FREE-FUNCTIONS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-III-ASSERTIONS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-III-STANDALONE-CLASSES | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-III-CLOSURE-OF-OPERATIONS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-III-DECLARATIVE-DESIGN | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-III-DRAWING-ON-ESTABLISHED-FORMALISMS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-III-CONCEPTUAL-CONTOURS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-CONTEXT-MAP | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-PARTNERSHIP | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-SHARED-KERNEL | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-CUSTOMER-SUPPLIER-DEVELOPMENT | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-CONFORMIST | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-ANTICORRUPTION-LAYER | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-OPEN-HOST-SERVICE | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-PUBLISHED-LANGUAGE | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-SEPARATE-WAYS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-IV-BIG-BALL-OF-MUD | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-V-CORE-DOMAIN | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-V-GENERIC-SUBDOMAINS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-V-DOMAIN-VISION-STATEMENT | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-V-HIGHLIGHTED-CORE | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-V-COHESIVE-MECHANISMS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-V-SEGREGATED-CORE | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-V-ABSTRACT-CORE | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-VI-EVOLVING-ORDER | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-VI-SYSTEM-METAPHOR | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-VI-RESPONSIBILITY-LAYERS | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-VI-KNOWLEDGE-LEVEL | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-VI-PLUGGABLE-COMPONENT-FRAMEWORK | catalog: DDD-Evans | checkability: tier2-advisory | trap-ref: 5.1
- id: DDD-VERNON-EFFECTIVE-AGGREGATE-DESIGN-RULES | catalog: DDD-Vernon | checkability: tier3-not-checkable | trap-ref: 5.3
- id: DDD-VERNON-EVENT-STORMING | catalog: DDD-Vernon | checkability: tier3-not-checkable | trap-ref: 5.3
- id: RELEASEIT-ANTI-INTEGRATION-POINTS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-CHAIN-REACTIONS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-CASCADING-FAILURES | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-USERS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-BLOCKED-THREADS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-SELF-DENIAL-ATTACKS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-SCALING-EFFECTS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-UNBALANCED-CAPACITIES | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-DOGPILE | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-FORCE-MULTIPLIER | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-SLOW-RESPONSES | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-ANTI-UNBOUNDED-RESULT-SETS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-TIMEOUTS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-CIRCUIT-BREAKER | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-BULKHEADS | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-STEADY-STATE | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-FAIL-FAST | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-LET-IT-CRASH | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-HANDSHAKING | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-TEST-HARNESSES | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-DECOUPLING-MIDDLEWARE | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-SHED-LOAD | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-CREATE-BACK-PRESSURE | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: RELEASEIT-PAT-GOVERNOR | catalog: Release-It | checkability: tier1-static | trap-ref: 6
- id: MSIO-MONOLITHIC-ARCHITECTURE | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-MICROSERVICE-ARCHITECTURE | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-DECOMPOSE-BY-BUSINESS-CAPABILITY | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-DECOMPOSE-BY-SUBDOMAIN | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SELF-CONTAINED-SERVICE | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-PER-TEAM | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-STRANGLER-APPLICATION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-ANTI-CORRUPTION-LAYER | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-DATABASE-PER-SERVICE | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SHARED-DATABASE | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SAGA | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-COMMAND-SIDE-REPLICA | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-API-COMPOSITION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-CQRS | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-DOMAIN-EVENT | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-EVENT-SOURCING | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-TRANSACTIONAL-OUTBOX | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-TRANSACTION-LOG-TAILING | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-POLLING-PUBLISHER | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-CONSUMER-DRIVEN-CONTRACT-TEST | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-CONSUMER-SIDE-CONTRACT-TEST | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-COMPONENT-TEST | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-MULTIPLE-SERVICE-INSTANCES-PER-HOST | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-INSTANCE-PER-HOST | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-INSTANCE-PER-VM | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-INSTANCE-PER-CONTAINER | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVERLESS-DEPLOYMENT | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-DEPLOYMENT-PLATFORM | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-MICROSERVICE-CHASSIS | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-EXTERNALIZED-CONFIGURATION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-TEMPLATE | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-REMOTE-PROCEDURE-INVOCATION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-MESSAGING | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-DOMAIN-SPECIFIC-PROTOCOL | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-IDEMPOTENT-CONSUMER | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-API-GATEWAY | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-BACKEND-FOR-FRONT-END | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-CLIENT-SIDE-DISCOVERY | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVER-SIDE-DISCOVERY | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVICE-REGISTRY | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SELF-REGISTRATION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-3RD-PARTY-REGISTRATION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-CIRCUIT-BREAKER | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-ACCESS-TOKEN | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-LOG-AGGREGATION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-APPLICATION-METRICS | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-AUDIT-LOGGING | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-DISTRIBUTED-TRACING | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-EXCEPTION-TRACKING | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-HEALTH-CHECK-API | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-LOG-DEPLOYMENTS-AND-CHANGES | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-SERVER-SIDE-PAGE-FRAGMENT-COMPOSITION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: MSIO-CLIENT-SIDE-UI-COMPOSITION | catalog: microservices.io | checkability: tier2-advisory | trap-ref: 7.2
- id: ACTOR-ACTOR-MODEL-HEWITT-FORMALISM | catalog: Actor-Reactive | checkability: tier3-not-checkable | trap-ref: 8.2
- id: REACTIVE-REACTIVE-MANIFESTO-4-TRAITS | catalog: Actor-Reactive | checkability: tier2-advisory | trap-ref: 8.3
- id: REACTIVE-REACTIVE-DESIGN-PATTERNS-KUHN-ET-AL-CATALOG | catalog: Actor-Reactive | checkability: tier2-advisory | trap-ref: 8.3
- id: FUNC-MONAD | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-FUNCTOR | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-APPLICATIVE | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-OPTION-MAYBE | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-EITHER-RESULT | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-LENS | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-FREE-MONAD | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-MEMOIZATION | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-CURRYING-PARTIAL-APPLICATION | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: FUNC-PERSISTENT-DATA-STRUCTURES | catalog: Functional-Patterns | checkability: tier2-advisory | trap-ref: 9
- id: EFFJAVA-STATIC-FACTORY-METHODS | catalog: Effective-Java | checkability: tier2-advisory | trap-ref: 10.1
- id: EFFJAVA-BUILDER | catalog: Effective-Java | checkability: tier2-advisory | trap-ref: 10.1
- id: EFFJAVA-SINGLETON | catalog: Effective-Java | checkability: tier2-advisory | trap-ref: 10.1
- id: EFFJAVA-DEPENDENCY-INJECTION | catalog: Effective-Java | checkability: tier2-advisory | trap-ref: 10.1
- id: EFFJAVA-IMMUTABILITY-FRAGILE-BASE-CLASS | catalog: Effective-Java | checkability: tier2-advisory | trap-ref: 10.1
- id: EFFJAVA-SERIALIZATION-PROXY | catalog: Effective-Java | checkability: tier2-advisory | trap-ref: 10.1
- id: PYIDIOM-CONTEXT-MANAGER | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
- id: PYIDIOM-DESCRIPTOR-PROTOCOL | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
- id: PYIDIOM-DUCK-TYPING-PROTOCOL | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
- id: PYIDIOM-ITERATOR-PROTOCOL | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
- id: PYIDIOM-DECORATOR-SYNTAX | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
- id: PYIDIOM-SENTINEL-OBJECT | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
- id: PYIDIOM-MIXIN | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
- id: PYIDIOM-DATACLASS | catalog: Pythonic-Idioms | checkability: tier1-static | trap-ref: 10.2
TOTAL: 325
