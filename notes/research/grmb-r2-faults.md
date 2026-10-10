# grmb R2 (early), topic H: ambient faults and exhaustive error handling

Ticket ~5QA6P6W, researcher H. Date 2026-10-09. ASCII only. Not committed.

Design target evaluated (owner revision received mid-run, 2026-10-09):
there is NO separate pedantic profile. Every system declares ONE
ambient-fault policy (for example propagate to supervisor, crash the
step, retry); scenarios inherit it and may override it per scenario;
the checker treats the ambient class like any other outcome arm
(exhaustive, so no scenario can silently ignore it). Also evaluated: the
error-flow facts of ticket ~589WNWE (Rust Exact, Python May, TS Unknown;
non-exact sets surface through the opaque-cone Unresolved path; an
explicit outcome map is the claim that resolves them conditionally under
D121, verified by per-arm tests).

Verdict in one paragraph (details in section 4): the design HOLDS in
shape, with four amendments the evidence forces. (A1) The ambient class
must be a separate, closed namespace that a `_` arm, an outcome map and
a domain variant can never match or be fed from (the over-catch failure
mode, Yuan et al. 2014, and the Error/Exception, BaseException/Exception
and "universal error" splits in Java, Python and Swift). (A2) `retry` is
sound only for idempotent steps, so the policy needs a per-STEP
idempotency fact (not a per-step policy); a scenario-level `retry` over
a non-idempotent step must fire. (A3) Every restart or retry policy is
bounded and ends in an explicit escalation (OTP restart intensity,
Kubernetes back-off, Gray's Bohrbug test, SRE retry budgets), and retries
are declared at one layer only (retry amplification). (A4) Containment
(who restarts what) is a property of the isolation unit, which in grmb is
the NODE an impl runs in, not the scenario; the scenario override says
what the scenario does when it loses a step, the system or node default
says who recovers. The noise cost of the inherited design is about one
line per system plus rare overrides, against the documented failure of
the per-call-site alternative (Java checked exceptions).

## 1. Scope and search log

### 1.1 Field enumeration (done before reading)

| # | Node | Status |
|---|---|---|
| 1 | Language error models: Java (checked/unchecked/Error), Kotlin, C#, Python, TypeScript, Rust, Go, Swift, Zig, C++, Erlang | done (official spec or vendor doc fetched for each) |
| 2 | Ambient-fault behaviour per runtime: OOM, stack overflow, recursion limit, signals/interrupts, cancellation, exit, kill | done (official docs for Python, Rust, Go, .NET, Zig, POSIX via Python signal doc, Linux overcommit, Kubernetes) |
| 3 | Fault-tolerance architecture: fail-fast and process pairs (Gray), let-it-crash and supervisors (Armstrong, OTP), crash-only and microreboot (Candea, Fox), abandonment (Midori), container restart (Kubernetes) | done |
| 4 | Retry practice: idempotency, amplification, budgets | done (AWS Builders' Library x2, Google SRE book) |
| 5 | Checked-exceptions debate and its evidence | done (JLS rationale, Hejlsberg, Duffy, Sutter P0709, Swift rationale and SE-0413, MSR studies) |
| 6 | Empirical exception-handling bug studies (Yuan OSDI 2014 and follow-ups) | done for abstracts and Yuan full text; partial for Ebert JSS 2015, Coelho EMSE 2016, Gao FSE 2018, Cassee MSR 2018 (abstract or metadata only) |
| 7 | Empirical evidence on OOM handling | done (P0709 R4 section 4.3 full text: VC++ STL, PowerPoint, Word fault-injection) |
| 8 | Static exception-flow analysis (Java Jex, exception chains, ML row types, resource-leak dataflow, Python abstract interpretation, Java exception preconditions) | done (abstracts); Monat thesis chapter not read |
| 9 | Tools that expose raised sets or panics: pydoclint, ruff BLE001, mypy, TypeScript, CA1031, clippy, no-panic, anyhow | done |
| 10 | Rust panic studies | done (abstracts: Qin PLDI 2020, Qin TSE 2024, PanicFI) |
| 11 | Exception-handling testing evidence (does per-arm verification happen?) | done (Lima et al. 2021, Hora and Fraser 2026, Yuan 2014) |
| 12 | Production incidents that turn on ambient-fault policy | done (Cloudflare 2025-11-18 postmortem; Yuan HDFS over-catch case) |
| 13 | Async exceptions in functional runtimes (Haskell), OCaml effects, Ada, Akka supervision | located only (Marlow et al. PLDI 2001 metadata); not read, see 1.4 |

Denominator 13 nodes: done 11 (1-5, 7-12), partial 1 (6), located-only 1 (13).

### 1.2 Queries and lookups run

- WebSearch: Yuan OSDI 2014; static analysis uncaught exceptions Python;
  Rust panic empirical; Cloudflare 2025-11-18 unwrap; Rust OOM/stack
  overflow behaviour; Candea Fox crash-only; Armstrong thesis; P0709 OOM;
  Gray 1985; Go fatal errors; Ebert JSS 2015; Monat thesis; no-panic;
  Torvalds Rust allocation; Swift rationale authorship; Duffy Midori
  role; Sutter role; Gao FSE 2018; Cassee MSR 2018.
- WebFetch (primary text): usenix Yuan page; Cloudflare postmortem; JLS
  SE 21 ch. 11 (and curl of 11.2); java.lang.Error javadoc; Python
  exceptions, signal and asyncio-exceptions docs; Rust book ch. 9.3;
  catch_unwind doc; Rust reference non_exhaustive; anyhow doc; Swift
  SE-0413; Swift ErrorHandlingRationale; Go blog defer/panic/recover; Go
  FAQ; runtime/debug doc; OTP supervisor principles; crash-only HTML;
  AWS Builders' Library (retries; idempotent APIs); Google SRE ch. 22;
  .NET StackOverflowException, OutOfMemoryException, CA1031; TS 4.4
  notes; TS issue 13219; mypy issue 11282; pydoclint codes; ruff BLE001;
  cppreference noexcept; Linux overcommit-accounting; Kubernetes pod
  lifecycle; Kotlin exceptions; Hejlsberg interview; Duffy "The Error
  Model" (two passes) and "Blogging about Midori".
- Full texts read with pdftotext: Yuan et al. OSDI 2014; Sutter P0709R4;
  Armstrong thesis 2003; Gray TR 85.7.
- Crossref `query.bibliographic` (about 35 queries) for every paper;
  OpenAlex abstracts for 23 DOIs; Semantic Scholar for 3; arXiv API
  (abstract-field searches: exception+python, uncaught exceptions,
  exception handling empirical, panic+rust, error handling+rust, checked
  exceptions, exception flow, let it crash, exception handling+LLM) and
  `id_list` abstracts for 4 papers. The clippy lint index was curled and
  grepped for lint names and groups. GitHub API for the authorship of
  Swift's ErrorHandlingRationale.

### 1.3 Exclusions

Anonymous blogs, Medium/dev.to posts and aggregator summaries surfaced by
search were excluded (they appeared for Cloudflare and Swift). Secondary
summaries were used only to locate primaries; every number below is
from the primary unless tagged.

### 1.4 What remains unread and why it would not change the conclusions

- Full texts of Ebert et al. JSS 2015, Coelho et al. EMSE 2016, Gao et
  al. FSE 2018, Cassee et al. MSR 2018, Qin et al. TSE 2024 and Monat's
  thesis chapter on exceptions. Their abstracts point in the same
  direction as the read full texts (handlers are under-tested, generic
  catches are common, crash recovery is itself buggy); none could
  overturn the granularity question, which rests on the architecture
  sources.
- Haskell asynchronous exceptions (Marlow et al. PLDI 2001), OCaml 5
  effects, Ada, Akka supervision: located or known, not read. Akka copies
  the OTP model; Haskell's mask/bracket is a mechanism for writing code
  robust to async interruption, which would add a detail to the
  `interrupted` class (F14) and not change the policy set.
- Joshua Bloch, Effective Java (book) and Bruce Eckel's 2003 article: not
  retrievable as primary text this run; their positions are already
  represented by the Nakshatri study (which used Bloch as reference) and
  the Hejlsberg interview (Eckel co-interviewer).

### 1.5 Coverage argument

The question has three axes: (a) what ambient faults exist and how each
runtime surfaces them, (b) what policies work at what granularity, (c)
what can be known statically about error sets and what declaring them
costs. Axis (a) is covered by the official specification of every
mainstream language grimble binds or is likely to bind (section 3). Axis
(b) is covered by the four canonical fault-tolerance lineages (Tandem
fail-fast and process pairs, Erlang/OTP supervision, Berkeley/Stanford
recovery-oriented computing, Microsoft Midori abandonment) plus the two
operational sources with the largest deployments (Kubernetes, Google
SRE, AWS). Axis (c) is covered by the static exception-analysis line
from Robillard/Murphy (2003) to Marcilio/Furia (2022) and by the
empirical MSR/ICSE/OSDI studies of handler quality. A new source could
add a language row or a statistic; it is unlikely to add a policy
outside {escalate, restart, retry, terminate} because the four lineages
converge on that set independently.

## 2. Findings

Strength tags: [E] empirical study; [X] experience report from a named
organisation; [V] vendor or standards document; [O] expert opinion.

### 2.1 Taxonomy: ambient faults are a separate category everywhere

F1. Every mature error model separates "errors the caller plans for"
from "faults that can happen anywhere". Java: Error is exempt from
`throws` because errors "can occur at many points in the program and
recovery from them is difficult or impossible. A program declaring such
exceptions would be cluttered, pointlessly" (JLS 11.2); the Error javadoc
says an Error indicates "serious problems that a reasonable application
should not try to catch". Python: KeyboardInterrupt, SystemExit,
GeneratorExit and (since 3.8) asyncio.CancelledError derive from
BaseException, not Exception, "so as to not be accidentally caught by
code that catches Exception". Swift's rationale names "universal errors"
(cancellation, SIGINT, out of memory, stack overflow) and states typed
propagation of them is impossible and marked propagation unworkable.
P0709 states that programming bugs and abstract-machine corruption are
"never an error" and should be reported to a human, by default
fail-fast; "Stack exhaustion is always an abstract machine corruption (a
function cannot guard against it)". [V] JLS SE 21; Python docs; Swift
ErrorHandlingRationale (John McCall, Apple); [O+X] Sutter P0709R4.
Grade: strong (four independent designs converge).

F2. Within the ambient category there are at least four behaviourally
different classes, and runtimes treat them differently:
- exhaustion (heap, stack, recursion limit): Rust aborts on allocation
  failure by default (handle_alloc_error) and on stack overflow (guard
  page handler prints and aborts); Go's stack limit "crashes" the program
  (runtime/debug SetMaxStack) and OOM is a fatal error; .NET's
  StackOverflowException cannot be caught and terminates the process;
  .NET OutOfMemoryException is catchable but documented as "a
  catastrophic failure" to handle with Environment.FailFast; Python
  raises MemoryError but "the interpreter may not always be able to
  completely recover"; RecursionError is an ordinary RuntimeError
  subclass; Zig is "not yet protected from stack overflow".
- defects (panic, assertion, unwrap of an unexpected value, index out
  of bounds): Rust book: panic when "some assumption, guarantee,
  contract, or invariant has been broken"; catch_unwind is "not
  recommended ... for a general try/catch mechanism" and does not catch
  aborting panics; Go converts panics to errors only inside packages
  ("even when a package uses panic internally, its external API still
  presents explicit error return values", Gerrand 2010).
- interruption (SIGINT/SIGTERM, KeyboardInterrupt, cancellation,
  SystemExit): Python delivers signal-handler exceptions "after any
  bytecode instruction"; "Most Python code, including the standard
  library, cannot be made robust against this"; high-reliability code
  should install its own SIGINT handler instead of catching
  KeyboardInterrupt. Kubernetes sends TERM, waits a grace period
  (default 30 s), then KILL.
- kill (SIGKILL, kernel OOM killer, node loss): "It cannot be caught,
  blocked, or ignored" (Python signal doc). Under Linux overcommit mode 0
  (the default) only "seriously wild" allocations fail, so heap
  exhaustion often arrives as the OOM killer rather than as an error.
  Only an outside party can observe it.
[V] Rust std and book; Go docs; .NET docs; Python docs; Zig 0.15.1
reference; Linux kernel docs; Kubernetes docs. Grade: strong.

F3. The "can it fail at all" bit is often knowable even when the set is
not: Swift untyped `throws` vs non-throwing; C++ `noexcept` (but NOT
checked: "a noexcept specification on a function is not a compile-time
check", violation calls std::terminate); Java checked vs no checked
exceptions. [V] Swift SE-0413; cppreference. Grade: strong.

### 2.2 What happens when ambient faults are handled locally

F4. OOM handling that is believed correct is usually not. Fault
injection (the babb library, Sutter and Clow 2019) crashed the VC++ STL
in default debug builds; PowerPoint File > Open, believed OOM-safe, was
"not actually OOM-safe" because of noexcept functions that allocate;
Microsoft Word, written to handle allocation failure, crashed in 98% of
executions with under 5 MB available; the Word team then built Word to
terminate unconditionally on allocation failure, rolled it out to all
users, and saw "no statistically significant change in crash rates on
Windows, Mac, iOS, or Android". Many teams (Visual C++ compiler, most
Office apps) "make no attempt to be allocation failure-resilient and
just terminate". [X] P0709R4 section 4.3 (Sutter, ISO C++ convener,
22 years at Microsoft). Grade: strong for desktop software; contested
for constrained or kernel code (F5).

F5. The counter-position is real and context-bound: Zig's convention is
that libraries return error.OutOfMemory because overcommit is not
universal (Windows, embedded, real-time); Linus Torvalds called
panicking on allocation in kernel Rust "fundamentally not acceptable"
and Rust-for-Linux adopted fallible allocation only; P1404 (Krzemienski,
Kaminski) argues bad_alloc is often a recoverable per-request limit, not
heap exhaustion. [V] Zig reference; [X] LKML 2021 thread (Torvalds,
Ojeda, Triplett); [O] WG21 P1404R1. Grade: strong that the right OOM
policy is a per-system decision, not a universal one.

F6. Async interruption cannot be made safe at every call site in
mainstream code (Python doc, F2). Midori abandoned on OOM by default with
an opt-in recoverable form "rarely used", and treated stack overflow the
same way. [V] Python; [X] Duffy 2016 (led the Midori developer-experience
groups at Microsoft 2009-2014, per his own account). Grade: strong.

### 2.3 Policies that work, and their preconditions

F7. Fail-fast plus redundancy is the base pattern: "Make each module
fail-fast -- either it does the right thing or stops"; process pairs
retry the operation; of 132 software faults in the Tandem spooler logs,
one was a Bohrbug (failed again on retry), the rest Heisenbugs; MVS
recovery routines succeeded 76% of the time. [X+E] Gray, Tandem TR 85.7,
1985. Grade: strong but old and single-site; retry pays because most
production faults are transient.

F8. Let it crash: "Let some other process do the error recovery. If you
can't do what you want to do, die. Let it crash. Do not program
defensively." Hardware and software failure use one mechanism (linked
process gets an EXIT message), "handling errors, not where they
occurred, but at some other place in the system"; design starts by
identifying the "error kernel" that must be correct. OTP encodes the
policy once per supervisor: strategy one_for_one, one_for_all,
rest_for_one, simple_one_for_one; child restart permanent, transient,
temporary; restart intensity MaxR in MaxT (default 1 in 5 s) after which
the supervisor terminates its children and itself and the parent
decides. [X] Armstrong thesis (Ericsson, AXD301); [V] OTP docs. Grade:
strong; the policy is declared per supervision subtree, never per call.

F9. Crash-only software: stop = crash, start = recover; preconditions:
important state in dedicated state stores, all resources leased, all
interactions have timeouts ("Infinite timeouts or leases are not
acceptable"), requests self-describing "on whether they are idempotent,
along with a time-to-live", RetryAfter as an optimisation. [O+E] Candea
and Fox, HotOS IX 2003 (Stanford, recovery-oriented computing). Grade:
medium-strong; the preconditions are the checkable part.

F10. Restart must be bounded and back off: Kubernetes restarts with
exponential back-off 10 s, 20 s, 40 s capped at 300 s, reset after 10
minutes of clean running; restartPolicy Always / OnFailure / Never per
pod. [V] Kubernetes docs. OTP intensity (F8). Grade: strong.

F11. Retry needs idempotency and one layer: "APIs with side effects
aren't safe to retry unless they provide idempotency"; retry "at a single
point in the stack"; token-bucket limits. Amazon's client request token
makes EC2 calls idempotent. Google: retries at three layers turned one
user action into "64 attempts (4^3)" on an overloaded database; limit
retries per request; server-wide retry budget; a "query of death" crashes
every task it reaches. [X] AWS Builders' Library (Featonby, Principal
Engineer AWS EC2/containers); Google SRE book ch. 22 (Ulrich). Grade:
strong.

F12. Uniform crash policy plus deterministic input = global outage. On
2025-11-18 an oversized Bot Management feature file (over the 200-feature
preallocated limit) reached every Cloudflare FL2 proxy; the Rust code
returned an Err that was unwrapped: "thread fl2_worker_thread panicked:
called Result::unwrap() on an Err value". Remediations: harden ingestion
of internal config "in the same way we would for user-generated input",
more global kill switches, stop core dumps overwhelming resources,
"Reviewing failure modes for error conditions across all core proxy
modules". [X] Cloudflare postmortem (Prince, CEO). Grade: strong single
incident; lesson: a domain error (bad input) was turned into a defect
(panic), and a crash-restart policy cannot fix a Bohrbug (Gray F7).

### 2.4 Handler quality: the empirical record

F13. Yuan et al.: of 198 user-reported failures in Cassandra, HBase,
HDFS, MapReduce and Redis, 92% of catastrophic failures came from
incorrect handling of non-fatal errors explicitly signalled in software;
35% from trivial mistakes: errors ignored (25%), abort in over-caught
exceptions (8%), TODO in handler (2%); in 58% the bug was reachable by
simple testing of the error-handling code. The over-catch example: HDFS
DataNode registration with `catch (Throwable t) { System.exit(-1); }`
brought down the whole cluster. They note developers did check errors
(Java forces checked exceptions) but were "simply sloppy in handling
these errors". [E] OSDI 2014 (U. Toronto). Grade: strong.

F14. Follow-ups: 210 exception bugs in six cloud systems, 74% affect
availability or integrity, 54% triggered by non-semantic conditions such
as network errors (Chen et al. ASE 2019); crash-recovery mechanisms are
themselves a major bug source (Gao et al. FSE 2018, 103 bugs; CrashTuner
SOSP 2019 found them by crash injection at meta-info accesses). [E]
Grade: strong that the recovery path needs its own tests.

F15. Generic catches and minimal handlers are widespread: Java projects
on GitHub log, print, return or rethrow in catch blocks, catching
Exception and empty catches are "widespread" (Kery et al. MSR 2016);
"most programmers ignore checked exceptions" and use classes high in the
hierarchy (Nakshatri et al. MSR 2016); 154 surveyed developers say
handlers are rarely documented or tested (Ebert and Castor ICSM 2013);
in Java and C#, catch Generic, Over-catch and Unhandled are the common
anti-patterns (de Padua and Shang ICPC 2017); Swift developers mostly
react to library errors and rarely define their own (Cassee et al. MSR
2018, abstract only). [E] Grade: strong.

F16. Handlers are less tested than the rest: catch blocks and throw
instructions are covered significantly less than other code in 27 Java
libraries (Lima et al. 2021); in 25 Python systems 21.4% of executed
methods raise at run time and exception-raising behaviour is "not
necessarily abnormal or rare" (Hora and Fraser 2026). [E] arXiv
preprints. Grade: medium (preprints) but consistent with F13.

### 2.5 The checked-exceptions debate: what declaration costs

F17. Per-signature declaration of open-ended exception sets decays:
Hejlsberg (C# designer): adding an exception breaks clients
(versionability), the problem grows with "four or five different
subsystems", developers write `throws Exception` which "completely
defeats the feature", and good code has about ten try/finally per
try/catch because handling should be centralised. Sutter: "in Java,
real-world uses of checked exception specifications quickly devolve to
throws Exception"; C++ removed dynamic exception specifications for
untyped noexcept. Kotlin: "Kotlin treats all exceptions as unchecked".
TypeScript declined a `throws` clause (issue 13219, closed "Declined");
mypy closed "Ability to specify and check possible unhandled exceptions"
as not planned (needs a PEP). [O] Hejlsberg 2003 (Artima); [O+X] Sutter;
[V] Kotlin, TS, mypy. Grade: strong as practice evidence.

F18. Where typed sets survive, they are narrow and internal: Swift
SE-0413 says untyped throws "remains the better default" and typed
throws are for code within a module, pass-through generics, and
constrained embedded code; "Resist the temptation to use typed throws
because there is only a single kind of error". Midori: 90-something
percent of functions could not throw, abandonment outnumbered
recoverable errors nearly 10:1, single-mode `throws` outnumbered typed
10:1, typed clauses were added after 2-3 years on request, and internal
typed exceptions were commonly translated to plain `throws` at public
boundaries. Zig: explicit sets recommended over inferred ones for
recursion and function pointers; `anyerror` is the open global set.
Rust: `#[non_exhaustive]` enums force a wildcard arm outside the defining
crate; anyhow is "a trait object based error type for easy idiomatic
error handling in Rust applications". [V] Swift, Zig, Rust reference,
anyhow; [X] Duffy. Grade: strong.

F19. Exactness is cheap where the set is closed and local, and declared
handling is valuable there: Sutter notes that when the set is statically
known, tools can tell that a handler tested "all but one or two" values
and flag a new error value at compile time; when it is open-ended,
"absent whole program analysis" this is much harder. [O+X] P0709.

### 2.6 Static error-flow analysis: what can be computed

F20. Exception flow is hard for humans and computable by tools for
typed OO languages: Jex reports the exception types that may reach each
program point (Robillard and Murphy TOSEM 2003); exception-chain analysis
reconstructs multi-link propagation paths in Java servers, many spanning
components (Fu and Ryder ICSE 2007); ML row-typed analysis of uncaught
exceptions is "efficient and precise" (Leroy and Pessaux TOPLAS 2000);
dataflow over exceptional paths found 1,300 resource-cleanup defects in
5 MLOC Java (Weimer and Necula TOPLAS 2008); WIT extracts exception
preconditions of Java methods with 100% precision on a manual sample
but incomplete coverage (Marcilio and Furia ICSME 2022). In Java and C#,
each try block has up to 12 possible propagated exceptions, 22% of
distinct exceptions trace to multiple methods, and documentation of
possible exceptions is lacking; flow analysis over well-documented APIs
(JRE, .NET) recovers it (de Padua and Shang SCAM 2017). [E] Grade:
strong.

F21. Python: sound uncaught-exception analysis exists only in research
abstract interpreters for subsets (Monat, Ouadjaout, Mine; Mopsa, incl.
Python/C), not in mainstream checkers; pydoclint checks only the
function's own `raise` statements against its docstring (DOC501-503);
ruff BLE001 flags `except Exception`/`BaseException` unless re-raised
or logged with exc_info. [E/V] Grade: strong that Python raise sets are
May at best.

F22. Rust panics are invisible in signatures: detection is by lints
(clippy restriction group: unwrap_used, expect_used, panic,
indexing_slicing, unwrap_in_result, panic_in_result_fn; pedantic group:
missing_panics_doc, missing_errors_doc) or by link-time proof
(no-panic, which fails to link if a function may panic and is "useless"
under panic = "abort"). 110 panic-causing programming errors were
studied by Qin et al. (TSE 2024); PanicFI collected 102 panic bugs from
the top 500 crates. [V/E] Grade: strong.

## 3. Per-language table: ambient fault classes and static error-set knowability

Columns: E = exhaustion (heap, stack, recursion limit), D = defects
(panic, assertion, bug exceptions), I = interruption (signals,
cancellation, exit), K = kill (uncatchable, only an outside observer
sees it). Knowability uses ~589WNWE's lattice: Exact (closed set
computed or declared and checked), May (a lower bound from visible
raises/returns; callees widen it), Unknown (open set); "fails?" is the
can-it-fail bit (F3).

| Language | E | D | I | K | Domain error set knowable statically | Notes and sources |
|---|---|---|---|---|---|---|
| Rust | heap: abort by default (handle_alloc_error), opt-in `try_reserve`; stack: guard page, abort | `panic!`, unwrap/expect, indexing, overflow in debug; unwinding or abort per profile; catch_unwind partial | signals not delivered as Rust values (crate-level handling) | SIGKILL | Exact when the unit returns `Result<T, E>` with E a concrete enum without `#[non_exhaustive]` from the same crate; Exact-plus-open for a foreign `#[non_exhaustive]` enum; Unknown for `Box<dyn Error>` / `anyhow::Error`; `?` maps through `From` impls (resolvable with types). Panics never in the set | F2, F18, F22 |
| Zig | `error.OutOfMemory` is an ordinary error value (allocator passed explicitly); stack overflow unprotected | safety-checked illegal behaviour panics; unchecked is UB | OS-level | SIGKILL | Exact (explicit or compiler-inferred error sets; merging `||`); Unknown for `anyerror` | Zig 0.15.1 reference |
| Go | OOM and stack limit are fatal runtime errors, not recoverable panics | panic/recover; runtime.throw faults (concurrent map writes) bypass recover | os/signal | SIGKILL | Unknown: `error` is an open interface; sentinel errors and `errors.Is` sites give May | Go FAQ, blog, runtime/debug |
| Swift | traps, not errors | traps (force unwrap, bounds) not catchable | universal errors out of scope of `throws` | SIGKILL | Exact with typed `throws(E)`; untyped `throws` gives fails? = Exact, set = Unknown (`any Error`) | SE-0413, rationale |
| Java / Kotlin | `OutOfMemoryError`, `StackOverflowError` (VirtualMachineError, may be asynchronous) | unchecked RuntimeException, AssertionError | Thread interrupts; shutdown hooks | SIGKILL | Checked: declared upper bound, compiler-checked in Java (Exact modulo code compiled by other JVM languages: Kotlin treats all as unchecked); unchecked: May via flow analysis (Jex, chains) | JLS 11, Error javadoc, Kotlin docs |
| C# | `OutOfMemoryException` catchable but "catastrophic"; `StackOverflowException` uncatchable, process terminated | any Exception; corrupted-state exceptions not delivered since .NET 4 | console cancel, PosixSignalRegistration (not verified this run) | SIGKILL | May: no declarations; XML doc `<exception>` is documentation only; flow analysis over documented APIs (de Padua) | .NET docs, CA1031 |
| C++ | `bad_alloc` (often never thrown under overcommit), stack overflow is abstract-machine corruption | UB, assertions, std::terminate on noexcept violation | signals | SIGKILL | fails? = claim via `noexcept` (unchecked, a D121-style claim); set = Unknown | P0709, cppreference |
| Python | `MemoryError` (partial recovery), `RecursionError` (a RuntimeError) | any Exception subclass; AssertionError | `KeyboardInterrupt`, `SystemExit`, `asyncio.CancelledError` (BaseException), arriving between bytecodes | SIGKILL | May: explicit raises plus resolved callee raises; unresolved or dynamic calls widen to Unknown; BaseException-only classes belong to ambient, not to the May set | Python docs, pydoclint, mypy 11282 |
| TypeScript / JS | engine OOM, `RangeError` on stack overflow (not verified this run) | any thrown value | process signals (Node) | SIGKILL | Unknown: any value can be thrown, `catch` variable is `unknown` under strict; fails? is Unknown too | TS 4.4 notes, issue 13219 |
| Erlang/OTP | process heap limits (not verified this run) | badmatch, function_clause etc. crash the process | exit signals, trappable except `kill` (not verified this run) | node loss reported as an EXIT message | Unknown statically; the design moves recovery to supervisors | Armstrong, OTP docs |

Rows marked "not verified this run" are general knowledge and must not
be cited as findings.

## 4. Evaluation of the owner design

### 4.1 Is "system default plus per-scenario override" the right granularity?

Evidence on granularity: OTP declares policy per supervision subtree
(F8), Kubernetes per pod (F10), Midori per process (F6), crash-only per
component (F9), Gray per process pair (F7). None declares per call site,
and the per-signature alternative (checked exceptions) decayed into
`throws Exception` (F15, F17). The JLS itself exempts Error for exactly
the noise reason (F1). So "one declaration high up, inherited" matches
practice.

Two refinements:
- The isolation unit in grmb is the NODE (an impl is `in node N`, 6.4).
  Ambient faults kill processes, and a process hosts steps from many
  scenarios. "Who recovers, with what strategy and intensity" belongs to
  the node or system (containment); "what this scenario does when it
  loses a step" belongs to the scenario (reaction). The owner's override
  per scenario is the reaction half; the containment half should attach
  to the system with an optional node override. Without the split, two
  scenarios sharing a node could declare incompatible restart behaviour
  for the same process.
- Scenario granularity is too coarse for one fact: idempotency. A
  scenario typically mixes idempotent reads with a non-idempotent charge
  (the checkout example). A `retry` inherited by the whole scenario is
  unsafe for the charge (F11, F9). The fix is not per-step policies
  (that reintroduces per-call noise) but a per-step fact (`idempotent`
  on the step or impl, or an idempotency key in its contract) that the
  checker uses to reject or narrow `retry` (rule AMB-RETRY-IDEM).

### 4.2 Which policies the evidence supports

| Policy | Evidence | Preconditions the checker can verify |
|---|---|---|
| escalate (propagate to supervisor / caller) | Armstrong, OTP, Midori abandonment, P0709 fail-fast | an outside party exists to observe it: a supervising node, system or actor (kill is only observable from outside, F2) |
| restart (crash the step's process, rerun from the step) | crash-only, microreboot, Kubernetes, OTP | bounded (max N within T) with an `else escalate`; the node's durable state is in a declared store (Candea) |
| retry (re-issue the step) | Gray (131/132 Heisenbugs), AWS, SRE | step idempotent; bounded; single layer (no retry at both includer and included scenario, nor ambient retry wrapping a domain `retry` of the same step) |
| terminate (fail fast, end the scenario with an ambient error) | Word OOM rollout, P0709, Midori | none; it is the safe default |

Not supported: "handle in place and continue" for exhaustion, defects
or kill (F4, F6, F2). The grammar should not offer it. A domain-level
degradation (serve stale data) is a domain outcome and belongs in the
step's outcome type, not in the ambient policy.

### 4.3 Which ambient classes belong in the language

Four classes, closed and owned by grimble (not by authors), from F2:
`exhausted`, `defect`, `interrupted`, `killed`. One policy may cover all
four (the common case, one line); a system may split them, for example
`interrupted -> drain` vs `exhausted, defect, killed -> restart max 3
else escalate`. Mapping per language comes from the table in section 3;
the per-language adapter decides which raised types are ambient (Python
BaseException-only classes, Java Error, .NET OOM/StackOverflow, Rust
panic and alloc failure, Go fatal errors), and those types must never
enter an outcome map (A1).

Contradiction with the brief worth stating: RecursionError in Python is
an Exception subclass and Zig's OutOfMemory is an ordinary error value.
In those cases the language lets a step handle exhaustion as a domain
outcome. The rule should therefore be "an outcome map may map a
language's ordinary error that represents exhaustion to a domain variant
only when the step declares it" (Zig style, Torvalds' kernel stance), not
"exhaustion is always ambient". Systems where OOM must be handled
(embedded, kernel) declare it in the outcome; everyone else inherits the
ambient policy.

### 4.4 Treating the ambient class as an outcome arm

Adopt, with the separation in A1. Exhaustiveness is satisfied by
inheritance, so a scenario never writes an ambient arm unless it
overrides; the property "no scenario silently ignores ambient faults"
holds by construction because there is no policy value meaning "ignore".
Differences from ordinary arms that the spec must state:
- a `_` domain arm never matches an ambient class (else `_` becomes the
  over-catch of F13);
- an ambient arm never collects or propagates into `fails with` sets as
  a domain variant; it travels its own path (escalation) up the include
  graph or the node hierarchy;
- adding an ambient class is a grimble language change (edition), not a
  design change, so MDL028's "wildcard hides a later variant" concern
  does not apply to the inherited arm.

### 4.5 What it costs authors

- Declaration noise: one policy line per system, optional node and
  scenario overrides. Compare Java: a `throws` per signature, which
  produced `throws Exception` and empty catches (F15, F17). Midori's
  ratio (single-mode throws 10:1 over typed; 90%+ of functions cannot
  throw) suggests overrides will be rare.
- Idempotency facts: one attribute per non-idempotent step (or per
  idempotent step, depending on the default chosen). This is the main
  new burden and it is the one with the strongest evidence (AWS, Candea).
- Verification noise: the ambient policy needs evidence too (F13: 58% of
  catastrophic failures reachable by testing handlers; F14: recovery
  code is buggy). Requiring a per-scenario ambient test would be heavy;
  one fault-injection test per policy declaration (system or node), as
  an Advisory obligation in the PLAN005 family, is proportional.
- Risk of the uniform default: Cloudflare (F12) shows a uniform
  crash-and-restart on a deterministic input amplifies to a global
  outage. The bounded-restart-then-escalate rule and the "domain error
  turned into a defect" rule (AMB-DOMAIN-PANIC) address it.

### 4.6 The ~589WNWE error-flow facts

- "Rust Exact" is right for concrete closed enums and wrong for
  `Box<dyn Error>`, `anyhow::Error` (Unknown) and foreign
  `#[non_exhaustive]` enums (Exact-known variants plus an open
  remainder: the Unresolved path must fire for the remainder unless the
  outcome map has an explicit "other" arm). Panics are not in the set
  and belong to the ambient class.
- "Python May" is right; the reason string should name widening causes
  (unresolved call, dynamic attribute, C extension), mirroring D121's
  effects `hi`. BaseException-only classes are ambient and excluded.
- "TS Unknown" is right, and even fails? is Unknown.
- Add rows the ticket lacks: Java checked = Exact upper bound
  (compiler-checked), unchecked = May; C# May; Go Unknown with sentinel
  May; Swift typed Exact, untyped fails?-Exact set-Unknown; Zig Exact;
  C++ noexcept as an unverified claim (treat like a D121 claim: answers
  relying on it are conditional).
- Surfacing non-exact sets through opaque-cone Unresolved (no new
  severity) and resolving them with an outcome map as a conditional claim
  matches D121 and the evidence that typed sets work only where closed
  (F18, F19). Adopt.
- Per-arm tests: supported by F13 (simple handler tests prevent most
  catastrophic failures) and F16 (handlers are the least-covered code).
  The planning layer already has `verified_by SEL for STEP.VARIANT` and
  the `uncovered_arm` obligation; the outcome map arm should reuse it.
  WIT-style exception-precondition extraction (F20) is a future source
  of suggested test inputs per arm.

## 5. Implications for grmb (ADOPT / ADAPT / REJECT)

| # | Implication | Tag | Reason |
|---|---|---|---|
| I1 | One ambient policy per system, inherited by every scenario, overridable per scenario | ADOPT | matches OTP, Kubernetes, Midori granularity; avoids checked-exception noise (F8, F10, F17) |
| I2 | Split containment (system or node: strategy, intensity, supervisor) from reaction (scenario: what the scenario does on a lost step) | ADAPT | isolation unit is the process/node, not the scenario (F6, F8, F9) |
| I3 | Closed ambient class set `exhausted`, `defect`, `interrupted`, `killed`, owned by grimble, one policy may cover all | ADAPT | four behaviourally different classes across runtimes (F2) |
| I4 | Policy vocabulary {escalate, restart max N within T else ..., retry max N else ..., terminate}; no "ignore/continue" | ADOPT | convergent practice; local recovery from exhaustion fails (F4, F7-F11) |
| I5 | Ambient arms never matched by `_`, never fed from or into domain variants, never in outcome maps | ADOPT | over-catch is a top catastrophic pattern (F13) and every language separates the classes (F1) |
| I6 | Per-step idempotency fact; `retry` over a non-idempotent step fires | ADOPT | AWS, crash-only (F9, F11) |
| I7 | Bounded restart/retry with mandatory escalation tail; single retry layer | ADOPT | OTP intensity, k8s back-off, SRE 4^3, Gray Bohrbug test (F7, F8, F10, F11) |
| I8 | Exhaustion that the language reports as an ordinary error (Zig OutOfMemory, Python RecursionError) may be declared as a domain variant | ADAPT | kernel and embedded need it (F5); default remains ambient |
| I9 | One fault-injection `verified_by` per policy declaration, Advisory | ADOPT | F13, F14; keeps verification noise proportional |
| I10 | A separate pedantic profile for ambient faults | REJECT | owner decision; also unnecessary because inheritance removes the noise that motivated it |
| I11 | Per-call-site or per-step ambient declarations | REJECT | the Java experience (F15, F17) and JLS's own rationale (F1) |
| I12 | ~589WNWE lattice with corrected Rust row, added Java/C#/Go/Swift/Zig/C++ rows, reason strings naming widening causes | ADAPT | F18, F20-F22 |
| I13 | Outcome maps as D121 conditional claims, resolved through opaque-cone Unresolved, verified per arm via existing `for STEP.VARIANT` | ADOPT | F16, F19 and existing design |
| I14 | Treat C++ `noexcept` and similar unchecked "cannot fail" annotations as claims, not facts | ADOPT | cppreference: not a compile-time check (F3) |

## 6. Candidate rules

Ids are placeholders (AMBxxx, ERRxxx). Polarity: presence, absence or
mismatch. All are over the planning model or the model-code binding.

| Id | Anti-pattern prevented | Predicate | Polarity | Severity (proposed) | Source |
|---|---|---|---|---|---|
| AMB001 AMB-POLICY-MISSING | ambient faults silently out of scope | a `system` with no ambient policy declaration | absence | Error (quick-fix inserts `terminate`) | owner design; P0709 fail-fast default |
| AMB002 AMB-RETRY-IDEM | duplicate side effects on retry | effective ambient policy of scenario s for class c is `retry`, and some step use (st, s) has st not idempotent | mismatch | Error | AWS idempotent APIs; Candea and Fox |
| AMB003 AMB-UNBOUNDED | restart storms, crash loops | a `restart` or `retry` policy without `max` (and window for restart), or without an escalation tail | absence | Error | OTP intensity; Kubernetes back-off; Gray |
| AMB004 AMB-RETRY-AMPLIFY | retry amplification across layers | an ambient `retry` on scenario s and on a scenario s' with s includes s' (transitively), or an ambient `retry` on s while a domain `retry` targets the same step; report the product of max counts | presence | Warn | Google SRE ch. 22; AWS retries |
| AMB005 AMB-OVERCATCH | over-catch turning bugs and exhaustion into domain outcomes, or aborting a cluster on a domain error | an outcome-map arm whose source is an ambient type or a language root catch-all (Throwable, BaseException, `catch (...)`, `catch (Exception)` when the set is not Exact, Go `recover`) | presence | Error | Yuan OSDI 2014 (over-catch 8%); ruff BLE001; CA1031 |
| AMB006 AMB-ESCALATE-NOWHERE | let-it-crash with nobody to restart | effective policy `escalate` or `restart` where the node or system has no supervising owner declared (no outer system, no node supervisor) | absence | Error, Unresolved if node unknown | Armstrong; OTP; kill observable only externally |
| AMB007 AMB-DOMAIN-PANIC | domain errors converted to defects (Cloudflare) | a step declares variant v mapped from error E, and the bound unit converts E to a panic (Rust `unwrap`/`expect` on that Result, detected via clippy `unwrap_in_result`-style query) | mismatch | Warn | Cloudflare 2025-11-18; Rust book ch. 9.3 |
| AMB008 AMB-POLICY-UNVERIFIED | untested recovery path | an ambient policy declaration (system or node) with no `verified_by`, or evidence resolving empty | absence | Advisory (obligation family `unverified`) | Yuan (58% testable); Gao FSE 2018; CrashTuner; P0709 babb |
| AMB009 AMB-RESTART-STATEFUL | restart losing state | `restart` policy on a node whose impls write state with no declared store or flow to a store entity | absence | Advisory | Candea and Fox (state in dedicated stores) |
| ERR001 ERR-OPEN-SET | handling an error set nobody knows | step use bound to a unit whose error facts are May or Unknown and no outcome map | presence | Unresolved via opaque-cone (no new severity) | ~589WNWE; F18-F21 |
| ERR002 ERR-MAP-MISSING-ARM | new error type not designed for | the unit's Exact error set contains E with no outcome-map arm | mismatch | Error (MDL022 analogue) | Zig/Rust exhaustiveness; Sutter P0709 on closed sets |
| ERR003 ERR-MAP-DEAD-ARM | stale mapping | an outcome-map arm whose source E is not in the unit's Exact set, or not in `hi` of a May set | mismatch | Warn (MDL025 analogue); Unresolved when the set is Unknown | Robillard and Murphy (exception structure evolves) |
| ERR004 ERR-MAP-UNTESTED | arm never exercised | an outcome-map arm (v <- E) with no `verified_by ... for STEP.v` evidence | absence | Advisory (`uncovered_arm`) | Lima et al. 2021; Hora and Fraser 2026; Yuan |
| ERR005 ERR-OPEN-REMAINDER | foreign `#[non_exhaustive]` or open sets treated as closed | outcome map over a set marked open (non_exhaustive, `anyerror`, `any Error`, `error`) with no explicit `other` arm | absence | Error | Rust reference; Swift SE-0413; Zig |
| ERR006 ERR-NOFAIL-CLAIM | trusting unchecked "cannot fail" | a step with outcome `{ ok }` bound to a unit whose fails? is Unknown, or that relies on `noexcept`/no-panic claims; answer conditional `assumed:<claim>` | presence | conditional (clean in CI, Unresolved at release, D121) | cppreference noexcept; no-panic caveats; D121 |

## 7. Bibliography

Credibility line per source: venue; authors' practical standing.

Empirical and research papers

1. Yuan, D., Luo, Y., Zhuang, X., Rodrigues, G. R., Zhao, X., Zhang, Y.,
   Jain, P. U., Stumm, M. "Simple Testing Can Prevent Most Critical
   Failures: An Analysis of Production Failures in Distributed
   Data-Intensive Systems." OSDI 2014, pp. 249-265.
   https://www.usenix.org/conference/osdi14/technical-sessions/presentation/yuan
   Credibility: OSDI (top systems venue), full text read; University of
   Toronto; systems studied are production Apache/Redis deployments.
2. Chen, H., Dou, W., Jiang, Y., Qin, F. "Understanding Exception-Related
   Bugs in Large-Scale Cloud Systems." ASE 2019. doi:10.1109/ASE.2019.00040.
   Credibility: ASE; abstract read; academic, real bug trackers.
3. Gao, Y., Dou, W., Qin, F., et al. "An Empirical Study on Crash
   Recovery Bugs in Large-Scale Distributed Systems." ESEC/FSE 2018.
   doi:10.1145/3236024.3236030. Credibility: FSE; abstract only.
4. Lu, J., Liu, C., Li, L., Feng, X., Tan, F., Yang, J. "CrashTuner:
   Detecting Crash-Recovery Bugs in Cloud Systems via Meta-Info
   Analysis." SOSP 2019. doi:10.1145/3341301.3359645. Credibility: SOSP;
   abstract read.
5. Gunawi, H. S., et al. "What Bugs Live in the Cloud?" SoCC 2014.
   doi:10.1145/2670979.2670986; "Why Does the Cloud Stop Computing?"
   SoCC 2016. doi:10.1145/2987550.2987583. Credibility: SoCC; abstracts
   read; background only.
6. Weimer, W., Necula, G. C. "Finding and Preventing Run-Time Error
   Handling Mistakes." OOPSLA 2004. doi:10.1145/1028976.1029011;
   "Exceptional Situations and Program Reliability." TOPLAS 30(2), 2008.
   doi:10.1145/1330017.1330019. Credibility: OOPSLA/TOPLAS; abstracts
   read; academic (Berkeley), 5 MLOC of real Java.
7. Robillard, M. P., Murphy, G. C. "Static Analysis to Support the
   Evolution of Exception Structure in Object-Oriented Systems." TOSEM
   12(2), 2003. doi:10.1145/941566.941569. Credibility: TOSEM; abstract.
8. Fu, C., Ryder, B. G. "Exception-Chain Analysis: Revealing Exception
   Handling Architecture in Java Server Applications." ICSE 2007.
   doi:10.1109/ICSE.2007.35. Credibility: ICSE; abstract; Tomcat case.
9. Leroy, X., Pessaux, F. "Type-Based Analysis of Uncaught Exceptions."
   TOPLAS 22(2), 2000. doi:10.1145/349214.349230. Credibility: TOPLAS;
   Leroy leads OCaml (INRIA).
10. Kery, M. B., Le Goues, C., Myers, B. A. "Examining Programmer
    Practices for Locally Handling Exceptions." MSR 2016.
    doi:10.1145/2901739.2903497. Credibility: MSR; CMU; abstract.
11. Nakshatri, S., Hegde, M., Thandra, S. "Analysis of Exception Handling
    Patterns in Java Projects." MSR 2016 (mining challenge).
    doi:10.1145/2901739.2903499. Credibility: MSR challenge track;
    student authors; weak-medium.
12. Ebert, F., Castor, F. "A Study on Developers' Perceptions about
    Exception Handling Bugs." ICSM 2013. doi:10.1109/ICSM.2013.69;
    Ebert, F., Castor, F., Serebrenik, A. "An Exploratory Study on
    Exception Handling Bugs in Java Programs." JSS 106, 2015.
    doi:10.1016/j.jss.2015.04.066 (abstract not retrievable; metadata
    and secondary summary only); reflection paper SANER 2020,
    doi:10.1109/SANER48275.2020.9054791. Credibility: ICSM/JSS/SANER;
    survey of 154 developers plus Eclipse and Tomcat bugs.
13. de Padua, G. B., Shang, W. "Studying the Prevalence of Exception
    Handling Anti-Patterns." ICPC 2017. doi:10.1109/ICPC.2017.1;
    "Revisiting Exception Handling Practices with Exception Flow
    Analysis." SCAM 2017. doi:10.1109/SCAM.2017.16 (arXiv 1708.00817);
    "Studying the Relationship between Exception Handling Practices and
    Post-Release Defects." MSR 2018. doi:10.1145/3196398.3196435.
    Credibility: ICPC/SCAM/MSR; abstracts; 16 Java and C# projects.
14. Cacho, N., et al. "How Does Exception Handling Behavior Evolve? An
    Exploratory Study in Java and C# Applications." ICSME 2014.
    doi:10.1109/ICSME.2014.25. Credibility: ICSME; abstract (background).
15. Coelho, R., Almeida, L., Gousios, G., van Deursen, A., Treude, C.
    "Exception Handling Bug Hazards in Android." EMSE 2016.
    doi:10.1007/s10664-016-9443-7. Credibility: EMSE; metadata only
    [abstract not read].
16. Cassee, N., Pinto, G., Castor, F., Serebrenik, A. "How Swift
    Developers Handle Errors." MSR 2018. doi:10.1145/3196398.3196428.
    Credibility: MSR; abstract plus conference page.
17. Shah, H. B., Gorg, C., Harrold, M. J. "Why Do Developers Neglect
    Exception Handling?" WEH 2008. doi:10.1145/1454268.1454277.
    Credibility: workshop; abstract; background.
18. Marcilio, D., Furia, C. A. "What Is Thrown? Lightweight Precise
    Automatic Extraction of Exception Preconditions in Java Methods."
    ICSME 2022. doi:10.1109/ICSME55016.2022.00038. Credibility: ICSME;
    abstract; 46 projects.
19. Lima, L. P., Rocha, L. S., Bezerra, C. I. M., Paixao, M. "Assessing
    Exception Handling Testing Practices in Open-Source Libraries."
    arXiv 2105.00500, 2021. Credibility: preprint (EMSE version not
    verified); 27 Java libraries.
20. Hora, A., Fraser, G. "Exceptional Behaviors: How Frequently Are They
    Tested?" arXiv 2602.05123, 2026. Credibility: preprint; Fraser
    (Passau, EvoSuite author); 25 Python systems.
21. Qin, B., Chen, Y., Yu, Z., Song, L., Zhang, Y. "Understanding Memory
    and Thread Safety Practices and Issues in Real-World Rust Programs."
    PLDI 2020. doi:10.1145/3385412.3386036; Qin, B., et al.
    "Understanding and Detecting Real-World Safety Issues in Rust." TSE
    2024. doi:10.1109/TSE.2024.3380393. Credibility: PLDI/TSE; abstracts.
22. Ni, Y., Feng, Y., Liu, Z., Chen, R., Xu, B. "PanicFI: An
    Infrastructure for Fixing Panic Bugs in Real-World Rust Programs."
    arXiv 2408.03262, 2024. Credibility: preprint; abstract.
23. Monat, R., Ouadjaout, A., Mine, A. "A Multilanguage Static Analysis
    of Python Programs with Native C Extensions." SAS 2021.
    https://www-apr.lip6.fr/~mine/publi/article-monat-al-sas21.pdf ;
    Monat PhD thesis, Sorbonne Universite 2021. Credibility: SAS;
    located via search, not read beyond summaries [partially verified].
24. Marlow, S., Peyton Jones, S., Moran, A., Reppy, J. "Asynchronous
    Exceptions in Haskell." PLDI 2001. doi:10.1145/378795.378858.
    Credibility: PLDI; metadata only, not read.
25. Candea, G., Fox, A. "Crash-Only Software." HotOS IX, 2003.
    https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea_html/
    Credibility: HotOS; HTML read; Stanford recovery-oriented computing
    group (with Berkeley ROC).
26. Gray, J. "Why Do Computers Stop and What Can Be Done About It?"
    Tandem Technical Report 85.7, 1985.
    https://www.cs.columbia.edu/~junfeng/08fa-e6998/sched/readings/why-do-computers-stop.pdf
    Credibility: industrial technical report, full text read; Gray
    (Tandem, later Turing Award) measured Tandem customer systems.
27. Armstrong, J. "Making Reliable Distributed Systems in the Presence of
    Software Errors." PhD thesis, KTH, 2003.
    https://erlang.org/download/armstrong_thesis_2003.pdf
    Credibility: thesis, full text grepped; Armstrong co-created Erlang
    at Ericsson (AXD301 case study in the thesis).

Standards, vendor and language documentation

28. Gosling, J., et al. The Java Language Specification, Java SE 21
    Edition, chapter 11. https://docs.oracle.com/javase/specs/jls/se21/html/jls-11.html ;
    java.lang.Error javadoc. Credibility: language specification.
29. Python Software Foundation. Built-in Exceptions; signal; asyncio
    Exceptions. https://docs.python.org/3/library/exceptions.html ,
    https://docs.python.org/3/library/signal.html ,
    https://docs.python.org/3/library/asyncio-exceptions.html .
    Credibility: official docs.
30. The Rust Programming Language, ch. 9.3 "To panic! or Not to panic!"
    https://doc.rust-lang.org/book/ch09-03-to-panic-or-not-to-panic.html ;
    std::panic::catch_unwind, std::alloc::handle_alloc_error, std unix
    stack_overflow.rs; Rust Reference, `non_exhaustive`.
    Credibility: official docs and source.
31. Rust Clippy lint list. https://rust-lang.github.io/rust-clippy/master/index.html
    (lint names and groups grepped). dtolnay, no-panic crate.
    https://docs.rs/no-panic (via search summary). anyhow crate docs
    https://docs.rs/anyhow . Credibility: official tool docs; dtolnay is
    the maintainer of serde, syn and anyhow.
32. Zig 0.15.1 Language Reference. https://ziglang.org/documentation/0.15.1/
    Credibility: official.
33. Revuelta, J., Lehmann, T., Gregor, D. SE-0413 "Typed throws."
    https://github.com/swiftlang/swift-evolution/blob/main/proposals/0413-typed-throws.md .
    Credibility: accepted Swift Evolution proposal; Gregor is a Swift
    core team member at Apple.
34. McCall, J. "Error Handling Rationale and Proposal." Swift repository
    docs, first committed 2015-04-23 (author per git history).
    https://github.com/swiftlang/swift/blob/main/docs/ErrorHandlingRationale.md .
    Credibility: design rationale by an Apple Swift compiler engineer.
35. Gerrand, A. "Defer, Panic, and Recover." The Go Blog, 2010-08-04.
    https://go.dev/blog/defer-panic-and-recover ; Go FAQ
    https://go.dev/doc/faq ; runtime/debug https://pkg.go.dev/runtime/debug .
    Credibility: official Go team.
36. Ericsson. OTP Design Principles: Supervisor Behaviour.
    https://www.erlang.org/doc/system/sup_princ.html . Credibility: official.
37. Microsoft. StackOverflowException; OutOfMemoryException; CA1031.
    https://learn.microsoft.com/en-us/dotnet/api/system.stackoverflowexception ,
    https://learn.microsoft.com/en-us/dotnet/api/system.outofmemoryexception ,
    https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca1031 .
    Credibility: official.
38. cppreference. "noexcept specifier."
    https://en.cppreference.com/w/cpp/language/noexcept_spec .
    Credibility: community-maintained reference widely used by WG21
    members; checked against the standard's wording only indirectly.
39. Sutter, H. "Zero-overhead deterministic exceptions: Throwing values."
    WG21 P0709R4, 2019. https://www.open-std.org/JTC1/SC22/wg21/docs/papers/2019/p0709r4.pdf .
    Credibility: ISO C++ committee paper, full text read; Sutter convened
    WG21 and worked 22 years at Microsoft (left 2024 per search).
40. Krzemienski, A., Kaminski, T. P1404R1 "bad_alloc is not
    out-of-memory." https://open-std.org/JTC1/SC22/WG21/docs/papers/2019/p1404r1.html .
    Credibility: WG21 paper; located via search summary.
41. Linux kernel documentation. "Overcommit Accounting."
    https://www.kernel.org/doc/html/latest/mm/overcommit-accounting.html .
    Credibility: official.
42. Kubernetes documentation. "Pod Lifecycle."
    https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/ .
    Credibility: official (CNCF).
43. TypeScript 4.4 release notes (useUnknownInCatchVariables).
    https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-4.html ;
    microsoft/TypeScript issue 13219.
    https://github.com/microsoft/TypeScript/issues/13219 .
    Credibility: official.
44. python/mypy issue 11282. https://github.com/python/mypy/issues/11282 ;
    pydoclint violation codes https://jsh9.github.io/pydoclint/violation_codes.html ;
    ruff BLE001 https://docs.astral.sh/ruff/rules/blind-except/ .
    Credibility: official tool docs and maintainer statements.
45. Kotlin documentation, Exceptions. https://kotlinlang.org/docs/exceptions.html .
    Credibility: official.

Practitioner experience reports

46. Venners, B., Eckel, B. "The Trouble with Checked Exceptions: A
    Conversation with Anders Hejlsberg, Part II." Artima, 2003-08-18.
    https://www.artima.com/articles/the-trouble-with-checked-exceptions .
    Credibility: interview; Hejlsberg is lead architect of C# and
    TypeScript at Microsoft.
47. Duffy, J. "The Error Model." 2016-02-07.
    https://joeduffyblog.com/2016/02/07/the-error-model/ ; "Blogging
    about Midori." 2015-11-03. Credibility: named practitioner blog; Duffy
    "led the groups focusing on the developer experience" of Midori at
    Microsoft 2009-2014 (own account); later Pulumi CEO.
48. Featonby, M. "Making retries safe with idempotent APIs." Amazon
    Builders' Library.
    https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/ .
    Credibility: AWS Principal Engineer (EC2, containers).
49. "Timeouts, retries and backoff with jitter." Amazon Builders'
    Library, now at https://builder.aws.com/content/3EumjoZascWd1oZiEgL8ORlv3qE/timeouts-retries-and-backoff-with-jitter .
    Credibility: AWS; the fetched page names the author only as "Marc"
    with a 2026 date (the article is a re-hosting; original author
    attribution [unverified] this run).
50. Ulrich, M. "Addressing Cascading Failures." In Site Reliability
    Engineering (Google, O'Reilly 2016), ch. 22.
    https://sre.google/sre-book/addressing-cascading-failures/ .
    Credibility: Google SRE.
51. Prince, M. "Cloudflare outage on November 18, 2025." Cloudflare blog.
    https://blog.cloudflare.com/18-november-2025-outage/ . Credibility:
    first-party postmortem by Cloudflare's CEO.
52. Torvalds, L., Ojeda, M., Triplett, J. LKML thread "[PATCH 00/13]
    [RFC] Rust support", April 2021.
    https://lkml.iu.edu/hypermail/linux/kernel/2104.1/09079.html (and
    siblings). Credibility: Linux maintainers; quotes via search summary
    of the archive [partially verified].
