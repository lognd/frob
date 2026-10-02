# Neatness: a NEAT rule family over the universal structural model

Status: RESEARCH NOTE for the frob v2 design (T-0001 line of work), for owner review. Written
2026-10-02. Feeds docs/design/rules.md section 3 (a new family `NEAT`) and universal-model.md
sections 4.4 (effects capability) and 5 (query surface). ASCII only.

## 0. Honest status line

- Web access WAS available this session (curl, yt-dlp, youtube-transcript-api). Every item
  tagged `[verify]` below is from memory or a secondary source and was not re-read.
- Denominator for the primary source (Logan Smith, YouTube handle @_noisecode, channel name
  "Logan Smith", channel id UCnHX5FjwtQpxkCGziuh4NJA): 13 videos, enumerated with
  `yt-dlp --flat-playlist` on 2026-10-02 and cross-checked against the channel RSS feed.
  13 of 13 English transcripts obtained (auto-captions; mis-hearings exist, e.g. "arrest" for
  "Rust"), 13 of 13 read. Two caveats: for "Comprehending Proc Macros" the first ~40% was read
  in full and the implementation half was scanned for advice sentences only; transcripts are
  kept in the session scratchpad, NOT in the repo.
- One-hop references (people/talks/books he cites): 17 distinct works enumerated, status per
  source in Appendix B. Read in primary form: Van Eerd (CppNow 2023 transcript, full), Parent
  "C++ Seasoning" (transcript, about the first fifth plus targeted extracts of goals 2 and 3), Parent
  "Better Code: Runtime Polymorphism" (first third), R. Martin SRP post (full), Verse book
  effects chapter (full). Cited but UNREAD (marked `[unread]`): Hickey "Simple Made Easy",
  Meyers non-member article, Normand "Grokking Simplicity", Parnas 1972, matklad io::Error
  study, Hinnant move paper, C++ Core Guidelines entries, Beck "Tidy First", Dijkstra EWD215,
  Bernhardt "Boundaries" talk (only the screencast blurb), Ousterhout book (only the site).
- Linter rule ids were machine-verified against upstream sources where marked "(v)":
  clippy via clippy_lints/src/declared_lints.rs plus group extraction from each lint file;
  ruff via crates/ruff_linter/src/codes.rs; clang-tidy via the published checks list;
  revive via its rule/ directory; checkstyle via its checks/ tree; PMD via category/java/design.xml;
  eslint-plugin-functional via its README table; ESLint core via docs HTTP 200. Stable versus
  preview status for ruff rules was NOT recoverable from codes.rs and is tagged `[verify]`.
- Nothing here ran cargo or frob. No code was written. The first-ten list is in section 8.

## 1. How to read the catalogue

Vocabulary borrowed from universal-model.md (U) and lint-requirements.md (Qnn numbers):

- unit(kind=function|method|constructor|closure), body(u) = the `group(order=sequence)` under it,
  stmts(u) = its direct children in order. params(u) = Q15 (with `mode`, `type_text`,
  `default`). control(u) = Q16 (loops, branch_arms, max_nesting, cyclomatic, returns, lines).
- Roles on group/apply/bind come from the adapter morphism (2.4): loop, branch, return,
  assign, call, closure, guard. A rule needing a role the adapter did not map is
  Unresolved for that language, never clean (fidelity F3/F4, 3.3).
- comments(a) = Q10 with `enclosing`/`following`; attributes(u) = Q08; resolve = Q20
  (Must/May/Unknown); edges/closure/reaches = Q28/Q30; effects(u) = Q34 (Bounds of EffectSite
  atoms); entrypoints = Q37; callee_vocab = Q47 (empty vocabulary is NotApplicable);
  type_of/dispatch_targets = Q25 (tier 3, optional).
- Polarity: P+ fires on lo, certifies clean only if hi contains no offender; P- fires only if
  hi lacks the required thing; Pn threshold, evaluated on Exact only; Pc closure, Exact only;
  P0 equality. Subject accounting: zero examined subjects is Unresolved.
- Exactness classes used in each rule: S = structural (Theorem 2, exact on the closed
  fragment); C = needs a capability (names it); A = needs an annotation to be computable;
  J = judgment, not lintable (section 9).
- Binding policy (the owner's "bind the tool where it is better"): BIND = frob reads the
  tool's finding as a TOOL side input and maps it to the NEAT id (no re-implementation);
  NATIVE = frob implements on U because no tool covers it or the tool is language-bound;
  HYBRID = native universal predicate, tool finding raises confidence. If the bound tool is not
  installed or did not run, the rule is Unresolved for that language, never clean.
- Config: a `[neat]` table in frob.toml; thresholds are the "knobs". Whether they are
  `enforcement` fields (materialized by `frob init`, CFG001 on absence; architecture.md 6) is
  open question 1; this note proposes materializing only `neat.profile` and the thresholds of
  the first ten.

## 2. Primary sources and their checkable claims

Claim tags: LS-xx-n (Logan Smith, video code xx, claim n), TVE (Van Eerd), SP (Parent), RM
(Martin). Class: S/C/A/J as defined above, L = already enforced by a named linter.

### 2.1 Logan Smith (@_noisecode): the whole channel, video by video

Style of the channel: Rust and C++ language-design deep dives; rules appear as strong
opinions, mostly about invariants in types. Index with dates and the rules extracted per video
is Appendix A; this section gives the checkable claims.

#### 2.1.1 "How to write the perfect function" (2026-08-20), tag PF

Reasons for functions (PF-0): local reasoning, abstraction, testability, reuse; reuse
threshold n=1 (extract proactively; contrast Muratori, section 2.3). Claims:

- PF-1 (A/C) Honest = accesses the outside world only through its signature: never reads or
  writes anything not reachable from its arguments. sort-in-place, vector.clear, remove_if are
  honest; get_time, a getter that reads an asset manager singleton are dishonest. Pure and
  honest differ: honest permits mutation of parameters.
- PF-2 (C) Dishonesty is infectious upward: an honest function must not call a dishonest one;
  honest functions sit at call-tree leaves, dishonest near roots. Checkable as effect
  containment over the callee closure.
- PF-3 (S+C) Inject dishonesty at the top: pass the PRNG, clock, IO in; functional core,
  imperative shell; use for-each callbacks or iterators instead of materializing results.
- PF-4 (S) A function that reads a mutable global (the global PRNG, seeded elsewhere) has no
  local reasoning; make the dependency a parameter.
- PF-5 (S+A) Framework hooks ("backward" functions: update, main) stay as thin as possible and
  jump into right-side-up functions at once.
- PF-6 (S) Long positional parameter lists, especially bool flags ("any guesses what this last
  boolean does?"): use a parameter struct or strong types.
- PF-7 (S) Do not take a whole struct when the body uses two fields ("the wallet and the
  card"); a temporary parameter struct marshalling arguments is fine and different.
- PF-8 (C) Accept the weakest sufficient parameter type (span or iterator over a concrete
  vector); do not demand stronger guarantees than needed, but do ask when truly needed.
- PF-9 (A/J) Encode preconditions in types: NormalizedVec3 (invariant on construction, implicit
  conversion back to Vec3), lock-guard receipts so B cannot be called without the mutex held,
  strong types. Idempotent normalization permits specialization (normalize of a normalized is
  a no-op). He admits the line "where to stop" is a feel.
- PF-10 (S) Golden rule: every line of a body at one level of abstraction; no zooming in and out
  within one function. Equivalent to SRP, Van Eerd's produce-vs-act split, Parent's no raw loops.
- PF-11 (S) Section comments inside a function body are "a dead giveaway" of mixed levels.
- PF-12 (S+vocab) Hand-written to-lower loop and hand-written binary search inside business
  logic are raw loops; use the library algorithm (lower_bound) as a brick.
- PF-13 (S, experimental) Ad hoc data structure maintained across methods (normalize the key, then
  binary search a sorted vector, mirrored in every mutator) becomes a type (case-insensitive map).
- PF-14 (S+vocab) A lookup helper that aborts the whole application on a miss should return a
  richer result instead (callee vocabulary: exit, abort, panic in a non-shell function).
- PF-15 (A) Tooling idea: a test runner could skip re-running tests of local-reasoning
  functions unchanged since the last run, if the language annotates it (Verse does). This is
  exactly frob's touched-set test idea plus an effects annotation (section 4.4).

#### 2.1.2 "Verse: A New Scripting Language? In THIS Economy?" (2026-07-23), tag VS

- VS-1 (A) Effect specifiers on functions: `<computes>` asserts purity and the compiler checks
  the body only calls pure functions; it also licenses CSE and memoization.
- VS-2 (C) Callee effects must be a subset of the caller's: calling a function with fewer
  effects is always allowed (const T* analogy); a no-`<decides>` function behaves like
  `noexcept`, and the compiler enforces it.
- VS-3 (J) "Verse wants the type system for data and the effect system for control flow":
  `<decides>` (failure as an effect) is isomorphic to returning an optional; fallible calls use
  `[]` so they look different from infallible ones.
- VS-4 (S) A function that is a partial function (division) should either encode the failure in
  its signature (optional or decides) or be total; never leave it silent.

#### 2.1.3 "Moves Are Broken" (2025-11-06), tag MB

- MB-1 (J/S) Invariants are the structural unit of reasoning; reduce the number of illegal bit
  patterns a type admits; strong invariants simplify logic and let the compiler optimize.
- MB-2 (S) A parameter that cannot be null should be a reference, not a pointer; check null once
  at the API boundary and pass a non-null type onward (otherwise a linear number of null checks
  in the call hierarchy and broken local reasoning). Rust: `Option<&T>` at the boundary.
- MB-3 (S) Types with cross-field invariants must not rely on compiler-generated moves under the
  rule of zero (a move leaves the source with len != 0 and a null buffer).
- MB-4 (S) A type with a strong invariant should not offer a default constructor (TSharedRef's
  "do not use" constructor is the cautionary tale); prefer `optional<scoped_lock>` to a lock
  with an empty state (unique_lock).
- MB-5 (J) Destructive moves (Rust) compose with strong invariants; non-destructive moves weaken
  them. A language-design claim, not a lint.

#### 2.1.4 "Comprehending Proc Macros" (2025-01-09), tag PM

- PM-1 (S) Architect macros like compilers: model the problem as types first, then parse into
  the IR, then generate code (front end, IR, back end); do not start duct-taping syn and quote.
- PM-2 (S) Keep the proc-macro entry point thin: convert to `proc_macro2` at the edge, do the
  work in ordinary library code (also because the macro crate must be separate and logic outside
  it is testable). This is a framework hook (PF-5) with a name: `#[proc_macro*]`.
- PM-3 (S, language-specific) Generated code must fully qualify paths (`::core::iter::...`) so
  it does not depend on the caller's imports or shadowed names.
- PM-4 (S) Store only the information the IR needs (drop the `for` and `in` keywords after
  parsing); derive Debug on IR during development; gate heavy syn features.

#### 2.1.5 "Constructors Are Broken" (2024-01-19), tag CB

- CB-1 (S) Fallible creation is a named factory function returning an optional/result; no
  exceptions out of constructors in performance-sensitive code.
- CB-2 (S) No two-phase initialization (default constructor plus `init()`): "spaces between the
  lines" where a pointer to a half-built object escapes; the C++ Core Guidelines advise against it.
- CB-3 (S) Keep constructor bodies empty; a non-empty body is "a place for complexity and bugs to
  hide". Set everything up, then build the object in one motion (bundle members into a private
  struct, aggregate-initialize, move in).
- CB-4 (A) An `unchecked` factory that skips validation must be marked unsafe (Rust) or the type's
  invariant is meaningless; a public `create_unchecked` without a safety marker voids the invariant.
- CB-5 (S) Initializer lists cannot share a computed local (strlen twice) and member order is
  declaration order: a symptom that the factory form is better.

#### 2.1.6 "Cursed C++ Casts" (2023-10-19), tag CC

- CC-1 (S) Principle of least power: use the weakest conversion that does the job (an
  `implicit_cast`, then `static_cast`, then `reinterpret_cast`).
- CC-2 (S) Never use a C-style cast: it silently falls through const_cast, static_cast (incl.
  private base), reinterpret_cast, and changes meaning when a refactor breaks an inheritance edge.
- CC-3 (S) Type-pun with `bit_cast`/memcpy, not union or pointer reinterpretation (UB).
- CC-4 (S) Never access private members through template-instantiation tricks (public_cast).

#### 2.1.7 "Two Ways To Do Dynamic Dispatch" (2023-09-28), tag DD

- DD-1 (J) Polymorphism is a property of use, not of the type: non-intrusive wide pointers
  (Rust trait objects, type erasure) versus intrusive vptr in every instance (inheritance).
  (Sean Parent's "there are no polymorphic types, only polymorphic use of similar types".)
- DD-2 (S, C++) A class with a virtual function that is deleted polymorphically needs a virtual
  destructor; delete the copy operations of polymorphic types.
- DD-3 (J) Choose by error path: a cold error path may prefer the thin-pointer intrusive form
  (anyhow) over a wide `Box<dyn Error>`.

#### 2.1.8 "5 Strong Opinions On Everyday Rust" (2023-08-31), tag SO

- SO-1 (J) Semicolon after a unit-returning tail call encodes intent ("I return what A returns" vs
  "I return unit regardless"); "it depends but think about it".
- SO-2 (L) Never glob-import enum variants to write unqualified match arms: removing a variant turns
  the arm into a catch-all binding and the compiler stops guiding you. Alias the type instead.
  clippy::enum_glob_use (pedantic) and clippy::wildcard_enum_match_arm (restriction) (v).
- SO-3 (L) Never `&Option<T>`, `&Vec<T>`, `&String`, `&Box<T>` in APIs: use `Option<&T>`, `&[T]`,
  `&str`, `&T`. clippy::ref_option (pedantic), ptr_arg (style), borrowed_box (complexity) (v).
- SO-4 (S) Do not return `impl Into<T>` / `impl IntoIterator` or any trait with one consuming
  method (the caller can only call it); do accept them as parameters; use the inner-function
  trick to avoid monomorphization bloat. No clippy lint found `[verify]`.
- SO-5 (L) `unsafe fn` bodies must still wrap unsafe operations in `unsafe {}`; keep unsafe
  blocks minimal: rustc `unsafe_op_in_unsafe_fn`, clippy multiple_unsafe_ops_per_block and
  undocumented_unsafe_blocks (restriction) (v).

#### 2.1.9 "The Dark Side of .reserve()" (2023-08-17), tag RS

- RS-1 (S+vocab) In a public API, never call `reserve`/`reserve_exact` (C++ `vector::reserve`,
  Rust `Vec::reserve_exact`, Unreal `TArray::Reserve`) on a container you received by reference
  or through `self`: it defeats geometric growth and makes a caller's loop quadratic. Fine on
  local vectors and private APIs; never in a loop. Rust's plain `Vec::reserve` is amortized-safe.
- RS-2 (S) For bulk append use the bulk API (`extend`, `insert(end, range)`), not reserve plus a
  loop. Also: accept a span/iterator rather than a heap array to avoid forcing allocation.

#### 2.1.10 "A Simpler Way to See Results" (2023-07-27), tag RE

- RE-1 (S) Option when there is exactly one self-evident failure reason; Result when there is
  more than one. A function that returns None along multiple separate paths probably wants a
  Result. Return more information than less; the caller can discard it.
- RE-2 (S) Prefer `?` to nested map/and_then combinator chains.
- RE-3 (S, library) Model errors as an enum with a variant per failure mode (thiserror for
  libraries, anyhow acceptable in applications), implement `std::error::Error` proactively, and
  use `Infallible` as the error type when a trait forces Result but the code cannot fail.
- RE-4 (L) `Result` is must_use; `Result<T, ()>` is legitimate but is flagged by
  clippy::result_unit_err on public functions (style) (v).

#### 2.1.11 "Rust Functions Are Weird (But Be Glad)" (2023-07-13), tag FW

- FW-1 (J/perf) Each fn item and closure has a unique zero-sized type, so generic higher-order
  code inlines; `fn` pointers and `dyn Fn` force indirect calls. In C++, wrap a function in a
  lambda before passing it to a hot template. Monomorphization has a code-size cost.
- FW-2 (J) `std::any` tools are for getting out of a jam, not for anchoring a design.

#### 2.1.12 "Choose the Right Option" (2023-06-29), tag OP

- OP-1 (L) Never `&Option<T>` as a parameter or return type; `Option<&T>` hides storage, is easier
  at call sites (no as_ref), survives representation change (Option<T> to Option<Box<T>> breaks
  `&Option<T>` signatures), and allows filtering. `&mut Option<T>` can be legitimate (caller may
  set None). If you need ownership, take `Option<T>` by value. clippy::ref_option (v).

#### 2.1.13 "Use Arc Instead of Vec" (2023-06-13), tag AR

- AR-1 (S+C) Long-lived immutable sequences and strings: `Arc<[T]>`/`Arc<str>` (or `Rc`, or `Box<str>`
  when never cloned), not `Vec`/`String`; never `Arc<String>` (double indirection); hash-map keys
  should be immutable types. clippy::rc_buffer (restriction) covers the double-indirection part (v).
  The "never mutated after construction" half needs whole-program use analysis (Q25 tier 3).

### 2.2 People and works he cites (one hop)

#### 2.2.1 Tony Van Eerd, "Value Oriented Programming Part 1: You Say You Want to Write a Function" (CppNow 2023)

Transcript read in full (youtube id b4p_tcLYDV0, 1:20:48). This is the talk the perfect-function
video opens with (June/Padawan parable: "write the functions you want to see in the world"). Claims:

- TVE-1 (S) Top-down on the way down, bottom-up on the way back: after writing the function the
  call site wanted, narrow its parameters to what it uses (a projector became orientation plus
  tolerance); people do the first half and skip the second, so parameters accrete ("complecting
  made easy": the easiest step at every point makes the code worse).
- TVE-2 (S) Do not pass a "big common struct" (or a model pointer to the whole world) when two
  fields suffice; passing the world makes reaching for it "close at hand".
- TVE-3 (S) Separate calculating from doing (Normand): a calculating function takes values and
  returns an answer; a doing function applies it. "Returning void is a code smell" (stop and
  look): a 150-line function whose last line pushes into a member should return the computed set.
- TVE-4 (S) Prefer returning a value to an out parameter (also unclear whether the callee clears).
- TVE-5 (S) Prefer non-member functions: a class is "velcro"; member functions all break when the
  representation changes; keep a minimal basis set and put the rest outside (Meyers). Do not
  create a base class merely to share one helper: "functions are for sharing".
- TVE-6 (S) Section comments mark cutting points: copy the comment, add underscores and brackets,
  you have a function name (the `step one` grep: search your code base for "step 1" and count
  giant functions). Loops are good cutting points (loosely Parent), "sometimes the whole thing, sometimes
  just the body".
- TVE-7 (S) Locals that are dead after a section prove the cut; make the section a function.
- TVE-8 (S) Naming: no parameter types in function names; `calc` for math, `find` is at worst
  linear, do not call it `get` if it does work; magic numbers like the 5-degree tolerance "came
  out of the air".
- TVE-9 (J) Make a function pure when you need thread safety; locks inside notification
  dispatch cause deadlocks; keep strong ID types (ProjectorId vs CameraId) instead of passing the
  object everywhere.
- TVE-10 (J, caveat) For objects external to the machine (a physical projector) reference
  semantics and polymorphism are legitimate; value orientation applies to things inside it.

#### 2.2.2 Sean Parent

- "C++ Seasoning" (GoingNative 2013, youtube W2tWOdzgXHA): three goals ("goals, not rules"): no
  raw loops (a raw loop is a loop inside a function that does much more than the loop; replace
  with an existing algorithm, a known algorithm from the literature, or a new generic function;
  rotate, stable_partition, slide/gather examples; "replace all coding guidelines with this one"),
  no raw synchronization primitives (mutex, atomic, semaphore, fence: "you will likely get it
  wrong"; use futures/tasks/channels), no raw pointers (a pointer with implied ownership, which
  includes unique_ptr and shared_ptr; leads to incidental data structures and reference semantics).
  Tags SP-1, SP-2, SP-3. Transcript read only through the start of goal 1 plus targeted extracts of goals 2 and 3.
- "Better Code: Runtime Polymorphism" (NDC 2017, id QGcVXgEVMJg): goal "no inheritance";
  "a shared_ptr is as good as a global variable" (SP-4); "write all code as if it were a library"
  (SP-5); polymorphism is a property of use, not of type (SP-6); "no incidental data structures"
  (SP-7: a structure for which no single object owns the relationships, e.g. several shared
  pointers into the same elements). First third read.
- "Goal: no incidental data structures" is the SP-7 sentence the task named; the Smith video's
  ad hoc data structure (PF-13) is the same idea from the code side.

#### 2.2.3 Robert C. Martin

- SRP (blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html, read in
  full): "each software module should have one and only one reason to change", where a reason
  to change is a person or tightly coupled group of people (RM-1; the CFO/COO/CTO Employee
  example). Gather together the things that change for the same reasons, separate those that
  change for different reasons (RM-2). Lineage: Parnas 1972 `[unread]`, Dijkstra separation of
  concerns, Constantine cohesion and coupling.
- "Clean Code" function rules (small, do one thing, one level of abstraction per function, few
  arguments, no side effects, command-query separation): book `[unread]`; quoted here from
  memory `[verify]`: small is about twenty lines or fewer, zero to two arguments ideal, three
  suspect, flag (boolean) arguments are a smell, "do one thing" is "all statements one level
  below the function's name", the stepdown rule.
- Observation for the design: SRP is people-relative (who asks for the change), so it is not
  decidable from structure at all; the Smith/Van Eerd/Parent forms (levels, calculating vs
  doing, loops) are the structure-visible shadows of it (section 9).

#### 2.2.4 Verse effect specifiers (primary: https://github.com/verselang/book, docs/13_effects.md, read)

- Exclusive heap specifiers: `<computes>` (empty heap effects = pure), `<transacts>` (reads,
  writes, allocates; the default), additive: `<reads>`, `<writes>`, `<allocates>`, `<decides>`
  (may fail), `<suspends>` (async; cannot combine with decides). Divergence: `<converges>`
  (guaranteed to terminate; only on native functions, abstract methods and type signatures),
  default is may-diverge. Prediction: `<predicts>`.
- Composition: a function's body may use only effects within its declared set; function types
  are subtypes by effect inclusion (a `<computes>` function can be passed where a
  `<transacts>` one is expected); joining sets is union. Mapping to frob in section 4.3.

#### 2.2.5 Other references appearing in the videos (all `[unread]` unless noted)

Hickey "Simple Made Easy" (complect; cited by Van Eerd), Meyers "How non-member functions improve
encapsulation" (2000), Normand "Grokking Simplicity" (calculations/actions/data), matklad "Study
of std::io::Error" (https://matklad.github.io/2020/10/15/study-of-std-io-error.html), Hinnant et
al. move semantics proposal (the CString example), Arthur O'Dwyer "Super-elider" (initialization
factories), folly FBVector docs (growth factor), ldionne/dyno (type erasure), Rust tracking issue
71668 (`unsafe_op_in_unsafe_fn`), C++ Core Guidelines (two-phase init discouraged `[verify]`
C.41/C.82 family; I.12 not_null `[verify]`).

### 2.3 Adjacent, widely cited sources

Each with the checkable claims. Fowler pages and King/Seemann/Bernhardt/Muratori were fetched; the
rest are `[verify]`.

- Gary Bernhardt, "Boundaries" talk and "Functional Core, Imperative Shell" screencast
  (https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell, blurb
  read; talk `[unread]`): core of values, shell of IO; "an imperative shell with few
  conditionals"; the core tests with no test doubles. Claim GB-1 (S+C): shell functions branch little;
  core functions take and return values.
- Mark Seemann, impureim sandwich (https://blog.ploeh.dk/2020/03/02/impureim-sandwich/, read): the
  best achievable shape is impure entry, pure middle, impure exit: gather from impure sources,
  call a pure function, change state from its result. Claim MS-1 (S+C): in a shell function the
  sequence is (impure*) (pure call) (impure*), with one pure call in the middle. "Dependency
  rejection" (blog.ploeh.dk, 2017) `[verify]`: pass values, not dependencies.
- John Ousterhout, "A Philosophy of Software Design" (https://web.stanford.edu/~ouster/cgi-bin/
  book.php, site read only): deep modules (simple interface, rich implementation), information
  hiding, general-purpose modules are deeper, comments describe what is not obvious from code,
  "define errors out of existence", pull complexity downward `[verify]`. Claims: OU-1 (S) a
  module whose public surface is about as large as its implementation is shallow; OU-2 (S) pass-through
  methods (one-line delegation with the same signature) add interface without depth. He argues
  against very small functions (classitis): this CONFLICTS with Martin/Smith "small functions";
  see section 6 conflict note.
- Casey Muratori, "Semantic Compression" (https://caseymuratori.com/blog_0015, read): do not
  reuse anything until at least two instances exist ("make your code usable before you make it
  reusable"); compress like a dictionary compressor on semantic repetition. Conflicts with Smith's
  n=1 (extract at first use); DUP's clone rungs R1-R5 are the n=2 mechanism.
- Alexis King, "Parse, don't validate" (https://lexi-lambda.github.io/blog/2019/11/05/
  parse-don-t-validate/, read): a parser is a function that refines a type
  (`[a] -> Maybe (NonEmpty a)`); validation that returns unit throws the knowledge away; "use a
  data structure that makes illegal states unrepresentable"; "push the burden of proof upward as far
  as possible, but no further"; shotgun parsing. Claims: AK-1 (S) a function named validate/check
  returning unit/bool where the caller then keeps using the unrefined value; AK-2 (S) the same
  predicate re-checked at several depths.
- Bertrand Meyer, command-query separation and design by contract (as summarized at
  https://martinfowler.com/bliki/CommandQuerySeparation.html, read): queries return a result and do
  not change observable state; commands change state and return nothing (Fowler notes exceptions such
  as `pop`); contracts are pre/postconditions/invariants in the language (Eiffel). Contrast: Smith and
  King prefer to put the precondition in a type; Meyer in a contract; both beat a comment.
- Kent Beck, "Tidy First?" `[unread]`: small structural tidyings (guard clauses, extract helper,
  explaining variables/constants, reading order) done in separate commits before behavior changes
  `[verify]`. Not a lint source; it argues the commit shape (structure change and behavior change
  separate), which frob already has the machinery to check (touched-set vs ticket scope).
- Fowler refactoring catalogue (https://refactoring.com/catalog/, entries read): Extract Function
  (the example is literally a comment-labelled section turned into a function), Replace Primitive
  with Object, Introduce Parameter Object (repeated `(startDate, endDate)` becomes a range),
  Split Phase (parse then compute: `parseOrder` then `price`), Separate Query from Modifier. These
  are the REMEDIES for NEAT rules (Remedy sections); Remove Flag Argument is the remedy for
  the boolean-parameter rule `[verify]`.
- Rust API Guidelines (https://rust-lang.github.io/api-guidelines/checklist.html, checklist read):
  C-NO-OUT (functions do not take out-parameters), C-CUSTOM-TYPE (arguments convey meaning through
  types, not bool or Option), C-NEWTYPE (newtypes provide static distinctions), C-GENERIC (minimize
  assumptions about parameters via generics), C-CALLER-CONTROL (caller decides where to copy and
  place data), C-INTERMEDIATE (expose intermediate results to avoid duplicate work), C-VALIDATE
  (functions validate their arguments), C-STRUCT-PRIVATE, C-NEWTYPE-HIDE, C-CTOR (constructors are
  static inherent methods), C-GOOD-ERR. The newtype and typestate patterns (Rust API / Rust
  Design Patterns book `[verify]`): a single-field wrapper for a distinction or invariant; typestate
  encodes the protocol state as a type parameter so illegal call orders do not compile.
- Edsger Dijkstra, "Go To Statement Considered Harmful" (CACM 1968; EWD215) `[unread]`: the origin of
  structured decomposition: the programmer's understanding of a dynamic process should map to the static
  text; textual structure should mirror the progress of the computation. The structural reading:
  nesting depth and single-entry single-exit are the text-visible proxies.

## 3. What languages and linters already enforce mechanically

(v) = id machine-verified against upstream; [verify] = from memory. Defaults quoted are the
tool's own, as found in its configuration documentation.

### 3.1 Metric rules (size, arity, depth, complexity)

| Concept | Rust (clippy) | Python (ruff) | JS/TS (ESLint) | Go | Java | C/C++ (clang-tidy) |
|---|---|---|---|---|---|---|
| parameter count | too_many_arguments (complexity; default 7) (v) | PLR0913 (v), PLR0917 positional-only count `[verify preview]` | max-params | revive argument-limit (v) | checkstyle ParameterNumber (v), PMD ExcessiveParameterList (v) | readability-function-size ParameterThreshold (v) |
| function length | too_many_lines (pedantic; default 100) (v) | PLR0915 statements (v) | max-lines-per-function, max-statements | funlen (golangci), revive function-length (v) | checkstyle MethodLength, ExecutableStatementCount (v), PMD NcssCount (v) | readability-function-size Line/StatementThreshold (v) |
| nesting depth | excessive_nesting (complexity; default threshold 0 = off) (v) | PLR1702 too-many-nested-blocks `[verify preview]` | max-depth, max-nested-callbacks | nestif, revive max-control-nesting (v) | checkstyle NestedIfDepth/NestedForDepth/NestedTryDepth (v), PMD AvoidDeeplyNestedIfStmts (v) | readability-function-size NestingThreshold (v) |
| cyclomatic | (none; see cognitive) | C901 mccabe, PLR0912 branches (v) | complexity | gocyclo, cyclop, revive cyclomatic (v) | checkstyle CyclomaticComplexity, NPathComplexity (v), PMD CyclomaticComplexity (v) | (clang-tidy has cognitive only) |
| cognitive | cognitive_complexity (restriction since move from nursery; default 25) (v) | (none in ruff `[verify]`) | eslint-plugin-sonarjs cognitive-complexity `[verify]` | gocognit, revive cognitive-complexity (v) | PMD CognitiveComplexity (v), Sonar | readability-function-cognitive-complexity (v) |
| boolean parameters | fn_params_excessive_bools (pedantic; default max 3, 0 = any) (v), struct_excessive_bools | FBT001 FBT002 FBT003 (v) | (typescript-eslint has none core) | revive flag-parameter (not found in revive/ directory listing; `[verify]`) | PMD UseObjectForClearerAPI (v, related) | (none) |
| many returns | (none) | PLR0911 (v) | (core `consistent-return` is different) | (none) | checkstyle ReturnCount (v) | (none) |
| magic values | (none; unreadable_literal is cosmetic) | PLR2004 (v) | no-magic-numbers | revive add-constant (v), golangci mnd `[verify]` | checkstyle MagicNumber (v) | readability-magic-numbers (v) |

Sonar Cognitive Complexity (G. Ann Campbell, whitepaper v1.7, 2023-08-29, read:
https://www.sonarsource.com/docs/CognitiveComplexity.pdf) is the shared definition: three rules
(ignore structures that shorthand multiple statements; +1 for each break in linear flow: loops,
conditionals, catch, switch as one, sequences of like boolean operators, recursion cycles, goto,
break/continue to label; +nesting-level increment for each flow-break nested inside another).
Increment types: structural, hybrid (else if, else: no nesting increment), fundamental,
nesting. It is computable on U from roles (loop, branch, catch, goto, closure nesting): so frob
can compute it uniformly for every F3+ adapter instead of binding six tools (Rule NEAT005).

### 3.2 Loops, iterators and "raw loop" idioms

- clippy: needless_range_loop (style), explicit_iter_loop and explicit_into_iter_loop (pedantic),
  explicit_counter_loop (complexity), while_let_loop (complexity), manual_flatten (complexity),
  manual_memcpy (perf), manual_retain, manual_find, manual_filter_map, same_item_push (style),
  needless_collect (nursery), map_entry (perf) (all v). `manual_fold` does NOT exist (v, checked).
- ruff: PERF401 manual-list-comprehension, PERF402 manual-list-copy, PERF203 try-except-in-loop,
  PLW2901 redefined-loop-name, B020 loop-variable-overrides-iterator, B023 function-uses-loop-variable
  (v); SIM110/SIM111 (any/all loops), C4xx comprehension rules `[verify ids]`.
- ESLint core no-loop-func; eslint-plugin-functional `no-loop-statements` (bans ALL imperative loops),
  `no-let`, `immutable-data`, `prefer-immutable-types`, `no-return-void`, `no-mixed-types`,
  `functional-parameters`, `no-this-expressions`, `no-classes`, `no-class-inheritance` (v, README table);
  `prefer-readonly-type` is listed there but flagged deprecated `[verify]`.
- clang-tidy: modernize-loop-convert `[verify]`; Haskell hlint "Use map", "Use foldr", "Eta reduce"
  `[verify]`; Go: revive range-val-in-closure, range-val-address (v).
- Gap: every one of these matches a SPECIFIC idiom. None implements Parent's criterion "a loop
  inside a function that does much more than the loop", nor Van Eerd's "loop whose body is the
  cutting point". That is a structural, language-neutral predicate (NEAT006).

### 3.3 Effects, purity, honesty (language level)

| Language | Mechanism | Effect it expresses | Maps to |
|---|---|---|---|
| Verse | `<computes>` `<reads>` `<writes>` `<allocates>` `<transacts>` `<decides>` `<suspends>` `<converges>` | compiler-checked effect sets with subtyping | none, reads, writes, alloc, fail, async, total (read in primary) |
| D | `pure`, `@safe`, `@nogc`, `nothrow` | weakly pure: reaches global/static mutable state only through arguments; strongly pure: also no mutable-indirection params (read in spec) | weakly pure = honest; strongly pure = none |
| Nim | `func`, `{.noSideEffect.}`, `{.raises: [].}` | only side effects through parameters; result depends only on parameters; no thread-local/global access (read in manual) | honest |
| Haskell | `IO` in the type; `ST`; Safe Haskell | absence of IO = none (modulo unsafePerformIO, Debug.Trace) | none; `ST` = honest-like |
| Elm | purity enforced; effects only as Cmd/Sub values | none (outside the runtime) | none |
| Koka, Effekt | effect rows (`<exn,div>`), total/pure; Effekt handlers as capabilities `[verify]` | typed rows | declared effect set |
| Hack | contexts and capabilities: `[]` (empty = pure), `[read_globals, write_props]`, default `[defaults]`; callee context list must be a subset of the caller's (read in docs) | enforced capability containment | none, reads(global), writes(prop) |
| Fortran | `PURE`, `ELEMENTAL` procedures | no global-state writes, no IO; pure function dummy args are intent(in) `[verify]` | none (function), honest (subroutine) |
| Ada SPARK | `Global =>` (null, Input, Output, In_Out), `Depends`, `Pre`/`Post`, package `Pure` `[verify]` | proved data flow; `Global => null` is Smith's honest | honest, reads, writes |
| Dafny / Whiley | `function` (pure) vs `method`; `reads`/`modifies` frames; Whiley function vs method `[verify]` | frame specifications | none, reads(x), writes(y) |
| Rust | `const fn` (compile-time evaluable), `#[must_use]`, `unsafe`; no effect system | const fn is NOT purity | adapter inference only |
| C++ | `constexpr`/`consteval`, `[[nodiscard]]`, `noexcept`; GCC/Clang `[[gnu::const]]`/`[[gnu::pure]]` (UNCHECKED optimizer hints) `[verify]` | partial | declared-unverified |
| Python/JS/Go/Java | none | no effect system | frob annotation or adapter analysis |

Mechanical hygiene linters for hidden state: ruff PLW0603 global-statement and PLW0602
global-variable-not-assigned (v), B006 mutable-argument-default, B008 function-call-in-default,
B019 cached-instance-method (v); clippy `static_mut_refs` is a rustc lint (the clippy declared-lints
list does not contain it, v); Go gochecknoglobals, gochecknoinits (golangci, v present in reference
config); PMD MutableStaticState (v); clang-tidy cppcoreguidelines-avoid-non-const-global-variables (v).
Config-driven bans (the right mechanism for ambient sources): clippy disallowed_methods,
disallowed_types, disallowed_macros (v), ruff flake8-tidy-imports banned-api (TID251 `[verify]`),
ESLint no-restricted-properties/no-restricted-globals, golangci forbidigo (v present).
`print`/`exit` family: clippy print_stdout, exit (restriction) (v), ruff T201 (v), revive deep-exit (v).

### 3.4 Types carrying invariants, API shape (language level)

clippy ptr_arg, borrowed_box, ref_option, ref_option_ref, needless_pass_by_value, unused_self,
impl_trait_in_params (restriction), large_enum_variant (perf), result_unit_err, result_large_err,
unnecessary_wraps, must_use_candidate (pedantic), must_use_unit, double_must_use,
missing_const_for_fn (nursery), new_without_default, rc_buffer, trivially_copy_pass_by_ref,
large_types_passed_by_value, type_complexity (all v); Rust has no lint for "newtype this
primitive". clang-tidy bugprone-easily-swappable-parameters (v), modernize-use-nodiscard (v),
bugprone-unused-return-value (v), cppcoreguidelines-owning-memory (v), cppcoreguidelines-no-malloc (v),
modernize-make-unique/make-shared (v), cppcoreguidelines-pro-type-cstyle-cast,
-reinterpret-cast, -const-cast (v), google-readability-casting (v), concurrency-mt-unsafe (v).
PMD UseObjectForClearerAPI, LawOfDemeter, GodClass, DataClass (v). revive modifies-parameter,
unused-parameter, get-return, confusing-results, bare-return (v). checkstyle ParameterAssignment (v).
TypeScript/Java/C#: nullability and branded types are language features, not lint rules.

## 4. Decidability per principle under the universal model

### 4.1 The table

Class: S structural (exact on the closed fragment, Theorem 2), C capability, A annotation or
declared effects, J not lintable. "Needs" names the least thing that makes the answer computable.

| Principle (source) | Candidate rule | Class | Needs | Exact when | Otherwise |
|---|---|---|---|---|---|
| small function (RM, clippy) | statement count | S | Q16 lines/statements | parse_status Ok | Partial parse: Unresolved |
| few arguments (RM, PF-6) | param count | S | Q15 | signature parsed | Unresolved |
| no flag args (PF-6, C-CUSTOM-TYPE) | bool-typed or bool-defaulted param; literal bool at call | S (typed langs), C (untyped: call-site literals only) | Q15 type_text, Q14 literals | param type text is `bool` | alias to bool hidden: Bounds |
| one level of nesting (Sonar, Dijkstra) | depth, cognitive | S | roles | adapter maps roles | Unresolved |
| no raw loops (Parent, PF-10) | loop with non-trivial body in a function doing more | S | loop role, stmt count | closed | Unresolved |
| section comments (PF-11, TVE-6) | label comments inside a body | S | Q10 attachment | comments channel present | NotApplicable (no comments) |
| mixed abstraction level (PF-10) | delegate vs primitive statement mix | S + resolve | Q20 Must for callee classification | callees Must-resolve | Bounds from May edges; Advisory only |
| thin hook (PF-5, PM-2) | size and nesting of a hook | S + hook identity | Q37 entrypoints, Q08 attributes, or `frob:hook` | hook identified | non-hook subjects: NotApplicable |
| dispatcher stays one level above (ruff 29076) | section 5 | S | roles, resolve | closed | Advisory |
| honest function (PF-1) | effects(f) within ceiling | C then A | Q34 effects; declared or inferred | closed call cone and vocabulary covers externals | Bounds{lo,hi}; clean only if hi inside ceiling |
| honesty is infectious (PF-2) | callee effects contained in caller's | C | closure over Q28 edges | Must edges, declared callees | May: lo from Must edges; hi from May edges |
| no hidden global reads (PF-4) | ref resolves Must to mutable module-level binding | S (scope graph) | Q20 + binding mutability attr | Must resolution | May: Bounds; dynamic scope: Unknown |
| ambient sources only at the shell (PF-3) | call to clock/rng/env/fs/net/exit/print vocabulary | S + vocab | Q47 callee_vocab, Q20 | callee resolves Must to a vocab path | name-only match: May |
| dishonesty near roots (PF-2) | call-depth of a dishonest function from entrypoints | Pc over closure | Q30, Q37, effects | whole graph Exact | Unresolved |
| calculate vs do (TVE-3) | big unit-returning function with tail write | S + C | assign role to non-local, effects | direct assignments | mutating method calls need callee effects |
| out parameters (TVE-4, C-NO-OUT) | mutable-mode param first written | S | Q15 mode | `mode` attr present | no mode attr: NotApplicable |
| command-query (Meyer) | returns value AND writes non-local | S + C | effects | closed | off by default (Smith endorses mutate-and-return-info) |
| weakest sufficient parameter (PF-8) | param only iterated, type is owning container | C | Q25 type_of, use analysis | typed, closed | Rust: bind clippy; else Unresolved |
| narrow parameter (PF-7, TVE-1) | param used only via at most k field projections | S | field-access roles | param never escapes whole | escape: clean (can not tell) |
| invariants in types (PF-9) | leading asserts on one param; "must hold lock" prose | S (shape) / J (whether a type is right) | Q14, Q10 | shape matches | shape only; the verdict is J |
| parse, don't validate (AK) | validate/check returning unit/bool then reuse | S heuristic | name vocabulary + return type | n/a | Advisory, off by default |
| idempotence (PF-9) | none: undecidable | A | `frob:idempotent` plus a property test bound by INV | declared | cannot lint, only require evidence |
| single responsibility (RM) | none | J | people | never | section 9 |
| right abstraction level, naming quality, where to stop encoding invariants | none | J | taste | never | section 9 |

Rice's theorem is the reason honesty cannot be a flat Yes/No: "this function reads or writes only
through its parameters" is a non-trivial semantic property. The model's own answer applies: effects
are a Bounds{lo,hi} over atoms; local effects of a body are syntactic (exact when the scope graph
resolves Must); the call-closure is a monotone least fixpoint over a finite powerset (polynomial,
stratified Datalog, Theorem 2); what is undecidable lives only in the EDGES (dynamic dispatch, eval,
FFI, reflection, unresolved externals), and those enter as May/Unknown, so lo comes from Must edges and
Must evidence, hi from every May edge and every unresolved callee. A rule never says "honest" from
absence of evidence; it says Unresolved. This is exactly the "annotate or be opaque" direction.

### 4.2 The effect lattice frob would use

Atoms (extend the capability atoms already in lint-requirements: fs, net, exec, env, sql):

    param            effects confined to locations reachable from parameters (including receiver)
    reads(<place>)   read of a named non-parameter location (module-level variable, static, field of a global)
    writes(<place>)  write of a named non-parameter location
    clock rng env fs net exec stdio sql     ambient sources and sinks (stdio = stdin/stdout/stderr)
    exit             process termination (exit, abort, uncaught panic as a design choice)
    panic diverge    may panic / may not terminate
    alloc            heap allocation visible as an effect (off unless a repo opts in)
    unsafe ffi       region(kind=unsafe) or foreign call
    any              unbounded (declared, as opposed to unknown)

Named levels (a chain; each includes the ones before it):

    none     no effect atoms at all, not even param writes   (Verse computes, D strongly pure, Haskell non-IO, Koka total/pure, Elm)
    honest   only the atom `param`                           (Smith honest; D weakly pure; Nim func; Fortran PURE subroutine)
    reads(G) honest plus reads of the named set G
    writes(G) honest plus reads/writes of the named set G
    io       honest plus any ambient atoms
    any      everything

`dishonest(f)` = effects(f) contains any atom other than `param`. Smith's PF-1 is exactly the level `honest`.
Unknown is not a level: an unannotated function with no adapter analysis has effects = Unknown, and rules
that need effects report Unresolved for it.

### 4.3 The annotation vocabulary frob would accept

A claim is a `comment` directive or an `attr` payload (so languages without line comments work, per
universal-model section 7). Native forms win where they exist; frob directives are the fallback.

    frob:effects <set>        declared effect ceiling of this unit
        <set> := none | honest | io | any
               | atom {"," atom}*          e.g.  reads(CONFIG), writes(cache), clock
               optionally suffixed by  total  (no panic, no diverge)
    frob:pure                 alias of  frob:effects none
    frob:honest               alias of  frob:effects honest
    frob:core                 on a module, file or unit: every function below must satisfy ceiling `honest`
                              (repo-wide default via [neat] core = ["src/domain/**"], core_ceiling = "honest")
    frob:shell                on a unit: permitted to be dishonest; exempt from NEAT010/012/013; subject to NEAT030
    frob:hook [kind]          this unit is a framework hook (kind: main | update | handler | callback | macro)
    frob:dispatcher           this unit is a dispatch site on purpose (consumed by NEAT031)
    frob:idempotent           claim; INV family may require a bound property test
    frob:trusted              suffix on frob:effects: the claim is NOT verified by analysis and the owner owns it

Verification states of a claim, reported in the finding (never silent): VERIFIED (adapter analysis gives hi
inside the claim), CONTRADICTED (lo exceeds the claim: NEAT010 fires), UNVERIFIED (analysis could not decide;
without `trusted` this is Unresolved, with `trusted` it counts as the contract and is listed in the report
as trusted-claim N; changing a trusted claim changes the Attr facet digest, so DRIFT sees it).
External symbols (stdlib, third-party) get effect sets from a data table, not code:

    [neat.effects]                       # frob.toml, shipped defaults per language, repo may extend
    "python:builtins.len"        = "none"
    "python:builtins.print"      = "stdio"
    "rust:std::time::Instant::now" = "clock"
    "rust:alloc::vec::Vec::sort" = "honest"
    "ts:Date.now"                = "clock"

### 4.4 Native forms and how an adapter promotes precision

Native annotation read as a declared effect set (attribute channel Q08, precision "declared"):

| Native form | Declared set |
|---|---|
| Verse `<computes>` / `<reads>` / `<transacts>` / `<decides>` | none / reads(heap) / writes(heap)+reads+alloc / adds `fail` (a cardinality flag, kept as `panic`-like) |
| D `pure` (weak/strong decided by parameter indirections) | honest / none |
| Nim `func`, `{.noSideEffect.}` | honest (none if no var/ref/ptr/cstring/proc params) |
| Hack `[]`, `[read_globals]`, `[write_props]` | none / reads(globals) / writes(props) |
| SPARK `Global => null`, `Global => (Input => X)` | honest / reads(X) |
| Dafny `function`; `method` with `reads`/`modifies` | none / reads(..)/writes(..) |
| Fortran `PURE` | none or honest |
| Haskell signature without `IO` | none (check imports of unsafePerformIO, Debug.Trace) |
| Rust `const fn` | only a hint (compile-time evaluable); no declared set |

Precision ladder per adapter, using Bounds{lo,hi} over atoms (lo from Must evidence, hi from everything
not proven absent):

- Rust. lo: `unsafe` region, `static mut` or `static` interior-mutable access (Must), calls whose Must
  target is in the vocabulary (Instant::now, thread_rng, env::var, fs::*, print!). hi shrinks to
  `honest` iff: no `unsafe`, no `static`/`thread_local!` reference, no IO or atomics/lock types in the
  body, `&mut` only on parameters/locals, every callee Must-resolves to a function whose effects are
  within `honest` (callee closure). Trait-method callees are May until the impl set is a singleton
  (Q25); generic `T: Trait` calls inherit the bound's declared effects if the trait carries
  `frob:effects`.
- Python. lo: `global`/`nonlocal`, assignment to an attribute or subscript of a name that is neither a
  parameter nor a local, Must calls into the vocabulary (open, print, input, time, random, os, sys,
  subprocess, requests). hi shrinks to `honest` iff: none of the above, no `eval`/`exec`/`getattr` with
  non-literal name/`__import__`, no mutable module-level binding referenced (scope graph Must), no
  mutable default arguments used as state, every callee Must-resolved and honest or in the table.
  Unresolved attribute calls on parameters are `param` by definition (this is where Python's
  dynamism helps: a method called on an argument is reachable from the argument) only if the method
  itself is not known to touch globals; otherwise May.
- TypeScript/JavaScript. As Python, plus reads of captured `let`/`var` from an enclosing scope
  (scope graph, binding mutability via `bind(mode)`) count as `reads`; `this` is a parameter in methods.
- Go. lo: package-level `var` reads/writes (Must), `init`, goroutine+channel to outside, vocabulary
  (time.Now, rand, os, net, fmt.Print*). Receivers are parameters.
- Java/C#. lo: static non-final field access, `System.*`, `Random`, `LocalDate.now`, files, sockets;
  instance fields of `this` are `param`.
- C/C++. lo: globals/`static` locals, `errno`, volatile, vocabulary (time, rand, getenv, fopen, printf);
  `[[gnu::const]]`/`pure` and `noexcept` are declared-unverified.
- Haskell/Elm/OCaml: types (IO, ST, Cmd) give lo/hi directly; `unsafe*` and `Debug.Trace` are lo.

Where analysis stalls (opaque regions, macros without expansion, reflection, FFI, unresolved
externals) the answer is Unknown and the rule is Unresolved with a Remedy that names the cheapest fix:
add `frob:effects ...` to the unit, or add the external symbol to `[neat.effects]`.

Why annotation pays beyond linting (PF-15): for a function with ceiling `honest` the set of tests
affected by an edit is exactly the callee closure's Body digests (local reasoning), so `frob test` can
skip every honest function whose closure digest is unchanged; dishonest functions force the wide
touched-set. This turns the annotation into a measured test-time saving, which is the incentive for
people to write it.

## 5. The ruff PR as the canonical example (astral-sh/ruff PR 29076)

Facts (fetched from the GitHub API and the PR diff): "[flake8-builtins] Expand checks in class scopes
(A001)", https://github.com/astral-sh/ruff/pull/29076, opened and merged 2026-10-02 (the author is the
owner's account `lognd`, reviewer `ntBre`). Four commits; the last two are the review response: "Move
the class-scope check into builtin_variable_shadowing" and "Drop the class-scope check from the A001
call site". The review comment on crates/ruff_linter/src/checkers/ast/analyze/expression.rs: "I
initially missed that there was an existing scope check here. Now that the logic is more involved, I
think it's a better fit to move it into the rule function itself."

Before review, inside the dispatcher `expression(expr, checker)` the arm for names held:

    let scope = checker.semantic.current_scope();
    let is_class_attribute = scope.kind.is_class()
        && scope.get(id).is_none_or(|binding_id| matches!(checker.semantic.binding(binding_id).kind,
               BindingKind::Assignment | BindingKind::Annotation));
    if !is_class_attribute { if checker.is_rule_enabled(Rule::BuiltinVariableShadowing) { ... } }

The original (pre-PR) site was `if !checker.semantic.current_scope().kind.is_class() { if
checker.is_rule_enabled(...) {...} }`: a call chain of two, a guard. After the PR the dispatcher is
just `if checker.is_rule_enabled(Rule::BuiltinVariableShadowing) { builtin_variable_shadowing(checker,
id, *range); }` and the 16 added lines (class-scope check with BindingKind) live in the rule function.

### 5.1 The rule it encodes

"Dispatch sites stay one level of abstraction above the logic they dispatch to. A dispatcher that
grows a condition beyond a guard must delegate that condition to the callee." It is the golden rule
(PF-10) applied to routing code, and a special case of Van Eerd's cutting points: the dispatcher's
one job is to decide WHICH peer runs; deciding WHETHER the peer's own concern applies belongs to the
peer, which is also the only place its unit tests and its docs live (the new fixture cases and snapshot
in the PR are for the rule, not the dispatcher).

### 5.2 Detecting a dispatcher by shape (structural)

    dispatcher(f)  :=  f is unit(function) and
        (a) body is dominated by a `branch` group on the kind of one of f's own parameters (a match/switch
            over the dispatched node), or
        (b) apply_stmts(f) / stmts(f) >= r (default 0.7) and apply_stmts(f) >= 5,
        where apply_stmts counts statements that are an `apply` whose head resolves (Q20) to a peer unit
        or to a callee in the same package, optionally wrapped in a guard branch.
    guard(c)       :=  c is a branch condition with weight(c) <= g (default 2), where
        weight(c) = number of apply nodes in c + number of refs to binds declared inside f
                    + 2 * number of closures in c + 2 * number of nested branch or loop groups in c.
        (`checker.is_rule_enabled(R)` has weight 1; `!x.current_scope().kind.is_class()` has weight 2;
         the pre-review version above has weight >= 8 with a closure and a matches!.)
    offender       :=  in a dispatcher, a branch whose condition is not a guard and whose then-branch
                       contains an apply to a peer, or a `bind` introduced only to feed such a condition.

All of this is Q16 roles, Q13/Q20 for "peer", and a small walk of the condition subtree: S, Exact on
the closed fragment; with May callees the apply count has Bounds and the rule stays Advisory.

Confidence raiser (decidable, and the reason a Tier-C fix is possible): `movable(c, call)` holds when every
free variable of c is also a free variable of the call's argument list or is reachable from them (here:
`checker` and `id` are both passed). When movable the finding says "move into <callee>"; when not it says
"hoist into a named predicate".

### 5.3 False-positive risk

1. Performance gating: dispatchers exist to skip calls early; a cheap pre-check hoisted into the dispatcher
   is sometimes deliberate (ruff itself uses `is_rule_enabled` for this). Mitigation: the single-call guard
   is exempt (weight <= g).
2. Shared guards: one condition legitimately guarding several callees (hoisted common precondition). Moving it
   would duplicate it. Suppress when the branch encloses apply to >= 2 distinct callees (knob
   `neat.dispatch_shared_guard_min = 2`).
3. Idiomatic routers: Redux reducers, Elm `update`, message handlers, CLI subcommand `match`, visitors: arms
   with one or two inline statements are the idiom. Mitigation: arm bodies of <= 2 primitive statements are
   not offenders; `frob:dispatcher` or `frob:hook` marks intent.
4. Parsers and interpreters: a large `match` on tokens is the logic, not a dispatcher; the apply ratio r
   separates them (primitives dominate).
5. Generated code and test tables: excluded by path.
6. Languages without roles at F3 (the guard test needs `branch` roles): Unresolved.

## 6. The NEAT rule catalogue

### 6.0 Conventions and one conflict

- Id format NEATnnn (slug alias as in rules.md section 3). All severities below are DEFAULTS; the profile
  knob `neat.profile = "off" | "advisory" | "strict"` shifts them (advisory: everything Advisory;
  strict: Warn where noted). Nothing in NEAT is Error by default: neatness is advice, and Error would make
  every threshold a build break.
- Subjects: units of kind function/method/constructor outside tests and generated code (`neat.exclude`
  globs), unless stated. A rule with zero subjects is Unresolved.
- Every Remedy cites the Fowler refactoring that fixes it. "Tools" lists existing coverage per language;
  a BIND rule is implemented by reading those tools and mapping their ids.
- Conflict to record in the rule docs (not resolvable by a linter): Smith and Martin favour small
  functions and extract at n=1; Ousterhout argues many tiny functions make shallow modules; Muratori
  extracts at n>=2. Resolution proposed: NEAT never FIRES on "too few/too small functions". It only fires on
  the shapes that every camp calls bad (mixed levels, deep nesting, giant bodies). The n=1 versus n=2
  question stays a profile choice for DUP, not NEAT.
- Another conflict: Smith calls `remove_if` (mutates and returns info) an honest specimen while Meyer's CQS
  forbids it; so CQS (NEAT019) is OFF by default.

### A. Shape (structural, universal, Exact)

NEAT001 function-length (Pn, Advisory). Source: RM small functions, PF-0, clippy too_many_lines. Predicate:
statement count of body(u) (not physical lines, so formatting-proof) > `neat.max_statements` (default 40;
tools differ: clippy 100 lines, ruff PLR0915 50 statements, ESLint max-statements 10, checkstyle 150 lines).
Class S, Exact when parse Ok. Knobs: neat.max_statements, neat.exclude. FP: table-driven code, generated, big
`match` that is a dispatch table (see NEAT031), test setup. Tools (BIND): rust too_many_lines; py PLR0915;
ts max-statements/max-lines-per-function; go funlen; java checkstyle ExecutableStatementCount, PMD NcssCount;
c++ readability-function-size. Frob adds only the uniform threshold.

NEAT002 parameter-count (Pn, Advisory; Warn in strict). Source: RM few arguments, PF-6, TVE-1, Fowler
Introduce Parameter Object, PMD UseObjectForClearerAPI. Predicate: count of params(u) excluding receiver
(self/this/cls) > `neat.max_params` (default 5; clippy 7, ruff 5, ESLint 3). Class S, Exact. Knob
neat.max_params, neat.max_params_ctor (constructors, default 7). FP: signature forced by a framework or
trait; DI constructors; FFI shims. Tools (BIND): rust too_many_arguments; py PLR0913; ts max-params; go
revive argument-limit; java ParameterNumber, PMD ExcessiveParameterList; c++ readability-function-size.

NEAT003 boolean-flag-parameter (P+, Advisory). Source: PF-6, Rust API C-CUSTOM-TYPE, Fowler Remove Flag
Argument `[verify]`. Predicate: (i) param whose type text is bool or whose default is a bool literal, in a
unit with visibility >= crate, or (ii) call site passing a bare `true`/`false` literal as a positional
argument whose callee param is bool. Class S in typed languages; untyped languages get (ii) only
(Bounds). Knob neat.max_bool_params (default 0 for public, 2 for private). FP: setters `set_enabled(bool)`,
predicates named by the flag, builder `with_x(true)`. Tools (BIND): py FBT001/FBT002/FBT003; rust
fn_params_excessive_bools (pedantic, default 3: weaker than this rule); go revive flag-parameter `[verify]`;
java PMD UseObjectForClearerAPI (related); ts none. HYBRID.

NEAT004 nesting-depth (Pn, Advisory). Source: Sonar nesting increment, Dijkstra, PF-10. Predicate: max depth of
nested branch/loop/catch groups in body(u) > `neat.max_nesting` (default 3). Class S, Exact. FP: flat
`match` arms count once, so exclude switch-arms from depth. Tools (BIND): rust excessive_nesting (default off);
py PLR1702 `[verify preview]`; ts max-depth; go nestif, revive max-control-nesting; java NestedIfDepth,
NestedForDepth, PMD AvoidDeeplyNestedIfStmts; c++ readability-function-size NestingThreshold.

NEAT005 cognitive-complexity (Pn, Advisory). Source: Sonar whitepaper (section 3.1). Predicate: Sonar score over
roles > `neat.max_cognitive` (default 15, Sonar's own; clippy uses 25). Class S; computable uniformly for
every adapter with loop/branch/catch/closure/recursion roles (recursion needs the edges, so Bounds with
May edges). Tools: rust cognitive_complexity (restriction), go gocognit/revive, java PMD, c++
readability-function-cognitive-complexity, ts sonarjs `[verify]`, py none. NATIVE for languages without a
tool; BIND otherwise.

NEAT006 raw-loop (P+, Advisory). Source: SP-1, PF-10, PF-12, TVE-6. Predicate: a `loop` group L in function f
such that (a) stmts(L.body) > `neat.raw_loop_body` (default 3) or L contains a nested loop/branch with a
write to a bind declared outside L, AND (b) f has other top-level statements besides L
(`stmts(f) - 1 > neat.raw_loop_siblings`, default 2): a loop inside a function that does much more than the loop.
A function whose whole body is one loop is the algorithm itself and is exempt. Class S, Exact. Knobs: the two
above, neat.raw_loop_allow_paths (kernels). FP: hot numeric kernels, state machines and event loops (also hooks),
retry loops, early-exit searches, languages without algorithm libraries (C). Tools (HYBRID, idiom-specific
only): rust needless_range_loop, explicit_counter_loop, manual_flatten, manual_memcpy, while_let_loop,
same_item_push, needless_collect; py PERF401, PERF402, SIM110, SIM111; ts eslint-plugin-functional
no-loop-statements (too blunt: bans all loops); c++ modernize-loop-convert `[verify]`; haskell hlint. The size
criterion is the frob-native part nobody implements. Remedy: Extract Function; Replace Loop with Pipeline
(Fowler `[verify]`).

NEAT007 section-comment (P+, Advisory; Warn in strict). Source: PF-11 ("dead giveaway"), TVE-6, Fowler
Extract Function (example is a labelled section). Predicate: in a function with > `neat.section_min_stmts`
(default 12) body statements, >= `neat.section_min_labels` (default 2) comments that are (i) leading trivia of a
statement at body depth 0, (ii) label-shaped: <= 6 words, own line, no terminal sentence punctuation, or banner
form (`// ---- x ----`, `# Step 1`, `#region`, `// 1.`), and (iii) not a doc/directive/TODO/license comment.
Class S, Exact for the shape; whether it signals mixed levels is judgment, hence Advisory. Needs Q10
`enclosing`/`following` (F4); NotApplicable where no comments exist. FP: licence banners, protocol steps that
mirror a spec ("RFC step 3"), tests ("arrange/act/assert" labels), literate code. NATIVE (no linter covers
it). Knob: neat.section_labels_extra (regexes).

NEAT008 abstraction-level-mix (Pn, Advisory, experimental, off in all profiles at first). Source: PF-10.
Classify each top-level statement: delegate (an `apply` or `bind` of an `apply` whose head Must-resolves
to a unit in the same package), scaffold (branch/loop group), primitive (operators, literals, indexing, direct
assignment). Fire when f has >= 1 delegate AND a primitive-dense run of >= `neat.mix_primitives` (default 4)
inside or beside delegates. Class S + resolve; May callees widen: delegates counted only on lo for the
"has delegate" half and on hi for the primitive half, so only a sure mix fires. FP: glue with small
arithmetic, builders, math code. NATIVE; this is a heuristic proxy and the note's honest position is that
NEAT006/NEAT007 carry the signal and NEAT008 is a research toggle.

NEAT009 magic-value (Pn, Advisory). Source: TVE-8 ("that five is terrible"), PLR2004. BIND only: py PLR2004,
ts no-magic-numbers, java MagicNumber, go revive add-constant, c++ readability-magic-numbers. Rust: none
(unreadable_literal is cosmetic).

### B. Honesty and purity (capability and annotation)

NEAT010 effect-ceiling-exceeded (P+, Warn when a ceiling is declared). Source: PF-1, PF-2, Verse subset rule,
Hack contexts. Predicate: unit u has a declared ceiling C (`frob:effects`, native form, or inherited from
`frob:core`); fires if effects(u).lo is not contained in C, i.e. some EffectSite from Must evidence is outside C;
also fires per call edge: callee g with effects(g).lo outside C(u). Clean only if effects(u).hi is inside C;
otherwise Unresolved (UNVERIFIED claim, section 4.3). Class C then A. Evidence in the finding: the EffectSite
(atom, loc, via Typed|Lexical). Knobs: neat.core, neat.core_ceiling, neat.effects (table), neat.trusted_ok
(default false). FP: logging (`stdio`) in core, metrics, tracing, memoization caches (a `writes(cache)` that is
semantically pure): declare `writes(cache)` or whitelist atoms via neat.ignore_atoms. Tools: language level
only, see 3.3 (D pure, Nim func, Haskell types, Verse/Hack, Fortran PURE, SPARK Global); for Rust/Python/TS/Go/
Java there is none, and config-driven bans (clippy disallowed_methods, ruff TID251, ESLint no-restricted-*,
golangci forbidigo) catch the ambient-source half. HYBRID: bind those findings as lo evidence.

NEAT011 effects-undeclared (P-, Unresolved by default; Advisory once `neat.require_effects = true`). Source:
the "annotate or be opaque" direction. Predicate: a unit inside `frob:core` (or a unit explicitly marked
`frob:honest` in a callee list) has no declared set and no adapter analysis that bounds hi. P- fires only if hi
lacks a declared or proven bound; clean if declared or proven. This rule is the thing that makes NEAT010
non-vacuous: without it a repo gets Unresolved everywhere. Remedy text: add `frob:effects ...` or add external
symbols to `[neat.effects]`. NATIVE.

NEAT012 hidden-state-read (P+, Advisory; Warn in strict). Source: PF-4 (global PRNG), PF-1, Sean Parent "a
shared_ptr is as good as a global". Predicate: a `ref` in a non-shell, non-hook function resolves (Must) to a
`bind` at module/package/static scope that is mutable (static mut, module-level assigned more than once or
non-const, `var` at package level, `global`), or to a mutable default argument used as state (B006), or to a
captured outer `let/var`. May resolution gives Bounds (fires only on Must). Class S via the scope graph plus
binding-mutability attribute (F2+). Knobs: neat.allowed_globals (loggers, constants by naming), neat.const_by_name
(UPPER_CASE counts as constant, default true in Python). FP: loggers, config singletons deliberately read in
a shell, interned tables, Python module "constants" with no `Final`. Tools (HYBRID): py PLW0603, PLW0602,
B006, B008, B019; rust rustc static_mut_refs, clippy declare_interior_mutable_const `[verify]`; go gochecknoglobals,
gochecknoinits; java PMD MutableStaticState; c++ cppcoreguidelines-avoid-non-const-global-variables; ts
functional/immutable-data, no-let (blunt).

NEAT013 ambient-source-call (P+, Advisory; Warn in strict). Source: PF-3, PF-14, GB-1, MS-1. Predicate: a call whose head
Must-resolves to a vocabulary entry of class clock, rng, env, fs, net, exec, stdio, exit, appearing in a unit
that is not `frob:shell`, not a hook, and not main. Dependency-injection fix is in the Remedy. Class S + vocab
(Q47; empty vocabulary is NotApplicable, never "no hits"). Name-only match without resolution is May and does
not fire (lo). Knobs: neat.vocab_extra, neat.shell_paths, neat.ambient_ignore (atoms). FP: thin wrappers that ARE
the injection seam (`SystemClock::now`), logging, CLI crates. Tools: rust clippy disallowed_methods /
disallowed_macros (config), print_stdout, exit; py ruff TID251 `[verify]`, T201, DTZ family (different aim); ts
no-restricted-properties; go forbidigo, revive deep-exit; java forbiddenapis `[verify]`. HYBRID: frob owns the
cross-language vocabulary table, tools are corroboration.

NEAT014 dishonesty-depth (Pc, Advisory, needs Exact graph else Unresolved). Source: PF-2 ("dishonest near roots"),
GB-1. Predicate: for each unit d with effects(d).lo containing a non-param atom, minimum call distance from any
entrypoint (Q37) or hook, over Must edges, > `neat.max_dishonest_depth` (default 2). Class C (Q28/Q30/Q37).
Pc polarity: Exact only. FP: logging/telemetry leaf helpers, deliberately layered shells. NATIVE.

NEAT015 discarded-pure-result (P+, Warn). Source: PF-1 (an honest function with `none` effects communicates only
through its return), Rust `#[must_use]`. Predicate: an expression statement that is an `apply` whose callee
effects are `none` and which returns a non-unit value: the call does nothing. Class C (callee effects) or A.
Tools: rustc unused_must_use, clippy let_underscore_must_use (restriction); c++ bugprone-unused-return-value;
haskell -Wunused-do-bind `[verify]`; py/ts/go none. HYBRID.

NEAT016 name-effect-mismatch (P+, Advisory). Source: PF-0 dishonest accessor story, TVE-8, Rust API C-GETTER/C-CONV.
Predicate: unit name starts with a query prefix (get, is, has, find, calc, compute, to_, as_; knob neat.query_prefixes) and
effects(u).lo contains `writes`, `reads(non-param)` or an ambient atom other than clock-free reads. Class C then
A. Naming QUALITY is not judged, only name-versus-declared-effect consistency. Tools: rust wrong_self_convention
(is_/as_/to_/into_ conventions), py none, java PMD none. NATIVE.

NEAT017 calculate-then-store (P+, Advisory). Source: TVE-3 (calculating vs doing; "returning void is a code
smell"), Fowler Split Phase and Separate Query from Modifier. Predicate: unit returns unit/void, has > `neat.calc_min_stmts` (default 15)
body statements, and its non-local writes (assign role to a bind outside body, or a mutating call on a param/field)
are confined to the last <= 2 top-level statements. Class S for direct assignment; mutating method calls need
callee effects (C), so detection is Bounds for those. FP: render/draw/IO functions legitimately return nothing;
exclude shell/hook and effects containing an ambient atom. Tools: eslint-plugin-functional no-return-void is the
blunt version. NATIVE.

NEAT018 out-parameter (P+, Advisory). Source: TVE-4, Rust API C-NO-OUT, Core Guidelines F.20 `[verify]`. Predicate: a
param with mutable-reference mode (Q15 `mode`) whose first use on every path is a write (assign, clear, push, `*p =`),
in a unit that returns unit or a status. In-out parameters (read first) are NOT flagged (sort-in-place is honest).
Class S, exact where `mode` is present; NotApplicable otherwise (JS/Python mutate args freely, no mode). FP: C APIs,
buffer-reuse hot paths (TVE concedes), FFI. Tools: C# CA1021 `[verify]`; clang-tidy none; rust none. NATIVE.

NEAT019 command-query-violation (P+, OFF by default). Source: Meyer CQS. Predicate: unit with a non-local write and a
non-status return value (a status is Result<(), E>, bool success, or the new length). See 6.0 conflict; keep as a
named opt-in rule. Class S + C. NATIVE.

### C. Types carry invariants

NEAT020 narrow-parameter-use (P+, Advisory). Source: PF-7 ("wallet and card"), TVE-1, TVE-2. Predicate: a non-receiver
param p such that every `ref` to p in the body is the base of a field projection and the distinct projected
fields number <= `neat.narrow_max_fields` (default 2); p is never passed whole, returned, captured, or method-called. Class S
(Exact for the single function); passing p onward counts as a non-projection use, so the rule stays clean there (it cannot
tell). FP: trait/interface-forced signatures, event/context objects in hooks, ORM entities, DTO handlers. Tools: none
(PMD LawOfDemeter is different). NATIVE. Remedy: Introduce Parameter Object in reverse, or narrow the signature;
TVE-1's "wrapper at the top, narrow function below".

NEAT021 weakest-sufficient-parameter-type (P+, Advisory). Source: PF-8, SO-3, OP-1, Rust API C-GENERIC. Rust: BIND
clippy ptr_arg, borrowed_box, ref_option, ref_option_ref, needless_pass_by_value; C++: const vector& where only iterated
needs use analysis (Unresolved); py/ts: annotations only, Unresolved. Class C (Q25 type_of). BIND-only; frob adds no
re-implementation.

NEAT022 swappable-primitive-parameters (P+, Advisory). Source: PF-6 ("strong types for everything"), Fowler Replace
Primitive with Object, Rust API C-NEWTYPE. Predicate: public unit with a run of >= `neat.swap_min_run` (default 3)
adjacent params of the same primitive type text (int, float, str, string, bool). Class S in typed languages (aliases hide
types: Bounds). Tools: clang-tidy bugprone-easily-swappable-parameters (v); none elsewhere. HYBRID.

NEAT023 precondition-outside-type (P+, Advisory, off in strict until tuned). Source: PF-9, AK, Meyer DbC. Predicate: unit whose
first statements are an assertion/guard on a single parameter (assert vocabulary Q47, or `if p == null/0/empty -> panic|return`), or whose
doc/comment contains precondition phrases ("must be", "caller must hold", "requires", "never null", knob neat.precondition_phrases).
Class S for the shape; whether a type could carry it is J. FP: assertions for relations between parameters (ordering), cross-field
invariants, debug asserts at trust boundaries. Tools: clippy missing_panics_doc, missing_errors_doc (docs hygiene, different aim).
NATIVE; the finding names the candidate newtype (NormalizedVec3, NonEmpty, lock receipt).

NEAT024 option-with-many-none-paths (P+, Advisory). Source: RE-1. Predicate: unit returning Option/Maybe/`T | None`/`T?`
with >= `neat.none_paths` (default 3) distinct `return None`-equivalent sites (excluding `?` propagation). Class S where the return type text is
Option-like; else NotApplicable. FP: `get`-like lookups with several guard returns of one reason. Tools: clippy unnecessary_wraps
(opposite problem), option_option, result_unit_err (v). NATIVE.

NEAT025 validate-returns-nothing (P+, Advisory, off by default). Source: AK ("parse, don't validate"), Fowler Replace Primitive with Object.
Predicate: unit whose name matches a validation vocabulary (validate, check, ensure, verify, assert_valid, is_valid; knob) returning unit/bool/Result<(),_>
and taking a value that its callers then keep using unrefined (callers: Q29 referrers; the call's value is discarded or used only in an if). Class S heuristic.
FP: validators that legitimately return bool for search/filter use; this is the weakest rule here and is included so the owner can choose. NATIVE.

NEAT026 must-use-missing (P-, Advisory). Source: PF-1, Rust `#[must_use]`, C++ `[[nodiscard]]`. Predicate: a unit with effects `none`/`honest` that
returns non-unit and lacks a must-use attribute (Q08). P- (absence of a required attribute): fires only if hi lacks it, clean if lo has it. Class C+S. Tools (BIND):
rust must_use_candidate (pedantic), must_use_unit, double_must_use; c++ modernize-use-nodiscard (v); py/ts/go: none.

NEAT027 half-built-object (P+, Advisory, off by default). Source: CB-2, MB-4. Predicate: a type with a no-argument constructor (or none declared) and a
method named in a vocabulary (init, initialize, setup, open, start; knob) that assigns a field the constructor does not assign. Class S. FP: lazy
init, builders (the builder IS the half-built object by design), framework lifecycles (annotate `frob:hook`). Tools: C++ Core Guidelines only `[verify]`. NATIVE.

### D. Boundaries, hooks, dispatch

NEAT030 thin-hook (Pn, Warn in strict, Advisory otherwise). Source: PF-5, PM-2, GB-1, MS-1. Predicate: unit identified as a hook (Q37 entrypoints incl.
`main`; decorated handlers via Q08 attribute registry such as `@app.route`, `#[proc_macro*]`, `#[tokio::main]`, `@Test` excluded; names in
neat.hook_names when `frob:hook` absent, which yields Bounds; or `frob:hook`) with statement count > `neat.hook_max_statements` (default 8) or
nesting > `neat.hook_max_nesting` (default 1) or a loop whose body > 1 statement. Also checks the sandwich shape (MS-1) when `frob:shell`: statements
should be impure* pure-call impure* with at most `neat.shell_max_branches` (default 2) branches. Class S + hook identity (C). Non-hook subjects:
NotApplicable (not clean). FP: `main` that wires many services, event loops, CLI parsers (clap derive is declarative: thin by construction),
generated. Tools: none specific. NATIVE.

NEAT031 dispatch-site-owns-logic (Pn, Advisory; Warn when `movable`). Source: ruff PR 29076 (section 5), PF-10. Predicate as in 5.2. FP in 5.3. NATIVE.

NEAT032 incidental-data-structure (P+, Advisory, experimental). Source: PF-13, SP-7. Predicate: within one type/module, >= 2 functions apply the same resolved
unary transform f to a parameter and then use the result as key/index/search argument on the same field F (the asset manager: lower-case then binary
search then insert). Class S over (F, f) pairs. FP: many; shipped only so the pattern has a name. NATIVE.

### E. Language-level least power (Lang tier; BIND-first)

NEAT040 minimal-unsafe-region (P+, Advisory). Source: SO-5. Predicate: `region(kind=unsafe)` with > `neat.unsafe_max_ops` (default 1) operations, or a body of an
`unsafe fn` containing unsafe operations outside a nested region. Class S. Tools (BIND): rustc unsafe_op_in_unsafe_fn, clippy multiple_unsafe_ops_per_block,
undocumented_unsafe_blocks (restriction) (v). Other languages (C#, Swift, Go): NotApplicable unless the adapter maps `region(unsafe)`.

NEAT041 enum-glob-in-match (P+, Advisory, Rust). Source: SO-2. BIND clippy enum_glob_use (pedantic), wildcard_enum_match_arm (restriction) (v). Tree-sitter query
if clippy is absent.

NEAT042 powerful-cast (P+, Advisory, C/C++/Rust). Source: CC-1..CC-4. Predicate: a C-style cast; reinterpret_cast/const_cast outside an allowlist; Rust `as` between numeric types
where From/TryFrom exists. BIND clang-tidy cppcoreguidelines-pro-type-cstyle-cast, -reinterpret-cast, -const-cast, google-readability-casting; clippy as_conversions
(restriction), cast_lossless (pedantic) (v).

NEAT043 raw-owning-pointer (P+, Advisory, C++). Source: SP-3. Predicate: `new`/`delete` expressions, `malloc`, owning raw pointer members, `shared_ptr` in public signatures
(SP-4). BIND clang-tidy cppcoreguidelines-owning-memory, -no-malloc, modernize-make-unique/make-shared (v).

NEAT044 raw-sync-primitive (P+, Advisory). Source: SP-2. Predicate: use of mutex, atomic, condition variable, fence, semaphore types or calls outside
`neat.sync_allowed_paths`. Class S + vocab/type names (Q47). Tools: clippy disallowed_types (config) and mutex_atomic `[verify]`, clang-tidy concurrency-mt-unsafe (different
aim), go vet copylocks `[verify]`. NATIVE vocabulary.

NEAT045 reserve-in-reusable-api (P+, Advisory). Source: RS-1. Predicate: a vocabulary call (`std::vector::reserve`, Rust `Vec::reserve_exact`, `TArray::Reserve`,
Java `ensureCapacity` `[verify]`) whose receiver root is a parameter or `self`/`this` field in a unit with visibility >= crate, or any such call inside a loop. Class S + vocab.
Direction note: clang-tidy performance-inefficient-vector-operation asks for reserve before a push loop on a LOCAL vector; the two do not conflict (local vs received). NATIVE.

NEAT046 consuming-trait-return (P+, Advisory, Rust). Source: SO-4. Predicate: return type text `impl Into<_>`, `impl IntoIterator<..>`, `impl ToString`, or any `impl Trait` where
Trait is in the repo-configured single-consuming-method set. Tree-sitter query, Exact. No clippy lint found `[verify]`. NATIVE (Lang).

## 7. Rollout and profiles

- Fidelity gating: NEAT001-004, 007, 009 need F1-F2 plus Q16/Q10; NEAT005, 006, 012, 013, 020, 030, 031 need F3 roles and Must resolution; NEAT010,
  011, 014-016, 026 need the effects capability (declared precision first, inferred later); NEAT040-046 are Lang tier and need only a grammar.
- Order of adapter work that buys the most: (1) Rust and Python F3 with roles; (2) the effects atom vocabulary (Q47 table extended with clock/rng/stdio/exit);
  (3) `frob:effects` reader; (4) Rust and Python body analysis promoting hi to `honest`.
- Profiles: `off`; `advisory` (all Advisory, nothing fails a run); `strict` (the ones marked Warn). `--fail-on` stays the only thing that fails CI (rules.md section 1).
- Ratchet: thresholds are most useful with the ratchet pools (rules.md section 6): freeze today's offender set and fail only on new or worse.

## 8. The ten rules to ship first, and why

Selection criteria, in order: (1) decidable on structure or declared annotation, so the answer is Exact on the closed
fragment and Unresolved (not wrong) elsewhere; (2) low false-positive rate or a clean suppression story;
(3) the owner's stated targets (honest functions, one level per function, thin hooks, invariants in types);
(4) frob adds something no existing tool does, or one threshold uniform across languages. Commodity metrics
(NEAT001 length, NEAT005 cognitive, NEAT009 magic value) ship as BOUND entries in the profile so they appear under one id
and one config, but frob authors nothing; they do not count toward the ten.

1. NEAT002 parameter-count. Exact, cheapest, every language has a tool to bind, and it is the direct trigger for Introduce Parameter Object (PF-6, TVE-1). Proves
   the bind-the-tool mechanism end to end.
2. NEAT003 boolean-flag-parameter. Exact in typed languages; the strongest single readability smell in Smith's video; clippy only covers "more than 3" and ruff only
   Python, so a uniform P+ rule has real value. Call-site literal form works even in untyped languages.
3. NEAT004 nesting-depth. Exact from roles, one number, a direct structural reading of "one level at a time" (Dijkstra, Sonar). Ships with NEAT005's role machinery.
4. NEAT007 section-comment. The sharpest checkable proxy for mixed abstraction levels (PF-11, TVE-6) and the one gap where NO linter exists; Exact for the shape,
   Advisory because the meaning is judgment. Cheap (comments plus attachment) and a good demo of the F4 comment channel.
5. NEAT006 raw-loop (loop in a function that does more than the loop). Parent's single highest-leverage goal; tools only match idioms, none match the size criterion.
   Needs only the loop role and statement counts. Highest false-positive risk of the ten, hence Advisory and the leaf-exemption.
6. NEAT012 hidden-state-read. The scope graph already answers it (Must edge to a mutable module-level bind); it is the structural half of "honest" and needs no annotation or
   effects analysis at all. Directly the particle-PRNG example. Exact where resolution is Must.
7. NEAT013 ambient-source-call. The other half of honesty that needs only the callee vocabulary (clock, rng, env, fs, net, stdio, exit) and Must resolution; the
   remedy (inject at the top, functional core / imperative shell) is exactly the owner's wording. Reuses Q47 and the CAP atoms.
8. NEAT010 effect-ceiling-exceeded with its annotation face NEAT011 effects-undeclared (counted as one slot). This is the capability/annotation pair that makes
   "honest" a checked claim: declared ceilings, native specifiers mapped (D pure, Nim func, Verse, Hack contexts, SPARK Global), Bounds{lo,hi}, Unresolved when
   the adapter cannot bound hi. Ship it with only DECLARED precision first (no analysis), then promote with Rust/Python body analysis.
9. NEAT030 thin-hook. The owner's "thin framework hooks"; Exact once hook identity is known (entrypoints, attribute registry, `frob:hook`); NotApplicable, never
   clean, for non-hooks. PM-2 shows the same shape for proc macros.
10. NEAT031 dispatch-site-owns-logic. The ruff PR 29076 pattern as a rule: dispatcher by shape plus a condition-weight test plus the `movable` check that makes the
    remedy mechanical. Advisory; included first because it is the worked example the owner brought and because its predicate reuses NEAT006/NEAT008's statement classification.

Deferred on purpose: NEAT008 (heuristic proxy), NEAT014 (needs Exact whole-graph), NEAT015/026 (need callee effects), NEAT019 (conflicts with Smith), NEAT025, 027, 032
(weak heuristics), and the Lang-tier BIND rules NEAT040-046 (cheap to add later, no new model support needed).

## 9. What cannot be linted (and why, honestly)

- Whether the abstraction LEVEL of a statement is right. Level is relative to the function's name and the reader's expectation; there is no ground truth in the tree.
  Structure gives proxies (section comments, delegate/primitive mix, loop size) that correlate; the verdict stays a review judgment. (PF-10)
- Single responsibility, as Martin defines it: "one reason to change" where reasons are people (CFO, COO, CTO). The organisation chart is not in the source. Only its
  structure-visible shadows (size, mixed effects in one function, calculating vs doing) are checkable.
- Naming quality. A name is natural language; the checkable slice is consistency between a name vocabulary and declared effects/types (NEAT016, Rust API C-CONV,
  clippy wrong_self_convention), banned words, and shape rules, never "is this a good name".
- Whether an invariant should live in a type and where to stop ("not wise or feasible to encode every combination ... I know it when I see it", PF-9). Cost versus
  benefit; the lint can only show the candidate (leading asserts, "must hold" prose).
- Idempotence, determinism, termination and totality of arbitrary code: semantic properties, undecidable (Rice, universal-model 4.5). Only declared (`frob:idempotent`,
  `frob:effects ... total`) plus bound evidence (a property test) can be required; the claim itself cannot be proven by frob.
- Whether a dishonest effect is benign. A memoization cache or a log line is observable only to someone watching; "pure enough" is a policy decision, expressed by
  `neat.ignore_atoms`, not derived.
- Extract at n=1 versus n=2 versus never (Smith vs Muratori vs Ousterhout): a values question. NEAT refuses to fire on "too few functions".
- Performance claims: `reserve` in a loop, `Arc<str>` versus `String`, `fn` pointer versus generic `F`. Right or wrong depends on workload and measurement; frob has PERF and engine timing
  for that, and NEAT only flags the structural precondition (NEAT045).
- Whether reference semantics or polymorphism is legitimate because the thing is external to the machine (TVE-10); whether to choose intrusive or non-intrusive dispatch (DD-3).
- Whether "thin" is thin enough: the thresholds are knobs because the right number is a team decision.
- Shared-condition hoisting versus delegation in a dispatcher (5.3 items 1-3): the performance and duplication tradeoff is a human call; the rule can only compute `movable`.

## 10. Open questions for the owner

1. Which NEAT knobs are `enforcement` fields written by `frob init`? Proposal: `neat.profile` plus the ten first-wave thresholds only; the rest default silently.
2. Where do the effect tables live: shipped data crate per language, `[neat.effects]` in frob.toml, or both with repo override winning? (Proposal: both.)
3. Should `frob:effects` enter the Attr facet digest so DRIFT sees a changed claim? (Proposal: yes; trusted claims especially.)
4. Is a method receiver a parameter for the purposes of `honest`? On a large aggregate `&mut self` can reach the world, which weakens the claim. Proposal: yes by default,
   `neat.receiver_is_param = false` for strict profiles.
5. NEAT versus existing families: NEAT002/004/001 overlap LARGE's "small metric core" (size, nesting, LCOM, coupling) in rules.md section 3. Merge or keep as
   LARGE for repo-level and NEAT for function-level? And the effect atoms should be shared with grimble CAP rather than duplicated.
6. Confirm the policy of never firing on "too many small functions" (6.0 conflict).
7. `[verify]` items to close before acceptance: ruff stable-versus-preview status of PLR0904, PLR0914, PLR0917, PLR1702, PLR6301; revive flag-parameter and unused-parameter (not in the
   rule/ listing I fetched); ruff TID251; golangci mnd; the Fortran, SPARK, Dafny, Whiley and Effekt rows of 3.3; PMD/Checkstyle behaviours quoted from memory; Clean Code function numbers; Core
   Guidelines rule numbers; Beck and Dijkstra summaries; Ousterhout claims beyond the site text.

## Appendix A. Logan Smith channel index

Source of the list: `yt-dlp --flat-playlist --print "%(id)s %(title)s" https://www.youtube.com/@_noisecode/videos` on 2026-10-02 (13 entries, matches the RSS feed). Transcripts: yt-dlp
auto-subs, 13 of 13 obtained, kept outside the repo (session scratchpad). "Read" means the whole transcript unless noted.

| # | Date | Video id | Title | Read | Rules extracted (tags; NEAT ids) |
|---|---|---|---|---|---|
| 1 | 2026-08-20 | 2OMRWPOSw9s | How to write the perfect function | full | PF-1..PF-15; NEAT010-013, 014, 016, 020, 021, 022, 023, 007, 006, 030, 032 |
| 2 | 2026-07-23 | ebqKYLKjL6U | Verse: A New Scripting Language? In THIS Economy? | full | VS-1..VS-4; annotation vocabulary 4.3, NEAT010 |
| 3 | 2025-11-06 | Klq-sNxuP2g | Moves Are Broken | full | MB-1..MB-5; NEAT027, NEAT021 (non-null), (MB-3 move-with-invariant: clang-tidy cppcoreguidelines-special-member-functions `[verify]`) |
| 4 | 2025-01-09 | SMCRQj9Hbx8 | Comprehending Proc Macros | first ~40% full, rest scanned | PM-1..PM-4; NEAT030 (proc-macro entry as hook); PM-3 quote! path qualification: unclaimed Lang(Rust) rule |
| 5 | 2024-01-19 | KWB-gDVuy_I | Constructors Are Broken | full | CB-1..CB-5; NEAT027, constructor-body-size via NEAT001 with ctor knob, unchecked-factory marker (needs `unsafe`, Rust) |
| 6 | 2023-10-19 | SmlLdd1Q2V8 | Cursed C++ Casts | full | CC-1..CC-4; NEAT042 |
| 7 | 2023-09-28 | wU8hQvU8aKM | Two Ways To Do Dynamic Dispatch | full | DD-1..DD-3; NEAT043 area (virtual destructor: clang-tidy cppcoreguidelines-virtual-class-destructor `[verify]`) |
| 8 | 2023-08-31 | 8j_FbjiowvE | 5 Strong Opinions On Everyday Rust | full | SO-1..SO-5; NEAT041, 021, 046, 040 |
| 9 | 2023-08-17 | algDLvbl1YY | The Dark Side of .reserve() | full | RS-1, RS-2; NEAT045 |
| 10 | 2023-07-27 | s5S2Ed5T-dc | A Simpler Way to See Results | full | RE-1..RE-4; NEAT024 (plus result_unit_err bound) |
| 11 | 2023-07-13 | SqT5YglW3qU | Rust Functions Are Weird (But Be Glad) | full | FW-1, FW-2; no NEAT rule (perf and judgment, section 9) |
| 12 | 2023-06-29 | 6c7pZYP_iIE | Choose the Right Option | full | OP-1; NEAT021 (clippy ref_option) |
| 13 | 2023-06-13 | A4cKi7PTJSs | Use Arc Instead of Vec | full | AR-1; clippy rc_buffer bound under PERF, not NEAT |

Unread: none. Videos with no NEAT rule are listed with the reason, not dropped.

## Appendix B. One-hop reference status

| # | Work | URL or identifier | Status |
|---|---|---|---|
| 1 | Van Eerd, Value Oriented Programming Part 1: You Say You Want to Write a Function (CppNow 2023) | https://www.youtube.com/watch?v=b4p_tcLYDV0 | read, transcript, full |
| 2 | Parent, C++ Seasoning (GoingNative 2013) | https://www.youtube.com/watch?v=W2tWOdzgXHA | read in part (start plus goals 2 and 3 extracts) |
| 3 | Parent, Better Code: Runtime Polymorphism (NDC 2017) | https://www.youtube.com/watch?v=QGcVXgEVMJg | read in part (first third) |
| 4 | Martin, The Single Responsibility Principle (2014) | https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html | read, full |
| 5 | Martin, Clean Code (function chapter) | book | [unread], quoted from memory [verify] |
| 6 | Verse book, Effects chapter | https://github.com/verselang/book (docs/13_effects.md) | read, full |
| 7 | Hickey, Simple Made Easy | conference talk | [unread] |
| 8 | Meyers, How Non-Member Functions Improve Encapsulation | C/C++ Users Journal 2000 | [unread] |
| 9 | Normand, Grokking Simplicity | book | [unread] |
| 10 | Parnas, On the Criteria To Be Used in Decomposing Systems into Modules (1972) | CACM | [unread] (quoted via Martin's post) |
| 11 | matklad, Study of std::io::Error | https://matklad.github.io/2020/10/15/study-of-std-io-error.html | [unread] |
| 12 | Hinnant et al., move semantics proposal (CString example) | WG21 | [unread] |
| 13 | C++ Core Guidelines (initialization, not_null) | https://isocpp.github.io/CppCoreGuidelines/ | [unread] |
| 14 | O'Dwyer, Super-elider round 2 | https://quuxplusone.github.io/blog/2018/05/17/super-elider-round-2/ | [unread] |
| 15 | folly FBVector growth-factor docs | https://github.com/facebook/folly/blob/main/folly/docs/FBVector.md | [unread] |
| 16 | ldionne/dyno | https://github.com/ldionne/dyno | [unread] |
| 17 | Rust issue 71668 (unsafe_op_in_unsafe_fn) | https://github.com/rust-lang/rust/issues/71668 | [unread] |

Also cited in passing and not enumerated above: Kate Gregory "Am I a good programmer?" and D. J. Wheeler on subroutines (both via Van Eerd), Scott Meyers by name.
Adjacent sources fetched in section 2.3: Seemann impureim sandwich, Bernhardt screencast blurb, King, Muratori, Fowler catalogue and CQS bliki, Rust API Guidelines checklist, Ousterhout
book page, Sonar whitepaper (partly read: definitions and increment rules).

Other URLs used: https://api.github.com/repos/astral-sh/ruff/pulls/29076 and its comments/files/diff;
https://raw.githubusercontent.com/rust-lang/rust-clippy/master/clippy_lints/src/declared_lints.rs;
https://raw.githubusercontent.com/rust-lang/rust-clippy/master/book/src/lint_configuration.md;
https://raw.githubusercontent.com/astral-sh/ruff/main/crates/ruff_linter/src/codes.rs;
https://clang.llvm.org/extra/clang-tidy/checks/list.html; https://github.com/eslint-functional/eslint-plugin-functional;
https://dlang.org/spec/function.html; https://nim-lang.org/docs/manual.html; https://docs.hhvm.com/hack/contexts-and-capabilities/introduction.
