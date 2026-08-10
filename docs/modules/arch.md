# frob.arch -- lightweight architectural-smell scanner

One sentence: `frob.arch.analyze_project` walks a source tree through
`frob.lang`'s single grammar-dispatch mechanism and reports structural
smells (long functions, god classes, high coupling, deep nesting, large
files, and cross-file signature-abstraction opportunities) as advisory
`ArchSuggestion`s -- most categories are advisory (nothing here fails a
build for them), but ARCH101 (low-cohesion-class) and ARCH103
(mixed-concern-function) are configured `severity="error"` in this repo's
own `frob.toml` (T-0977/T-0990) and DO fail `frob check` here; other repos
adopting `frob.arch` choose their own severities per category.

## Scope

Python and C/C++ today (whatever `frob.lang.raw_tree` resolves to a
`"python"` or `"cpp"` language label); other `frob.lang`-supported
languages (TypeScript, Rust) parse but are not yet checked -- a
`frob:todo` follow-up, not a silent gap, since `analyze_project` simply
has no `elif language == "..."` branch for them yet.

## Checks

| Category | Signal | Severity |
|---|---|---|
| `long-function` | a function/method body longer than `max_function_lines` AND structurally complex (see below) | warning |
| `god-class` | a class with more than `max_class_methods` methods | warning |
| `high-coupling` | a file with more than `max_local_imports` distinct local module imports (via `frob.lang.extract_imports`/`resolve_local_import`) | suggestion |
| `deep-nesting` | a function whose `if`/`for`/`while`/`try`/`with` nesting exceeds `max_nesting_depth` | suggestion |
| `large-file` | any file longer than `max_file_lines` | info |
| `abstraction-opportunity` | 3+ Python functions across the project sharing the same annotated parameter/return-type signature, EXCLUDING intentional dispatch/validator families (see below) | suggestion |
| `pattern-recommendation` | a strong structural HALLMARK (isinstance chain, state-field chain, telescoping constructor, scattered construction, wrap-and-delegate class, translating-wrapper class, manual callback list) matches a registered `frob.arch._patterns` rule | suggestion |
| `anti-pattern-escape` | a strong structural ANTI-PATTERN (god object, stringly-typed comparison chain, all-trivial-accessor class) matches a registered `frob.arch._patterns` rule | suggestion |
| `lsp-not-implemented-override` (ARCH104, T-0618) | an override raises `NotImplementedError` where the same-file base method is concrete -- written once against the normalized model | warning |
| `lsp-signature-variance` (ARCH105, T-0618) | an override accepts fewer required params, or returns a different annotated type, than its same-file base method -- written once against the normalized model | warning |
| `lsp-strengthened-precondition` (ARCH106, T-0618) | an override adds a guard-clause raise on a shared param the base lacks -- written once against the normalized model | warning |
| `lsp-weakened-postcondition` (ARCH107, T-0618) | an override can return nothing where the base always returns a value -- written once against the normalized model | warning |
| `lsp-noop-override` (ARCH108, T-0618) | an empty-shell override of a value-returning base method -- written once against the normalized model | warning |
| `fat-interface` (ARCH109, T-0619) | an ABC/Protocol-family interface whose resolved same-file implementers are mostly stubbed out -- written once against the normalized model | warning |
| `narrow-client-usage` (ARCH110, T-0619) | a function/method injected with a wide same-file interface that calls only a small fraction of its methods -- written once against the normalized model | suggestion |
| `low-cohesion-class` (ARCH101, T-0616) | a class's field-using methods split into 2+ disjoint field-usage components (LCOM4) -- written once against the normalized model, fires across languages | warning |
| `god-module` (ARCH102, T-0616) | a module's 10+ top-level exports partition into 3+ disjoint naming/usage clusters -- written once against the normalized model | warning |
| `mixed-concern-function` (ARCH103, T-0616) | one function body mixes an I/O call, a string-formatting call, and 2+ of its own decision points -- written once against the normalized model | suggestion |
| `pool-inside-pool` (T-0695) | a process-pool construction reachable alongside a thread-pool/thread construction in the same function | warning |
| `fork-after-threads` (T-0695) | a fork/fork-start-method call reachable after a `Thread(...).start()` on the same function's line order | warning |
| `pipe-wait-deadlock` (T-0695) | a `Popen` with a `PIPE` stream followed by `.wait()` with no `.communicate()` in the function | warning |
| `self-join-deadlock` (T-0695) | a function dispatched as a pool/thread task whose own body calls `.join()`/`.shutdown()`/`.close()` | warning |
| `dip-layering-violation` (T-0620) | an import between two `frob.toml`-declared layers not listed in the declared allow set, or a layered file with unresolvable dynamic-import indirection -- project-wide, resolved imports | warning |
| `no-di-construction` (T-0620) | a method/function (outside `__init__`/`__new__`/a factory) directly constructs a same-file concrete class instead of receiving it via injection -- written once against the normalized model | suggestion |
| `illegal-states-representable` (T-0621) | a bool field runtime-guarded against another field's value inside a method body, instead of modeled as an enum/newtype -- written once against the normalized model | suggestion |
| `primitive-obsession` (T-0621) | a function/method signature with 3+ raw `str`/`int`/`float` params -- written once against the normalized model | suggestion |
| `parse-dont-validate` (T-0621) | a function that guards its one param then returns the SAME unrefined type instead of a refined one -- written once against the normalized model | suggestion |
| `boolean-flag-param` (T-0621) | a public function/method with a bool param it branches on internally -- written once against the normalized model | suggestion |
| `type-dispatch-smell` (T-0617) | an isinstance/type-tag dispatch chain (OCP family) | warning |
| `non-exhaustive-enum-match` (T-0617) | an enum/literal match missing a member with no default arm (OCP family) | warning |
| `unlogged-error-path` (T-0622) | an except/error-return branch with no logging call | warning |
| `unlogged-boundary` (T-0622) | a process/network/file boundary crossing with no logging call | warning |
| `print-as-diagnostic` (T-0622) | a `print`/`console.log`-style call used where a logger call belongs | suggestion |
| `unhandled-result` (T-0623) | a `Result`/fallible-return value neither branched on nor propagated | warning |
| `swallowed-exception` (T-0623) | a caught exception with no re-raise, log, or return-signal | warning |
| `recoverable-error-wrong-signature` (T-0623) | a function that raises for an expected/recoverable condition instead of returning a typed error | suggestion |
| `over-broad-except` (T-0623) | a bare or overly wide `except`/`catch` clause | warning |
| `mutable-default-arg` (T-0624) | a mutable literal (list/dict/set) as a default parameter value | warning |
| `feature-envy` (T-0624) | a method that reads another object's fields/methods far more than its own | suggestion |
| `data-clumps` (T-0624) | the same group of params repeated across 3+ signatures | suggestion |
| `magic-literal` (T-0624) | an unexplained numeric/string literal used as a business-logic constant | suggestion |
| `dead-private-code` (T-0624) | a private symbol with no in-file caller | suggestion |
| `deep-inheritance` (T-0624) | a class hierarchy deeper than a configured bound | suggestion |
| `temporal-coupling` (T-0624) | methods that must be called in an undocumented required order | suggestion |
| `module-dependency-cycle` (T-0625) | a module import cycle (Tarjan's algorithm over `frob.cycle.graph`) | warning |
| `blocking-call-in-async` (T-0696) | a synchronous blocking call reachable from an `async def` | warning |
| `nested-event-loop` (T-0696) | an event loop started from within an already-running event loop | warning |
| `unawaited-coroutine` (T-0696) | a coroutine object created but never awaited | warning |
| `async-zero-awaits` (T-0696) | an `async def` whose body contains no `await` at all | suggestion |
| `sequential-independent-awaits` (T-1027) | 2+ sequential `await`s in one block where no earlier bound name is read by a later one (could run concurrently) | suggestion |
| `lock-order-cycle` (T-0694) | two or more locks acquired in inconsistent order across call paths | warning |
| `lock-identity-unresolved` (T-0694) | a lock object whose identity cannot be statically resolved (fail-closed) | warning |
| `unguarded-shared-write` (T-0697) | a write to module/class-level mutable state reachable from 2+ thread/task dispatch points with no guarding lock | warning |
| `gil-bound-in-threadpool` (T-0698) | CPU-bound work dispatched to a thread pool (GIL-limited) instead of a process pool | suggestion |
| `ipc-overhead-in-processpool` (T-0698) | IO-bound work dispatched to a process pool, paying IPC/pickling overhead for no CPU-bound benefit | suggestion |
| `errors-as-values-recommended` (T-0688) | a function whose may-raise set suggests a typed Result return would suit better than propagating exceptions | suggestion |
| `cpp-noexcept-throws` (T-0687) | a `noexcept` C++ function reached by a may-throw/unresolved-callee call with no enclosing `catch (...)` | error |

All thresholds are `analyze_project` keyword arguments with the defaults
shown in the Public API section below; there is no `frob.toml` table for
`frob.arch` (deliberately -- see below and T-0289's design note in
tickets-archive.md: per-function overrides belong at the code as reasoned
waivers, not a central escape-hatch table).

### `long-function` is complexity-aware (T-0289)

A function LONG but FLAT (linear setup+asserts, a big `match`/`case`
dispatch, a literal dispatch table) is not the smell this rule targets --
only long-AND-complex fires. `frob.arch._python`/`_cpp` compute a cheap
structural-complexity proxy off the existing tree-sitter parse (no new
dependency):

- **max nesting depth** of `if`/`for`/`while`/`try`/`with` control
  structures (the same walk `deep-nesting` already does).
- **cyclomatic proxy**: a count of branch/loop/except/boolean-op nodes
  (`if_statement`, `for_statement`, `while_statement`, `except_clause`,
  `boolean_operator`, `conditional_expression` for python;
  `catch_clause`/`&&`/`||` substituted for C++). `match_statement`/
  `case_clause` (python) and `switch_statement`/`case_statement` (C++)
  are deliberately EXCLUDED -- a big match/case is flat dispatch, not the
  decision complexity this rule targets, and (unlike python's if/elif,
  which folds into one `if_statement` node) each `case_clause` is its own
  tree-sitter node, so counting them would score the canonical flat case
  as maximally complex.

The rule: **flag iff `n_lines > max_function_lines` AND (`max_nesting >=
3` OR `cyclomatic >= 8`)**. Both thresholds are named module constants
(`_LONG_FUNCTION_NESTING_THRESHOLD`, `_LONG_FUNCTION_CYCLOMATIC_THRESHOLD`
in `frob.arch._python`/`_cpp`), not `frob.toml` knobs -- a global
threshold bump is exactly the lazy-developer escape this tool exists to
prevent; see the per-function override below for the honest way to
justify a real exception.

### `abstraction-opportunity` excludes intentional dispatch families (T-0360)

A same-signature group is NOT flagged when it looks like an intentional
dispatch/validator family -- N functions with an identical signature all
registered in / dispatched from one common site (a command table, a
validator runner, an `elif` chain on a tag). There the shared signature IS
the contract that lets the site call them uniformly; extracting a shared
base class or protocol would add ceremony, not remove duplication.

`frob.arch._abstraction._is_dispatch_family` detects this off tree-sitter
STRUCTURE, not raw text (a plain textual "mentioned nearby" signal was
tried first and reviewer-rejected -- see below for why). For every
eligible python file, `_python.collect_file_dispatch_refs` walks its
parsed tree and records every identifier name used in a dispatch-like
syntactic position:

- the callee of a `call` (`name(...)`) -- an `elif`/`match` branch calling
  a handler, or a direct dispatch call;
- a positional or keyword argument of a `call` (`register(name)`,
  `table.append(name)`, `dispatch(cmd, handler=name)`) -- a registration
  call;
- a value inside a `dictionary` literal's `pair` (`{"scan": name}`) -- a
  command table;
- an element of a `list`/`set`/`tuple` literal (`[name_a, name_b]`) -- a
  dispatch table built as a sequence.

A bare textual mention -- an import, a docstring, a name in an `__all__`
list of STRING literals -- matches none of these shapes and does not
count. Two members of a group are "linked" if some single eligible file's
dispatch-reference set contains both their names. A group is treated as
an intentional family, and suppressed, when every member is linked to at
least one sibling this way (a large family MAY be served by more than one
such site, e.g. two separate command tables). A group with a member linked
to no one else has no such site for that member and still flags as a real
opportunity.

**Corpus exclusions (defense-in-depth, T-0360).** Two file categories are
excluded from the dispatch-reference corpus entirely, on top of the
structural-only extraction above:

- `__init__.py` files (`frob.arch._is_init_file`) -- a package's re-export
  module has nothing but imports and an `__all__` string list, which the
  structural extraction already ignores, but it is excluded outright as a
  belt-and-suspenders guard given how central re-export modules are to
  this false-suppression risk.
- test files (`frob.excludes.is_test_file`) -- a test file's own calls
  into the functions it tests (`assert normalize_alpha("x") == ...`) ARE
  real `call` nodes and would otherwise satisfy the structural check,
  which is exactly the second false-suppression path an early version of
  this detector had: three unrelated same-signature functions imported
  and called from one test module looked, structurally, just like a
  dispatch table. Excluding test files from the corpus (not just from the
  signature/finding side, which T-0359 already did) closes that path.

These two exclusions are the fix for a reviewer-caught defect in an
earlier version of this detector, which linked names on RAW TEXT
proximity ("both names appear >=2 times in one file") instead of
dispatch-shaped structure -- a re-export list or a test's assertion calls
each mention a name at least twice (once imported, once used/listed) and
fully suppressed genuine findings with zero real dispatch signal. The
structural extraction plus these two corpus exclusions are what makes
`test_init_reexport_does_not_suppress` and
`test_test_file_co_mention_does_not_suppress` (`tests/unit/test_arch.py`)
pass.

Because `abstraction-opportunity` is one of the advisory,
unwaivable-channel categories (`frob.gates._waive._unwaivable_channel_rules`,
T-0101), a `frob:waive abstraction-opportunity reason="..."` directive
can never reach it -- disposition for a real finding is either fix it (add
the shared abstraction) or teach the detector to recognize a legitimate
pattern it is currently missing, never a code-comment waiver.

### `abstraction-opportunity` requires signature-specificity or body-similarity, not a bare shared signature (T-0370)

A shared signature ALONE is not evidence of a missing abstraction. Python
has few primitive types, so dozens of semantically-unrelated functions
routinely collide on the same over-generic shape purely by coincidence --
every `run(config: AppConfig) -> None` per-command entrypoint across the
runner modules (39, before this ticket), every `(str) -> str`
name-munging helper (31), every `(str) -> bool` predicate. You cannot
factor N unrelated functions into one shared abstraction just because they
happen to take the same primitive types; T-0360's dispatch-family
suppression caught the intentional-registry case but left this
coincidental-collision residue untouched.

`frob.arch._abstraction._check_abstraction_opportunities` now requires one of
two discriminators before flagging a same-signature group (after the
T-0360 dispatch-family exclusion above still runs first):

- **Signature-specificity** (`_signature_is_specific`): the shared
  signature carries at least one type outside `_GENERIC_TYPE_NAMES` (the
  ubiquitous primitives -- `str`, `int`, `bool`, `float`, `bytes`, `None`,
  `Path`, `object`, `Any`, bare containers, `Optional`/`Union`/`Callable`,
  and `AppConfig` -- the App/AppConfig pattern's uniform CLI-dispatch
  contract, shared by design, not by coincidence). A signature carrying a
  real domain type (`TicketStore`, `Violation`, `GraphSnapshot`, `Result[...,
  VetError]`) is specific enough on its own; the WHOLE group is reported,
  since the signature itself is the evidence.
- **Body-similarity** (`_near_duplicate_cluster`): when the signature is
  generic, the group is flagged only if a SUBSET of its members has
  near-duplicate bodies. Each function's body is normalized the same way
  the dup scanner does (`frob.dup._legacy_py._collect_locals_py` /
  `_serialize_py_body` -- locals alpha-renamed, string/numeric literals
  collapsed to `_S_`/`_N_`), then compared pairwise with
  `difflib.SequenceMatcher.ratio()`; two members are near-duplicate at
  `ratio >= _BODY_SIMILARITY_THRESHOLD` (0.9). Bodies under
  `_BODY_MIN_TOKENS` (8) normalized tokens never participate -- a
  same-shape one-liner (`return self._x`) collides with unrelated
  one-liners by coincidence, not logic, at that length. Only the
  near-duplicate SUBSET is reported (not the full generic-signature
  group) -- a group of 30 unrelated functions with one genuinely
  duplicated pair is reported as that pair, not misrepresented as 30
  functions sharing logic.

A generic-signature group with neither an above-threshold specific type
nor a near-duplicate body subset is not flagged at all. This is what
dropped the residue from 67 findings to the genuinely extractable
families: the 39-member `(AppConfig) -> None` and 31-member `(str) ->
str` groups vanished entirely (no near-duplicate bodies among their
members), while e.g. a literal-duplicate `_has_done_report` defined twice
still flags (found via body-similarity despite its generic `(str) ->
bool` signature). Specific-signature families sharing a project-wide
domain-type return convention (see the check-registry/gate-rule-builder/
tool-result-builder exclusions below) are excluded from this path
entirely, regardless of body similarity -- the signature-specificity
check alone would otherwise re-flag them every time.

### `abstraction-opportunity` excludes intentional detector/gate/check-stage registries by return-type or name convention (T-1112/T-1141/T-1144)

Three more same-signature groups are excluded even when signature-
specificity (above) would otherwise flag them in full, because the
package's own established interface convention -- not a coincidence --
is what put them there:

- **`frob.arch`'s own `check_*`/`run_*_checks` detector registry**
  (`_is_check_registry_family`, T-1112, filed from T-1084): every
  detector across `_python.py`/`_rust.py`/`_typescript.py`/
  `_async_hazards.py` and siblings implements the SAME
  `(NormalizedModule) -> list[ArchSuggestion]` registry contract, plus
  each family's own `run_*_checks` aggregator. NAME-based (`_CHECK_
  REGISTRY_NAME_RE`): every member's bare name must match `check_*` or
  `run_*_checks`.
- **`frob.gates`'s own gate/rule-builder convention**
  (`_is_gate_rule_builder_family`, T-1141, filed from T-1114): every
  gate function (`*_gate`) and the rule-builder helpers it dispatches to
  return one of `Violation`/`list[Violation]`/`tuple[Violation, ...]` --
  `Violation` is `frob.gates`'s own domain type, so any function
  returning one of these shapes participates in the same contract by
  construction. RETURN-TYPE-based (`_GATE_RULE_BUILDER_RETURN_TYPES`),
  not name-based, since gate/rule-builder names share no fixed
  prefix/suffix the way `check_*`/`run_*_checks` do.
- **`frob.process`/`frob.check`'s own check-stage-runner convention**
  (`_is_tool_result_builder_family`, T-1144, filed from T-1124): every
  check-stage runner and tool-result builder across `src/frob/check/**`
  and `src/frob/process/parsers/**` returns `ToolResult` or `ToolResult |
  None`, the same shape of argument as the gate/rule-builder exclusion
  above, applied to `frob.process`'s own domain type. T-1144's
  investigation confirmed the genuine body-level duplication in this
  area (`_opt_in_deploy_stage_result`, `_missing_tool_result` forwarding
  to `tool_unavailable_result`) was already extracted by T-1124 -- the
  4 remaining ToolResult-shaped groups (24 members) were purely this
  convention-shape false positive, evidenced by `parse_junit_xml` (real
  XML-parsing logic) sharing a signature with three trivial synthetic-
  result builders purely because its `tool` parameter has a default.

All three are structural/name discriminators over the shared signature
(mirroring `_is_dispatch_family`/`_is_language_parity_family` above),
never raw text proximity, and are checked after the T-0360 dispatch-
family exclusion and before the signature-specificity/body-similarity
checks -- a group excluded here never reaches that path at all.

### Design-pattern recommender: `pattern-recommendation` / `anti-pattern-escape` (T-0332/T-0605)

<a id="design-pattern-registry"></a>
<!-- frob:describes src/frob/arch/_patterns.py::_PatternRuleSpec -->
<!-- frob:describes src/frob/arch/_patterns.py::PATTERN_REGISTRY -->
<!-- frob:describes src/frob/arch/_patterns.py::new_construction_accumulator -->

`frob.arch._patterns` is a positive complement to the smell categories
above: instead of only flagging a structural problem, it maps a strong
structural HALLMARK to a recommended GoF/modern PATTERN, or a detected
ANTI-PATTERN to a concrete ESCAPE route. Both directions are pure
ADVISORY findings -- `severity="suggestion"`, never an error, and both
categories stay on the unwaivable advisory channel every other
`frob.arch` category is on (`frob.gates._waive._unwaivable_channel_rules`,
T-0101) -- forcing a pattern is itself over-engineering, so there is
nothing here a build can fail on.

Design constraints, in force for every registry row:

- **STRONG-HALLMARK-ONLY / high precision.** Every detector requires a
  multi-occurrence structural signal (three or more branch arms, call
  sites, or delegating methods -- see each rule's threshold below), never
  a single instance. A noisy recommender trains users to ignore it, and
  the recommender must never fire on code that is already simple.
- **Pairs with the smell detectors, not a second walk.** `god-object`
  reuses the already-computed `god-class` findings (`_check_god_classes`)
  and emits a companion `anti-pattern-escape` suggestion at the same
  location instead of re-walking the tree -- one detector, two outputs:
  "violates OCP" and "consider decomposing by responsibility".
- **Names the FORCE and a concrete sketch.** Every finding's `message`
  states the tension the pattern resolves; `detail` gives a one-line
  refactor sketch -- never a bare "use Strategy".
- **`_PatternRuleSpec`** (a frozen dataclass) is the registry's row shape:
  `rule_id`, `direction` (`"pattern"` or `"escape"`), `hallmark`,
  `response`, `force`, `sketch`, `languages`. `PATTERN_REGISTRY` is the
  full tuple of rows, independent of the detector code that matches each
  one, the same way `frob`'s other registries separate data from
  matching logic.

Implemented registry rows (each backed by a real tree-sitter detector in
`frob.arch._patterns`, reusing `frob.arch._python`'s shared function/class
walk helpers):

| Rule id | Direction | Hallmark | Response |
|---|---|---|---|
| `type-switch` | pattern | an `elif` chain of 3+ `isinstance(x, T)` checks on the same `x` | Strategy / polymorphic dispatch |
| `state-field-chain` | pattern | an `elif` chain of 3+ arms comparing the same `self.<state-like attribute>` (name containing `state`/`status`/`mode`/`phase`/`stage`) against a string literal | State machine (State pattern) |
| `telescoping-ctor` | pattern | an `__init__` with 6+ parameters, 4+ of them defaulted | Builder |
| `scattered-construction` | pattern | the same concrete class constructed directly (bare `ClassName(...)` call) across 3+ distinct files | Factory / dependency injection |
| `wrap-delegate` | pattern | a class storing one constructor-parameter object as `self.<attr>`, with 3+ methods whose entire body is a same-name pass-through call to that attribute | Decorator |
| `interface-translate` | pattern | (T-0605) a class storing one constructor-parameter object as `self.<attr>`, with 3+ methods whose entire body is a single call to a DIFFERENTLY-named method on that attribute | Adapter |
| `manual-callback-list` | pattern | (T-0605) a class initializing `self.<attr> = []` in `__init__`, with a distinct method appending to it and a distinct method iterating it to call each element | Observer |
| `god-object` | escape | a class already flagged `god-class` (more methods than `max_class_methods`) | SRP decompose |
| `stringly-typed` | escape | a plain identifier (never `self.<attr>` -- that is `state-field-chain`'s territory) compared via `==` against 4+ distinct string literals across one `elif` chain | newtype (Enum / typed value object) |
| `anemic-accessors` | escape | (T-0605) a class with 3+ non-`__init__`, non-dunder methods where EVERY one is a trivial single-statement getter or setter, no real behavior anywhere | move behavior to data (rich domain model) |
| `dataclass-boilerplate` | pattern | (T-0849) an undecorated class whose ONLY method is `__init__`, itself doing nothing but `self.<attr> = <attr>` for 3+ same-named parameters | `@dataclass` |
| `manual-decorator-wrap` | pattern | (T-0849) 3+ module-level `def f(...): ...` definitions each immediately followed by `f = wrapper(f)` reassignment | decorator syntax (`@wrapper`) |

`wrap-delegate` and `interface-translate` are disjoint PER-METHOD ONLY
(a same-name delegating method can never also count as a translating
one), NOT per-class: a class that mixes a same-name-delegating subset
with a separate 3+-method translating subset legitimately fires BOTH
`wrap-delegate` (Decorator) and `interface-translate` (Adapter) --
two independent findings about two disjoint method groups, not a
contradictory claim about the whole class (reviewer round 1, T-0605;
see `test_mixed_delegate_and_translate_methods_fires_both`).

`type-switch`/`state-field-chain` and `stringly-typed` are deliberately
disjoint on the same AST shape (an `elif` chain of equality/isinstance
comparisons): `type-switch` requires an `isinstance()` call,
`state-field-chain` requires the LHS to be a `self.<attribute>` access
with a state-lifecycle name hint, and `stringly-typed` requires the LHS to
be a bare identifier (no `self.` attribute access) -- so the same
comparison node can never satisfy more than one rule.

`scattered-construction` runs as a cross-file pass, mirroring
`abstraction-opportunity`'s accumulate-then-check shape:
`_collect_file_constructions` accumulates each file's Capitalized bare-
callee constructions into a `new_construction_accumulator()`-created dict
(class name -> set of files), excluding common builtin exception/
collection type names, and `_check_scattered_construction` flags any
class constructed from 3+ distinct files after every file has been
walked.

**T-0605 phase 2.** T-0332's plan enumerated 13 rows and shipped 7; T-0332
deferred 6 for precision reasons (`incompatible-interface-bridging ->
Adapter`, `expensive-object-reuse -> Flyweight/pool`, `manual-callback-
list -> Observer`, `anemic-domain-model -> move behavior to data`,
`poltergeist/lava-flow -> delete`, `sequential-coupling -> explicit
state`). T-0605 resolved each on its own merits instead of shipping a
uniform pass: 3 got real, precision-checked detectors (`interface-
translate`, `manual-callback-list`, `anemic-accessors`, all in the table
above), and 3 were recorded as reasoned NOT-CHECKABLE rather than shipped
imprecise (the ticket's own noise mandate: an imprecise recommender
trains users to ignore the advisory channel, which is worse than honest
silence):

- **Flyweight/pool** -- no single-file structural signal distinguishes
  "expensive to construct, should be shared/pooled" from an ordinary loop
  building N legitimately different objects without value/dataflow
  analysis this package does not have.
- **Poltergeist/lava-flow** -- the architecture-check-catalog itself notes
  poltergeist is "dup of Middle Man, at extreme" (its degenerate case is
  not distinguishable from a small, well-designed wrapper without knowing
  whether callers actually need it elsewhere), and lava-flow ("nobody
  dares remove it") requires whole-program reachability/usage evidence, a
  different kind of analysis (dead-code/call-graph) than a per-file
  structural walk provides.
- **Sequential coupling** -- the catalog notes it is "dup of Connascence
  of Execution"; the closest structural proxy (a private flag set by one
  method, checked-and-raised by another) is indistinguishable from
  ordinary guard-clause precondition validation without tracking actual
  call-order violations across real callers -- again a call-graph-class
  investment, not a bigger detector.

See `frob.arch._patterns`'s module docstring and `tickets.md`'s T-0605
Done report for the full per-pattern reasoning. `docs/design/registry/
patterns.yaml`'s corresponding rows (`GOF-ADAPTER`, `GOF-FLYWEIGHT`,
`GOF-OBSERVER`, `PAT-TRAP-20-ANEMIC-DOMAIN-GOD-OBJECT-LAVA-FLOW`) all
correctly stay `out_of_scope:advisory-design-pattern-recommendation`
regardless of whether a detector exists for their hallmark -- this
registry tracks whether a row is subject to enforceable GATE tracking,
not whether `frob.arch` happens to implement an advisory recommender for
it (T-0332's own precedent: its 7 shipped detectors' rows carry the
identical disposition).

**T-0849 phase 3.** T-0605 closed having worked its own 6 mandated rows;
41 other `patterns.yaml` rows (9 `DDD-II-*` DDD building blocks, 24
`RELEASEIT-*` stability anti-patterns/patterns, 8 `PYIDIOM-*` Python
idioms) had been re-pointed to `deferred:T-0849` when T-0605 closed (a
deferral to a closed ticket is not a real deferral). T-0849 worked or
dispositioned every one, and shipped 2 new real detectors in the process
(`dataclass-boilerplate`, `manual-decorator-wrap`, both in the table
above):

- **`DDD-II-*` (9 rows: Layered Architecture, Entities, Value Objects,
  Domain Events, Services, Modules, Aggregates, Repositories, Factories)**
  -- these are Evans's own building-block VOCABULARY, not a described
  structural hallmark the way `_patterns.py`'s registry rows are. "Is this
  class actually an Entity vs. a Value Object" is a domain-semantic
  judgment (does it have a persistent identity distinct from its
  attributes?) no single-file structural signal can answer without
  fabricating a claim -- the identical reasoning `_check_dataclass_
  boilerplate`'s own docstring and this doc's Flyweight/pool entry above
  already applies to "equivalent, expensive to construct" without
  value/dataflow analysis. `patterns.yaml`'s own sibling rows in the same
  Evans catalog (`DDD-I-*`, `DDD-III-*`) are already `out_of_scope` for
  the same reason; the 9 `DDD-II-*` rows now match.
- **`RELEASEIT-*` (24 rows: 12 stability anti-patterns, 12 stability
  patterns -- timeouts, circuit breaker, bulkheads, chain reactions,
  cascading failures, etc.)** -- these are runtime/distributed
  reliability properties (a timeout that fires under real network
  latency, a circuit breaker that trips under real failure load, a
  bulkhead that isolates real resource pools) that no per-file structural
  walk over one language's AST can observe; they require watching actual
  request/response behavior across a running distributed system, a
  different kind of analysis than this package performs anywhere. `RELEASEIT-
  PAT-TIMEOUTS` overlaps `strata`'s REL2xx timeout-obligation family
  (`docs/design/system-design-corpus.md`) at the concept level, but that
  is a config/design-graph proof over declared obligations, not a
  structural code detector `frob.arch` could add here -- the
  `patterns.yaml` row records this cross-reference rather than inventing
  a duplicate, weaker arch check.
- **`PYIDIOM-*` (8 rows: Context Manager, Descriptor Protocol, Duck
  Typing Protocol, Iterator Protocol, Decorator Syntax, Sentinel Object,
  Mixin, Dataclass)** -- 2 of the 8 got real, precision-checked detectors
  this pass (`PYIDIOM-DATACLASS` -> `dataclass-boilerplate`, `PYIDIOM-
  DECORATOR-SYNTAX` -> `manual-decorator-wrap`); the other 6 stay
  NOT-CHECKABLE:
  - **Context Manager** -- the hallmark (a manual `try/finally` block
    calling `.close()`/`.release()` on the same object across 3+ sites)
    is real in principle, but distinguishing a resource-cleanup call from
    an ordinary `finally`-block side effect without tracking the object's
    actual type/protocol would need cross-file type inference this
    package does not have; a name-based heuristic (`.close()`) risks
    firing on unrelated methods that happen to share the name.
  - **Descriptor Protocol** -- the hallmark is 3+ near-identical `@property`
    get/set pairs differing only by attribute name; detecting "near-
    identical" honestly needs a body-similarity comparison this package's
    tree-sitter walks do not perform anywhere yet (a bigger investment
    than a bigger detector, not a smaller one).
  - **Duck Typing Protocol** -- the hallmark is "code accepts anything
    with the right methods instead of checking a type," which is the
    ABSENCE of a check, not the presence of a structural shape a walk can
    match against.
  - **Iterator Protocol** -- the hallmark ("a method that materializes and
    returns a full list purely so callers can loop over it") is
    indistinguishable from a method that legitimately needs to return a
    list for other reasons without tracking every call site's actual
    usage.
  - **Sentinel Object** -- the hallmark ("`None` is overloaded as both
    'no value' and a valid domain value") requires knowing whether `None`
    is ever a legitimate domain value for the attribute in question, a
    domain-semantic judgment no structural check can make.
  - **Mixin** -- the hallmark (3+ unrelated classes independently
    duplicating an identical small method set) is a cross-class
    duplication proxy at least as complex as the Poltergeist/lava-flow
    call-graph investment above, not a bigger single-file detector.

See `frob.arch._patterns`'s module docstring and `tickets.md`'s T-0849
Done report for the full per-pattern reasoning.

### OCP checks: `type-dispatch-smell` / `non-exhaustive-enum-match` (T-0617)

<a id="ocp-checks"></a>
<!-- frob:describes src/frob/arch/_ocp.py::_check_type_dispatch_smell -->
<!-- frob:describes src/frob/arch/_ocp.py::_check_non_exhaustive_enum_match -->

`frob.arch._ocp` is the OCP (Open/Closed Principle) slice of T-0330's
SOLID catalog (the ARCH1xx family). Both checks stay on the same
unwaivable advisory channel every other `frob.arch` category is on
(`frob.gates._waive._unwaivable_channel_rules`) until a future ticket wires a
real ARCH1xx gate the way `ARCH001` already exists for `long-function`;
every finding already carries `symref`/`metric` so that wiring is a
gate-side addition, not a re-instrumentation of these checks.

- **`type-dispatch-smell`.** An `elif` chain of 3+ `isinstance(x, T)`
  checks on the same `x` is read as an OCP violation: adding a new type
  means editing this function instead of adding a new type. This is the
  EXACT structural signal T-0332's design-pattern recommender
  (`frob.arch._patterns`) already detects as the `type-switch` hallmark
  (recommending Strategy) -- per the ticket's "one detector, two outputs"
  mandate, `_ocp` does not re-walk the tree or re-derive the isinstance-
  chain match; it calls the shared generator `frob.arch._patterns.
  iter_type_switch_chains` (factored out of `_check_type_switch` for this
  reuse) and reads the identical chain as an OCP smell. The same source
  chain fires both `pattern-recommendation` and `type-dispatch-smell`.
- **`non-exhaustive-enum-match`.** A `match`/`case` over a variable
  statically tied to a locally-defined `Enum`-family class (`Enum`,
  `IntEnum`, `StrEnum`, `Flag`, `IntFlag`), with no wildcard/capture
  default arm (`case _:` or a bare-name capture), that omits at least one
  of that enum's members. PRECISION DISCIPLINE (fail toward silence):
  this only fires when the enum class is defined in the SAME file and
  EVERY case pattern is a plain `EnumClass.MEMBER` value pattern (or a
  `|`-union of same) naming that exact class -- a sequence/mapping/class
  pattern with arguments, a qualifier naming some other class, or an
  enum not locally resolvable makes the match's exhaustiveness
  unverifiable from this file alone, and the check silently skips it
  rather than risk a false positive.

T-0972: `_check_non_exhaustive_enum_match`'s own `sorted(missing)`
message-formatting call picked up a reasoned `frob:waive PERF004` (the
missing-member set differs per match, nothing to hoist) -- no behavior
change.

### LSP checks: `lsp-not-implemented-override` / `lsp-signature-variance` / `lsp-strengthened-precondition` / `lsp-weakened-postcondition` / `lsp-noop-override` (T-0618)

<a id="lsp-checks"></a>
<!-- frob:describes src/frob/arch/_solid.py::check_override_raises_not_implemented -->
<!-- frob:describes src/frob/arch/_solid.py::check_override_signature_variance -->
<!-- frob:describes src/frob/arch/_solid.py::check_override_strengthened_precondition -->
<!-- frob:describes src/frob/arch/_solid.py::check_override_weakened_postcondition -->
<!-- frob:describes src/frob/arch/_solid.py::check_noop_override -->
<!-- frob:describes src/frob/arch/_solid.py::run_lsp_checks -->

`frob.arch._solid` (EPIC T-0330's ARCH1xx LSP/Liskov family, T-0618) is
written ONCE against the T-0609 normalized model
(`frob.arch._normalized.NormalizedModule`), following `frob.arch._srp`'s
precedent (T-0616): every check below fires identically for every
`LanguageAdapter` output with no per-language branch in the check itself.
All five categories stay on the same unwaivable advisory channel every
other `frob.arch` category is on (`frob.gates._waive._unwaivable_channel_rules`)
until a future ticket wires a real ARCH1xx gate the way `ARCH001` already
exists for `long-function`; every finding already carries `symref` (and
`metric` where there is a natural count) so that wiring is a gate-side
addition, not a re-instrumentation of these checks. `analyze_project`
dispatch wiring is out of this ticket's scope, matching T-0616's own
disclosed cut (see its "Wiring" note above) -- `run_lsp_checks` is the
single entry point a future wiring ticket calls per parsed file.

**Base<->override linkage.** `NormalizedFunction.overrides` (T-0609) is
only populated by adapters for languages with an explicit override
keyword/annotation (Kotlin's `override` modifier, TypeScript's `override`
modifier, Rust's trait-impl methods) -- python has none, so
`PythonAdapter` never sets it. Rather than leave python's LSP checks
permanently blind, `_solid.py` resolves the linkage itself,
PRECISION-DISCIPLINE style matching `frob.arch._ocp`'s fail-toward-silence
posture (`_iter_override_pairs`): a class's `bases` (as written in
source) are looked up against every OTHER class defined in the SAME
`NormalizedModule`; a base class defined in another file, or not
resolvable from this file alone, makes the pair unresolvable and it is
silently skipped rather than risked as a false positive. A method name
shared between a class and a same-file base class IS the override
relationship for every check below.

| Category | ARCH id | Signal | Severity |
|---|---|---|---|
| `lsp-not-implemented-override` | ARCH104 | an override raises `NotImplementedError`/`NotImplemented` while its same-file base method does NOT raise the same type anywhere in its own body | warning |
| `lsp-signature-variance` | ARCH105 | an override accepts fewer required (no-default) params than the base, OR its annotated return type differs from the base's annotated return type | warning |
| `lsp-strengthened-precondition` | ARCH106 | an override adds a guard-clause raise (`if <cond mentioning a shared param>: raise ...`) on a param the base also declares, that the base's own body has no matching guard for | warning |
| `lsp-weakened-postcondition` | ARCH107 | the same-file base method always returns a real value on every return path, but the override has at least one bare `return`/`return None` path | warning |
| `lsp-noop-override` | ARCH108 | an override's OWN body has no branches/loops/calls/field-accesses/raises/catches and no value-returning `return`, while the same-file base method DOES return a value on at least one path | warning |

**`lsp-not-implemented-override` (ARCH104, `check_override_raises_
not_implemented`).** A base method that is itself abstract-shaped (also
raises `NotImplementedError`/`NotImplemented` somewhere in its own body --
e.g. a hand-rolled ABC method without `@abstractmethod`) is not flagged:
the base already documents "override me", so the override doing exactly
that is not a violation. Only an override whose CONCRETE base does not
raise the same exception type is flagged.

**`lsp-signature-variance` (ARCH105, `check_override_signature_
variance`).** Required-param-count comparison excludes a leading
`self`/`this`/`cls` receiver so a method-vs-method comparison is apples
to apples regardless of language convention; a narrower override
(`metric` carries the required-param deficit) is flagged and the
return-type half is skipped for that pair (one variance finding per pair
is enough signal). The return-type half only compares when BOTH sides
carry an annotated return type -- an unannotated type on either side is
not resolvable, so that half fails toward silence rather than guessing.

**`lsp-strengthened-precondition` (ARCH106, `check_override_
strengthened_precondition`).** The guard-clause proxy is intentionally
coarse (line-adjacency, not full data flow, matching `_ocp`'s syntactic-
proxy posture): a `NormalizedBranch` whose `condition_text` mentions a
shared param, with a `raise` at or within two lines of the branch's own
line, reads as `if <cond>: raise ...`. A guard present on BOTH the base
and the override for the same param is not flagged -- the precondition
is inherited, not strengthened; `metric` carries the count of newly
strengthened params.

**`lsp-weakened-postcondition` (ARCH107, `check_override_weakened_
postcondition`).** "Always returns a value" is a syntactic proxy: every
`return` statement directly in the function's OWN body (not counting
nested functions) carries a non-`None` value, AND there is at least one
such return. A function with zero returns makes no such promise and is
never treated as the base side of this check.

**`lsp-noop-override` (ARCH108, `check_noop_override`).** The "empty
shell" test requires the override to have NO structural events at all
(branches/loops/calls/field-accesses/raises/catches) and either no
returns or only bare/`None` returns -- a `pass`-only body, or a body that
is exactly `return`/`return None`, both read as no-op; any real body
event (even a single call) takes the override out of this check
entirely, since a real proxy this coarse would rather miss a subtler
no-op than flag a legitimate short override.

**`run_lsp_checks(module) -> list[ArchSuggestion]`** runs all five above
against one `NormalizedModule` and returns the combined findings,
mirroring `frob.arch._srp.run_srp_checks`'s convention.

T-0972: `check_override_strengthened_precondition`'s own
`sorted(new_guards)` message-formatting call picked up a reasoned
`frob:waive PERF004` (the guard set differs per override, nothing to
hoist) -- no behavior change.

### ISP checks: `fat-interface` / `narrow-client-usage` (T-0619)

<a id="isp-checks"></a>
<!-- frob:describes src/frob/arch/_solid.py::check_fat_interface -->
<!-- frob:describes src/frob/arch/_solid.py::check_narrow_client_usage -->
<!-- frob:describes src/frob/arch/_solid.py::run_isp_checks -->

`frob.arch._solid` (EPIC T-0330's ARCH1xx ISP family, T-0619) shares its
module with the LSP checks above -- both are written ONCE against the
T-0609 normalized model, and ISP's fat-interface check directly reuses
LSP's no-op/not-implemented "stub body" tests (`_is_stub_method` composes
`_NOT_IMPLEMENTED_EXCEPTIONS` and `check_noop_override`'s empty-shell
predicate) rather than re-deriving them. Both categories stay on the same
unwaivable advisory channel every other `frob.arch` category is on; no
real ARCH1xx gate is wired in this ticket's scope either -- `run_isp_
checks` is the entry point a future wiring ticket calls per parsed file.

| Category | ARCH id | Signal | Severity |
|---|---|---|---|
| `fat-interface` | ARCH109 | a same-file `ABC`/`Protocol`-family interface (4+ methods) with 2+ resolvable same-file implementers whose AGGREGATE (interface-method, implementer) override slots are 50%+ stub bodies | warning |
| `narrow-client-usage` | ARCH110 | a function/method with a same-file-typed parameter (4+ method interface) that calls at most 34% of that interface's methods on the parameter (and at least one) | suggestion |

**`fat-interface` (ARCH109, `check_fat_interface`).** "Interface-marked"
means a class whose `bases` (as written in source) include one of python's
own ABC/Protocol conventions (`ABC`, `abc.ABC`, `ABCMeta`, `abc.ABCMeta`,
`Protocol`, `typing.Protocol`) -- languages with an explicit interface/
trait keyword instead surface it via `NormalizedClass.bases` the same way
once an adapter maps that keyword onto a base name (no adapter changes are
in this ticket's scope). Implementers are resolved the same same-file-only
way `_iter_override_pairs` resolves LSP's base<->override pairs: only a
class in the SAME `NormalizedModule` naming the interface as a base counts.
The stub ratio (`_is_stub_method`: raises `NotImplementedError`/
`NotImplemented`, OR is a structurally empty shell -- no branches/loops/
calls/field-accesses/catches and no value-returning `return`) is
**measured over the whole resolved-implementer pool combined, not per
implementer** (per the ticket's own "not per-class" framing): every
(interface-method, implementer) pair that IS overridden counts as one
slot; a name the implementer never overrides at all is not resolvable and
is skipped, not counted as either implemented or stubbed. `metric` carries
the raw stub-slot count; `symref` is the interface's own class name.

**`narrow-client-usage` (ARCH110, `check_narrow_client_usage`).** A
"wide interface" candidate is any same-file class with at least
`NARROW_CLIENT_MIN_INTERFACE_METHODS` (4) methods -- unlike
`fat-interface`, no `ABC`/`Protocol` base marker is required, since a
narrow client can be injected with any concrete wide class just as
easily. A candidate client is a function/method with a parameter whose
annotated `type` text names one of those same-file classes; usage is read
straight off `NormalizedCall.callee`'s dotted `<param>.<method>` text for
calls inside the client's OWN body (not nested functions). A client
calling ZERO of the interface's methods on the parameter is a different
smell (dead/unused parameter) and is deliberately not flagged here --
only a NON-ZERO but small (`NARROW_CLIENT_MAX_USED_FRACTION`, 34%) slice
counts as "narrow". `metric` carries the unused-method count (interface
size minus the number actually called).

**`run_isp_checks(module) -> list[ArchSuggestion]`** runs both checks
above against one `NormalizedModule` and returns the combined findings,
mirroring `run_lsp_checks`'s convention.

### DIP layering contract: `dip-layering-violation` (T-0620)

<a id="dip-layering-contract"></a>
<!-- frob:describes src/frob/arch/_layering.py::LayeringConfig -->
<!-- frob:describes src/frob/arch/_layering.py::LayeringConfig.layer_for -->
<!-- frob:describes src/frob/arch/_layering.py::load_layering_config -->
<!-- frob:describes src/frob/arch/_layering.py::check_layering_violations -->

`frob.arch._layering` (EPIC T-0330's ARCH1xx DIP family, T-0620) is a
project-wide check, not a per-file `NormalizedModule` one -- a layering
contract is a claim about the whole import graph, not one file's shape.
It stays on the same unwaivable advisory channel every other `frob.arch`
category is on; no real ARCH1xx gate is wired in this ticket's scope
either (`check_layering_violations` is a library entry point a future
wiring ticket calls, same as `run_srp_checks`/`run_lsp_checks`/
`run_isp_checks`).

**Config schema (`[arch.layering]` in `frob.toml`).** Import-linter
style: named layers plus an explicit allowed-edge set, NOT the
"higher layer may import any lower layer" convention some tools default
to -- every cross-layer edge must be named explicitly or it is a
violation, matching the ticket's "declared allowed-module-dependency
graph ... layers + allowed edges" framing.

```toml
[arch.layering.layers]
app = ["src/frob/app"]
lang = ["src/frob/lang"]

[arch.layering.allow]
app = ["lang"]
lang = []
```

- `layers` maps a declared layer NAME to the repo-relative path prefixes
  (POSIX-style, no leading `/`) that belong to it. A file belongs to the
  layer whose prefix its relative path starts with; if more than one
  prefix matches, the LONGEST wins (`LayeringConfig.layer_for`). A file
  matching no declared prefix belongs to no layer and is never scanned
  or targeted by this check -- the contract only covers what it
  explicitly names.
- `allow` maps a layer name to the list of OTHER layer names it may
  import from. An edge from layer A to layer B where B is not in
  `allow[A]` is a violation; an edge within the SAME layer is never a
  violation regardless of `allow`.
- A missing `frob.toml`, missing `[arch.layering]` table, or malformed
  config (`load_layering_config`) means "nothing declared" -- the check
  has nothing to enforce, not an error, same posture as
  `frob.app.config.load_arch_config`.

This repo's own `frob.toml` carries a real, minimal worked example (not
wired into `frob check` yet, so inert today): `src/frob/lang` is a leaf
parsing-utility layer nothing else in this repo may import BACK from,
while `src/frob/app` (the CLI/orchestration layer) may depend on it.

**Resolved, not surface, imports (adversarial-hardening note).** A raw
import edge under-counts real coupling two ways this check addresses:

1. **Re-export resolution** (`_resolve_reexports`). Importing a package
   `__init__.py` that itself re-exports names from a submodule (`from
   .sub import X`) really couples the importer to `.sub`, not just to
   the package boundary. One bounded hop: `_resolve_reexports` reads the
   target `__init__.py`'s OWN local imports and adds those as
   additional edges from the original importer. Not chased further (an
   `__init__.py` re-exporting from another `__init__.py` stops there) --
   a bounded, terminating scan rather than a full transitive closure.
2. **Fail-closed on dynamic indirection.** A layered file containing
   `importlib.import_module(`/`__import__(` (`_has_dynamic_import`) can
   reach any module at runtime -- this scan cannot prove its real import
   set from static imports alone. Rather than silently passing (imports
   it does not statically declare are invisible), such a file is
   flagged as its own `dip-layering-violation` finding, distinct from
   any specific edge.

**`check_layering_violations(root, config) -> list[ArchSuggestion]`**
walks every python file under `root` belonging to a declared layer
(`frob.excludes.iter_files`/`is_excluded`, same exclusion posture every
other project-wide walk in this codebase uses), resolves its imports via
`frob.lang.extract_imports`/`resolve_local_import` -- the SAME pair
`frob.app.cycle_runner._build_graph` already calls for cycle detection,
reused rather than re-derived -- plus `_resolve_reexports`, and flags
every resolved edge landing in a declared layer not present in the
source layer's `allow` list. Per-file scan errors (T-1022) are caught at
each file rather than aborting the whole walk: an unresolvable path is
logged at debug level and skipped, so one bad file cannot hide layering
findings in every other file under `root`.

### No-DI construction smell: `no-di-construction` (T-0620)

<a id="no-di-construction-smell"></a>
<!-- frob:describes src/frob/arch/_layering.py::check_no_di_construction -->

Unlike the layering contract above, this check IS written once against
one file's `NormalizedModule` (T-0609) -- same convention as
`_solid.py`'s LSP/ISP checks, just kept in `_layering.py` since both
checks are this ticket's DIP slice of the SOLID catalog.

`check_no_di_construction` flags a method/function whose OWN body (not
counting nested functions) constructs a same-file concrete class inline
via a bare `ClassName(...)` call -- EXCLUDING:

- `__init__`/`__new__`. Accepting the collaborator as a constructor
  param IS the fix this check points at, so constructing it there is
  not itself the smell being flagged.
- Factory-named functions (`make_*`/`create_*`/`build_*`/`new_*`
  prefixes) -- construction IS a factory's job.

A regular method reaching for `Concrete(...)` mid-body instead of using
an already-injected collaborator hides the dependency inside the method
instead of making it visible at the class's construction boundary --
the textbook no-DI smell. Only a BARE (non-dotted) callee matching a
same-file class name is resolvable enough to flag (`_is_constructor_
call`) -- a dotted call (`self.foo()`, `pkg.Class()`) or a class defined
elsewhere is not, and is skipped, fail-toward-silence.

### Type-driven design checks: `illegal-states-representable` / `primitive-obsession` / `parse-dont-validate` / `boolean-flag-param` (T-0621)

<a id="type-driven-design-checks"></a>
<!-- frob:describes src/frob/arch/_typedesign.py::check_illegal_states_representable -->
<!-- frob:describes src/frob/arch/_typedesign.py::check_primitive_obsession -->
<!-- frob:describes src/frob/arch/_typedesign.py::check_parse_dont_validate -->
<!-- frob:describes src/frob/arch/_typedesign.py::check_boolean_flag_param -->
<!-- frob:describes src/frob/arch/_typedesign.py::run_typedesign_checks -->

`frob.arch._typedesign` (EPIC T-0330's "Logan Smith" type-driven-design
family, T-0621) is written once against the T-0609 normalized model, same
convention as `_solid.py`'s checks.

**T-0892 fold-in note.** At T-0621's implementation time, a sibling ticket
(T-0620) held an active scope lease on `src/frob/arch/_models.py`, so the
four categories below were built against a LOCAL `TypeDesignCategory`/
`TypeDesignSuggestion` pair mirroring `ArchCategory`/`ArchSuggestion`'s
shape field-for-field. T-0892 folded the four categories into the shared
`frob.arch._models.ArchCategory` (T-1028: now graph-indexed as a
`SymbolKind.TYPE` symbol -- the DOC006 waiver this pointer used to need is
gone) and migrated all four check functions to
build `ArchSuggestion` directly once the lease freed up; the local pair no
longer exists.

| Category | Signal | Severity |
|---|---|---|
| `illegal-states-representable` | a class's `bool`-typed field runtime-guarded (a branch mentioning both the bool field's name and another field's name, immediately followed by a raise) inside some method's own body | suggestion |
| `primitive-obsession` | a function/method signature with 3+ raw `str`/`int`/`float`-typed params | suggestion |
| `parse-dont-validate` | a function/method with exactly one param, guarded by a branch+raise on that param, whose declared return type is IDENTICAL to the param's declared type | suggestion |
| `boolean-flag-param` | a PUBLIC function/method with a `bool`-typed param that its own body branches on | suggestion |

**`illegal-states-representable` (`check_illegal_states_representable`).**
The guard-clause proxy is the same line-adjacency shape LSP's
strengthened-precondition check uses (`frob.arch._solid._raise_or_assert_
param_mentions`): a branch whose condition text mentions BOTH a bool
field's name and another field's name, with a raise at or within two
lines of the branch's own line. A "this bool field's validity depends on
that other field" constraint enforced at runtime is exactly the hidden-
state-machine smell -- modeling the valid combinations as an enum/newtype
would make the invalid combination impossible to construct at all.

**`primitive-obsession` (`check_primitive_obsession`).** A same-file,
single-signature proxy: `PRIMITIVE_OBSESSION_MIN_PARAMS` (3) or more
params annotated with a raw `str`/`int`/`float` type on one signature.
The ticket's fuller "repeated co-occurrence across call sites" framing
would need a project-wide call-site scan (out of this check's per-
signature shape, disclosed here rather than silently narrowed);
`metric` carries the raw-param count.

**`parse-dont-validate` (`check_parse_dont_validate`).** Requires EXACTLY
one non-receiver param, a guard on that param (the same line-adjacency
proxy as above), and a `return_type` IDENTICAL to the param's own `type`
text -- the function proves an invariant about its input but hands back
the exact same unrefined type instead of a type that encodes "already
validated". A different (or absent) return type is the refined-type
shape this check is pointing callers toward, and is not flagged.

**`boolean-flag-param` (`check_boolean_flag_param`).** Only a PUBLIC
function/method (name not starting with `_`) is considered -- a private
helper's bool flag is an implementation detail, not a caller-visible API
smell. Flags when a `bool`-typed param's name appears in one of the
function's OWN branch condition texts; `metric` carries the count of
branches mentioning that param.

**`run_typedesign_checks(module) -> list[TypeDesignSuggestion]`** runs
all four above against one `NormalizedModule` and returns the combined
findings, mirroring `run_srp_checks`'s convention.

T-0972: `check_illegal_states_representable`'s own
`sorted(mentioned_bool)`/`sorted(mentioned_other)` message-formatting
calls picked up a reasoned `frob:waive PERF004` (both sets differ per
method, nothing to hoist) -- no behavior change.

### Logging discipline checks: `unlogged-error-path` / `unlogged-boundary` / `print-as-diagnostic` (T-0622)

<a id="logging-discipline-checks"></a>
<!-- frob:describes src/frob/arch/_logging_checks.py::check_unlogged_error_path -->
<!-- frob:describes src/frob/arch/_logging_checks.py::check_unlogged_boundary -->
<!-- frob:describes src/frob/arch/_logging_checks.py::check_print_as_diagnostic -->
<!-- frob:describes src/frob/arch/_logging_checks.py::run_logging_checks -->

`frob.arch._logging_checks` (EPIC T-0330's observability family, T-0622)
is written once against the T-0609 normalized model, same convention as
`_typedesign.py`'s checks. Unlike `_typedesign.py` (T-0621), this
ticket's `_models.py` scope lease was free at implementation time, so all
three categories extend the shared `ArchCategory`/`ArchSuggestion`
directly -- no local literal, no fold-in follow-up needed.

**STRATA BOUNDARY NOTE (per CLAUDE.md).** These checks are logging-IN-CODE
only: "does a log call exist textually near this error path/boundary",
with no runtime/flow correlation. Whether a log statement actually FIRES
on the path that needs it at runtime, whether it correlates across a
distributed call, and log volume/level appropriateness are
`frob.strata`'s observability-of-flow concern
(`frob.strata._circuit_breaker`/`_retry`/`_fallback`), not this module's.
A function can pass every check here and still be silently unobservable
at runtime if the log call is unreachable dead code -- these checks only
prove a log call is textually present, not that it executes.

| Category | Signal | Severity |
|---|---|---|
| `unlogged-error-path` | an `except`/`catch` clause, or a `return Err(...)`, with no log call within 3 lines | suggestion |
| `unlogged-boundary` | a public function/method with no log call anywhere in its body, or a subprocess/network/filesystem call site with no log call within 3 lines | suggestion |
| `print-as-diagnostic` | a `print(...)` call outside a CLI-output module (path containing `cli`/`__main__`/`console`) | suggestion |

**`unlogged-error-path` (`check_unlogged_error_path`).** Scans every
function/method's `catches` and `returns`. A `catches` entry is flagged
unless some call in the function's own `calls` list looks like a log
statement (`_LOG_CALLEE_MARKERS`: a callee whose lowercased text contains
`log.`/`logger.`/`logging.`/`_log.`/`_logger.`) within 3 source lines
(`_LOG_ADJACENCY_WINDOW`) of the catch. A `returns` entry is flagged the
same way when its `value_text` contains `"Err("` (typani's Result-error-
value convention) and no log call falls within the same window of the
return's line. This model has no block-scoping finer than a whole
function body, so the line-adjacency window is the same style of textual
proxy `frob.arch._solid`'s guard-clause detectors already use for
raise-adjacent-to-branch.

**`unlogged-boundary` (`check_unlogged_boundary`).** Two shapes, both
scoped to PUBLIC functions/methods only (name not starting with `_`) for
the first shape -- a private helper crossing a boundary is usually one
step inside an already-logged public call:
1. A public function/method with NO log call anywhere in its own
   `calls` list is flagged once, at the function's own line -- an
   operator has no textual evidence it was ever invoked.
2. Any call (public or private function) whose callee text matches
   `_BOUNDARY_CALLEE_MARKERS` (`subprocess.`, `os.system`, `os.popen`,
   `requests.`, `httpx.`, `urllib.`, `socket.`, `open(`, `os.remove`,
   `os.unlink`, `os.mkdir`, `os.makedirs`, `os.rmdir`, `shutil.`) with no
   log call within the 3-line adjacency window is flagged at the call's
   own line.

**`print-as-diagnostic` (`check_print_as_diagnostic`).** Flags every
`print(...)` call (callee text exactly `"print"`, not a dotted
`obj.print` attribute call) in a module whose repo-relative path does
NOT contain `cli`, `__main__`, or `console` (`_CLI_OUTPUT_PATH_MARKERS`)
-- a CLI-output module's whole job is writing to stdout, so `print`
there is correct and is not flagged. `print()` elsewhere has no level,
no logger name, and cannot be filtered by a log aggregator.

**`run_logging_checks(module) -> list[ArchSuggestion]`** runs all three
above against one `NormalizedModule` and returns the combined findings,
mirroring `run_typedesign_checks`'s convention.

### Fallibility checks: `unhandled-result` / `swallowed-exception` / `recoverable-error-wrong-signature` / `over-broad-except` (T-0623)

<a id="fallibility-checks"></a>
<!-- frob:describes src/frob/arch/_fallibility.py::check_unhandled_result -->
<!-- frob:describes src/frob/arch/_fallibility.py::check_swallowed_exception -->
<!-- frob:describes src/frob/arch/_fallibility.py::check_recoverable_error_wrong_signature -->
<!-- frob:describes src/frob/arch/_fallibility.py::check_over_broad_except -->
<!-- frob:describes src/frob/arch/_fallibility.py::run_fallibility_checks -->

`frob.arch._fallibility` (EPIC T-0330's error-handling family, T-0623) is
written once against the T-0609 normalized model, same convention as
`_logging_checks.py`'s checks. `_models.py`'s scope lease was free at
implementation time (same as T-0622's), so all four categories extend
the shared `ArchCategory`/`ArchSuggestion` directly.

**MODEL-LIMIT DISCLOSURE.** `NormalizedCall` has no "is this call's
result assigned / passed along / discarded" field -- the T-0609 model
tracks a call's callee/line/args only, not its surrounding expression
context. `unhandled-result` is therefore a disclosed, best-effort proxy,
not a precise discard check -- see its own entry below.

| Category | Signal | Severity |
|---|---|---|
| `unhandled-result` | a call to a same-module Result-returning function whose line is not also a `return` statement's line | suggestion |
| `swallowed-exception` | a bare/`Exception` catch with no raise/log-call/return within 3 lines | warning |
| `recoverable-error-wrong-signature` | a function raises `ValueError`/`KeyError`/`LookupError`/`TypeError` but its declared return type is not `Result[...]` | suggestion |
| `over-broad-except` | a bare/`Exception` catch, OR a raise near a catch whose exception type differs from the caught type | suggestion |

**`unhandled-result` (`check_unhandled_result`).** Builds a same-module
lookup table of function/method bare names whose `return_type` text
contains `"Result["` (`_result_returning_names`), then scans every
function's `calls` for a callee whose trailing dotted segment matches
that table. A match is flagged UNLESS the call's own line is also one of
the caller's `returns` lines (the one shape -- `return foo()` -- this
model can positively confirm consumes the value). A genuine
`x = foo()` local assignment looks IDENTICAL to a discarded bare-
statement call under this model (no assignment-target field exists) --
this is a disclosed false-positive shape, not silently narrowed.
Cross-module Result-returning functions are out of scope (this model
does not resolve imports).

**`swallowed-exception` (`check_swallowed_exception`).** A bare `except:`
/`catch (...)` or `except Exception:` clause (`exception_type` is `None`
or `"Exception"`) is flagged unless some raise, log call (the same
`_LOG_CALLEE_MARKERS` text heuristic `_logging_checks` uses, duplicated
locally since this ticket's scope excludes that module), or return falls
within 3 lines of the catch (`_catch_does_something`) -- a caught
exception with no observable reaction is silently swallowed.

**`recoverable-error-wrong-signature`
(`check_recoverable_error_wrong_signature`).** Flags a function/method
that raises `ValueError`/`KeyError`/`LookupError`/`TypeError`
(`_RECOVERABLE_EXCEPTION_TYPES`) while its own declared `return_type` is
set and does NOT contain `"Result["` -- an expected, recoverable failure
mode modeled as a raised exception instead of a typed `Result[T, E]`
return forces every caller into try/except. A function with no declared
return type at all is not flagged (nothing to compare against).

**`over-broad-except` (`check_over_broad_except`).** Two shapes, folded
into one category per this ticket's own body text presenting them as a
single bullet: (a) a bare/`Exception` catch is flagged directly, same
detection as `swallowed-exception`'s catch-shape test but independent of
whether the body reacts; (b) a raise within 3 lines of ANY catch whose
`exception_type` differs from that catch's own caught type is flagged as
a possible re-raise-losing-context -- this model has no `from`-clause
field, so it cannot confirm chaining was actually omitted; it is the
same disclosed adjacency proxy every check in this module uses, not a
syntactic certainty.

**`run_fallibility_checks(module) -> list[ArchSuggestion]`** runs all
four above against one `NormalizedModule` and returns the combined
findings, mirroring `run_logging_checks`'s convention.

T-0972: `check_over_broad_except`'s own nested `for r in func.raises`
scan (comparing each raise site's exception type against the current
catch clause's, a small per-function raise-site list) picked up a
reasoned `frob:waive PERF003` (not a scale-sensitive cross join) -- no
behavior change.

### May-raise resolver: `compute_may_raise` / `FunctionMayRaise` / `UNKNOWN` / `UBIQUITOUS_TIER` (T-0686, extended T-0689)

<a id="may-raise-resolver"></a>
<!-- frob:describes src/frob/arch/_mayraise.py::compute_may_raise -->
<!-- frob:describes src/frob/arch/_mayraise.py::FunctionMayRaise -->
<!-- frob:describes src/frob/arch/_mayraise.py::UNKNOWN -->
<!-- frob:describes src/frob/arch/_mayraise.py::UBIQUITOUS_TIER -->

`frob.arch._mayraise` (T-0686, child 1 of T-0685's exception may-raise
umbrella) computes per-function may-raise sets over the shared
`frob.arch._normalized.NormalizedModule` (T-0609) -- own `raise` sites
plus a curated builtin-raiser table (`int`/`float` casts -> `ValueError`/
`TypeError`, `open` -> `OSError`, `getattr` -> `AttributeError`, `next` ->
`StopIteration`, a bare subscript -> `KeyError`) plus callee propagation
(a monotonic chaotic-iteration fixpoint over the same-module call graph,
so cycles converge) minus `except`-clause subtraction
(exception-hierarchy aware -- `except Exception` discharges a raised
`ValueError`). This is a RESOLVER, not a check on its own: it exposes a
per-function `raises` set for downstream `frob.arch` categories (T-0688's
exhaustiveness/boundary-catch-all family) to consume, not a
warning/suggestion of its own.

**Opaque boundaries and `frob:callee-raises` declarations (T-0689,
renamed from `frob:raises` by T-0931).** A call crossing into ctypes/cffi
or any other compiled C-extension module this resolver has no Python
source to see into (not a same-module function, not in either curated
raiser table below) is already fail-closed to `UNKNOWN` via the ordinary
unresolved-callee path -- no special-casing is needed to make an opaque
boundary Unknown by default. Two escapes from that default: (1) a
curated `_STDLIB_QUALIFIED_RAISERS` table, keyed on a call's FULL dotted
callee text (`"json.loads"`, `"sqlite3.connect"`, `"sqlite3.execute"`,
`"struct.pack"`, `"struct.unpack"`) rather than the bare name
`_BUILTIN_RAISERS` matches on, so well-known stdlib C-extension calls
resolve to their documented exception precisely; (2) a same-line
`# frob:callee-raises A, B` comment on the call site
(`NormalizedCall.declared_raises`, parsed by `frob.arch._python`'s
`PythonAdapter` for python; `# frob:callee-raises` alone declares the
EMPTY set) SUBSTITUTES its declared set for that call unconditionally,
checked FIRST before either curated table -- the intended way to clear
an otherwise-`UNKNOWN` ctypes/cffi call. This resolver only CONSUMES a
declaration already parsed onto the model; the declaration
grammar/enforcement across FFI boundaries generally (cross-checking a
pyo3 declaration against its visible Rust side, requiring a declaration
on every ctypes boundary) is a separate sibling ticket's job (T-0690),
not duplicated here.

**Naming note (T-0931).** This call-site directive was originally named
`frob:raises` (T-0689), but T-0688 landed concurrently with an unrelated
ABOVE-THE-DEF, function-wide `frob:raises` declared-propagation
directive consumed by `EXHAUST002` (see
[EXHAUST001/EXHAUST002](gates.md#exhaust001-exhaust002-t-0688) in
gates.md) -- same verb text, different placement rule, different
semantics, different consumer. T-0931 reconciled this by keeping
`frob:raises` for the function-wide declared-propagation surface (the
form T-0690's FFI-boundary declarations will also extend, matching its
`frob:deprecated`-style above-the-def placement) and renaming this
call-site, per-`NormalizedCall` form to `frob:callee-raises`. The two
directives remain independent: a function can carry an above-the-def
`frob:raises` declaring what it propagates to ITS OWN callers, while any
call inside its body can independently carry a `frob:callee-raises`
declaring what THAT callee is known to raise.

It is closely related to, but distinct from, the [Fallibility
checks](#fallibility-checks) family above: `_fallibility.py` flags
individual call-site SHAPES (an unhandled Result, a swallowed exception)
within one function's own body, while `_mayraise.py` computes each
function's full TRANSITIVE may-raise set across the module's call graph
-- the input the T-0688 exhaustiveness family needs and `_fallibility.py`
does not compute.

- **`compute_may_raise(module) -> dict[str, FunctionMayRaise]`.** Runs the
  fixpoint over every top-level function and method in `module`, keyed by
  `qualname` (`path::Class.method`/`path::function`). Same-module bare-
  name callee resolution only (`_build_name_to_func`) -- cross-module
  calls, aliased imports, and attribute-chain receivers are out of scope,
  matching `_fallibility.py`'s own disclosed model limit; a name bound to
  more than one function/method in the module is AMBIGUOUS and excluded,
  so a call to it resolves fail-closed to `UNKNOWN` rather than guessing.
  A bare `raise` (re-raise) resolves to the NEAREST PRECEDING `catch`'s
  caught type on that function (line-adjacency proxy, same style
  `_fallibility.py` uses elsewhere); with no preceding catch, or a bare
  `except:` preceding catch, it resolves to `UNKNOWN` too.
- **`FunctionMayRaise`.** One function/method's computed result: its
  `qualname` and the `frozenset[str]` of exception type names it may
  raise, `UNKNOWN` included whenever any contributing raise/call could
  not be statically resolved. Never includes `UBIQUITOUS_TIER` members.
- **`UNKNOWN`.** The sentinel raised-type name meaning "this function may
  raise something this resolver could not statically determine" -- the
  fail-closed contribution of any unresolved callee or unresolvable bare
  `raise`.
- **`UBIQUITOUS_TIER`.** `MemoryError`/`KeyboardInterrupt`/`SystemExit`,
  tracked SEPARATELY from a function's own computed `raises` set --
  asynchronous-delivery exceptions no static analysis of a function's own
  body can rule out. Exhaustiveness never demands these be enumerated
  per-function; only a boundary catch-all (bare `except:`) discharges
  them, which is a caller's concern (T-0688), not this resolver's.

### C++ may-throw analysis: `_scan_cpp_functions` / `check_cpp_noexcept_violations` / `cpp-noexcept-throws` (T-0687)

<a id="cpp-may-throw-analysis-t-0687"></a>
<!-- frob:describes src/frob/arch/_cpp_mayraise.py::_scan_cpp_functions -->
<!-- frob:describes src/frob/arch/_cpp_mayraise.py::check_cpp_noexcept_violations -->

Child 2 of T-0685's exception may-raise umbrella, the SAME may-set shape
the [may-raise resolver](#may-raise-resolver) (T-0686, Python) and the
[FFI-boundary cross-check](gates.md#ffi001-ffi002-t-0690) (T-0690, pyo3)
already establish, applied to C++'s own exception model: explicit `throw`
sites, resolved same-file callee propagation (an iterative fixpoint, same
shape `compute_may_raise`'s own callee-graph fixpoint uses), a curated
STL-thrower table (`.at(` -> `out_of_range`, `new` -> `bad_alloc`, the
`std::sto*` numeric-parse family -> `invalid_argument`), and `UNKNOWN`
fail-closed for anything this module cannot statically resolve
(virtual/indirect/function-pointer calls, per T-0665's established
obligation-pattern precedent for exactly this class of "cannot see
through this call" gap).

**`noexcept` functions are HARD boundaries**, not advisory ones: a
`noexcept` function whose computed may-throw set is non-empty (a real
type, or `UNKNOWN`) escapes to `std::terminate` at runtime the instant
that exception actually propagates. `check_cpp_noexcept_violations`
appends an `ArchSuggestion` (category `cpp-noexcept-throws`, severity
`"error"` -- T-0687 added `"error"` to `ArchSeverity`, previously
`warning`/`suggestion`/`info` only, see `frob.arch._models`'s own
module-level comment) for every such violation, naming the escaping
type(s). A `try { ... } catch (...) { ... }` anywhere in the function
discharges it (the SAME whole-function, not block-scoped, catch-all
doctrine [EXHAUST001](gates.md#exhaust001-exhaust002-t-0688) already uses
for Python's `Unknown` -- same disclosed limitation, not a new one).

**Raw-text scan, not a tree-sitter node walk** (deliberate, mirroring
`frob.arch._ffi`'s own choice for the same reason, see
[FFI-boundary cross-check](gates.md#ffi001-ffi002-t-0690)): no
`NormalizedModule`/`NormalizedFunction` adapter exists for C++ today
(`frob.arch._cpp`'s existing long-function/god-class checks are
themselves tree-sitter node walks, not model-adapter output), and
standing one up is a much larger change than this ticket's own declared
scope justifies for one new check family.

**Wired into `analyze_project`'s live `"cpp"` dispatch branch**
(`frob.arch.__init__._analyze_one_file`) -- a plain
`frob.arch.analyze_project(root)` call already surfaces these findings.
NOT yet promoted into a `src/frob/gates/**` enforced/unwaivable gate
finding (that wiring is out of this ticket's declared scope
(`src/frob/arch/**`/`src/frob/lang/**`/`tests/unit/test_arch.py` only);
same T-0728/T-0688 "built and tested first, wiring later" precedent this
package already uses repeatedly).

**Full soundness needs libclang eventually** (disclosed, per the parent
ticket's own acceptance text): a tree-sitter-level text scan cannot
resolve overload sets, template instantiation, or cross-translation-unit
calls -- the `UNKNOWN` fail-closed default is the approximation the
parent ticket explicitly asked for instead of a to-be-improved
placeholder.

### Misc design smells: `mutable-default-arg` / `feature-envy` / `data-clumps` / `magic-literal` / `dead-private-code` / `deep-inheritance` / `temporal-coupling` (T-0624)

<a id="misc-design-smells"></a>
<!-- frob:describes src/frob/arch/_smells.py::check_mutable_default_arg -->
<!-- frob:describes src/frob/arch/_smells.py::check_feature_envy -->
<!-- frob:describes src/frob/arch/_smells.py::check_data_clumps -->
<!-- frob:describes src/frob/arch/_smells.py::check_magic_literal -->
<!-- frob:describes src/frob/arch/_smells.py::check_dead_private_code -->
<!-- frob:describes src/frob/arch/_smells.py::check_deep_inheritance -->
<!-- frob:describes src/frob/arch/_smells.py::check_temporal_coupling -->
<!-- frob:describes src/frob/arch/_smells.py::run_smell_checks -->

`frob.arch._smells` (EPIC T-0330's catch-all smell family, T-0624) is
written once against the T-0609 normalized model, same convention as
`_fallibility.py`'s checks. `_models.py`'s scope lease was free at
implementation time, so all seven categories extend the shared
`ArchCategory`/`ArchSuggestion` directly. `_normalized.py`'s lease was
ALSO free -- `NormalizedParam.default_text` (raw source text of a
default value) was added there because `check_mutable_default_arg`
cannot recognize a list/dict/set literal default without it.

**PER-MODULE SCOPING DISCLOSURE.** `check_dead_private_code` and
`check_deep_inheritance` are described in T-0624's own body as needing
project-wide analysis (the T-0288 call graph; cross-file base-class
resolution) that a single `NormalizedModule` cannot provide --
`frob.graph.callgraph` is a separate subsystem `_smells.py`'s scope does
not integrate with. Both are disclosed PER-MODULE proxies below, not the
true project-wide versions.

| Category | Signal | Severity |
|---|---|---|
| `mutable-default-arg` | a param whose `default_text` looks like a list/dict/set literal or no-arg constructor | warning |
| `feature-envy` | a method calling one non-self receiver more than `self`/`this`/`cls`, at least 2 times | suggestion |
| `data-clumps` | the same 3+ keyword-arg-name group repeated across 3+ call sites in the module | suggestion |
| `magic-literal` | a bare numeric literal (not 0/1/-1) inside a branch condition | suggestion |
| `dead-private-code` | a private top-level function never called by bare name anywhere else in the same file | suggestion |
| `deep-inheritance` | a class whose same-file-resolvable base chain exceeds `DEEP_INHERITANCE_THRESHOLD` (3) | suggestion |
| `temporal-coupling` | a class with an initialization/readiness-named bool field runtime-guarded by another method via a branch+raise | suggestion |

**`mutable-default-arg` (`check_mutable_default_arg`).** Flags a param
with `has_default=True` whose `default_text` starts with `[`, `{`,
`list(`, `dict(`, or `set(` -- a mutable default is created ONCE and
shared across every call that omits the argument.

**`feature-envy` (`check_feature_envy`).** Tallies each method's calls by
receiver (the dotted prefix before the callee's last segment); flags
when some single non-`self`/`this`/`cls` receiver's call count is
STRICTLY GREATER than the self-receiver count and at least 2.

**`data-clumps` (`check_data_clumps`).** Groups call sites by their exact
keyword-argument-name SET (`DATA_CLUMP_MIN_GROUP_SIZE`, 3+ names);
flags a group repeated at `DATA_CLUMP_MIN_SITES` (3) or more distinct
call sites, once, at the first site. Positional-only call sites are
invisible to this proxy (`NormalizedCallArg.keyword` unset).

**`magic-literal` (`check_magic_literal`).** Scans every branch's
`condition_text` for a bare numeric literal not in `{0, 1, -1}`. String
literals are out of scope for this proxy (raw condition text cannot
reliably distinguish a magic string from an identifier without a real
tokenizer).

**`dead-private-code` (`check_dead_private_code`, PER-MODULE proxy).**
Flags a private (`_`-prefixed, not dunder) top-level function whose bare
name never appears as a call callee anywhere else in the SAME module. A
private symbol called only from another file is invisible to this proxy
and will false-positive -- disclosed, not the ticket's own project-wide
T-0288-call-graph version.

**`deep-inheritance` (`check_deep_inheritance`, PER-MODULE proxy).**
Resolves each class's base chain using only classes defined in the SAME
file (`_inheritance_depth`); a chain continuing in another file
under-counts. Flags a same-file-resolvable depth exceeding
`DEEP_INHERITANCE_THRESHOLD` (3).

**`temporal-coupling` (`check_temporal_coupling`).** Flags a class with a
`bool` field whose name suggests a call-order gate (contains
`initialized`/`ready`/`started`/`setup`/`_open`) when some method's own
body guards on that field (a branch mentioning the field's name,
immediately followed by a raise -- the same guard-clause line-adjacency
proxy `_typedesign.py`'s illegal-states-representable check uses).

**`run_smell_checks(module) -> list[ArchSuggestion]`** runs all seven
above against one `NormalizedModule` and returns the combined findings,
mirroring `run_fallibility_checks`'s convention. `check_module_dependency_
cycles` (T-0625, below) is NOT included -- it is project-wide, not
per-module, and is called separately.

T-0972: `check_data_clumps`'s own `sorted(group)` and
`check_temporal_coupling`'s own `sorted(mentioned)` message-formatting
calls each picked up a reasoned `frob:waive PERF004` (both differ per
clump/method, nothing to hoist) -- no behavior change.

### Module dependency cycles: `module-dependency-cycle` (T-0625)

<a id="module-dependency-cycles"></a>
<!-- frob:describes src/frob/arch/_smells.py::check_module_dependency_cycles -->

`check_module_dependency_cycles` (T-0625) lives in `frob.arch._smells`
alongside the misc smell checks above (per this ticket's own declared
scope naming that module rather than a new one), but is NOT written
against a single file's `NormalizedModule` -- an import cycle is
inherently a project-wide property, requiring the WHOLE tree's resolved
import graph, the same reason `_layering.check_layering_violations`
(T-0620) also takes `root` instead of a `NormalizedModule`.

**No second graph builder or cycle-finder is forked.** The check reuses,
directly:
- `frob.lang.extract_imports`/`resolve_local_import` -- the same import-
  resolution pair `frob.app.cycle_runner._build_graph` and
  `_layering.check_layering_violations` already call.
- `frob.cycle.graph.DependencyGraph`/`find_cycles` -- the EXISTING
  Tarjan's-algorithm strongly-connected-component finder `frob cycle`'s
  own CLI command already uses.

Every python file under the scanned root becomes a graph node; each
resolved local import becomes a directed edge. `find_cycles` returns
every strongly-connected component of size 2+ (or a self-loop); each
becomes one `ArchSuggestion` (category `module-dependency-cycle`,
severity `warning`) whose `message` reports the full cycle path
(`a -> b -> c -> a`) and whose `metric` carries the cycle's node count.

### Fork/pool hazards: `pool-inside-pool` / `fork-after-threads` / `pipe-wait-deadlock` / `self-join-deadlock` (T-0695)

<a id="fork-pool-hazards"></a>
<!-- frob:describes src/frob/arch/_concurrency.py::_check_fork_pool_hazards -->

`frob.arch._concurrency` is a call-graph-reachability slice, not a
runtime tracer: every finding is a FAIL-CLOSED syntactic co-occurrence
heuristic over one parsed python file's function bodies, on the same
unwaivable advisory channel every other `frob.arch` category is on
(`frob.gates._waive._unwaivable_channel_rules`). It exists because this repo's
own `_run_combined_jobs` produced a real 6-hour CI hang (T-0265) from a
`ProcessPoolExecutor` forked while a sibling thread pool was open --
T-0581 fixed the runtime ordering, but nothing statically caught the
SHAPE that made it possible. `_run_combined_jobs` initially still
tripped this check (the channel is unwaivable by design, so no waiver
could quiet it); T-0767 discharged the real-repo hit the only sanctioned
way -- restructuring, hoisting each pool's construction into its own
helper (`_open_process_pool` / `_run_thread_jobs`) so no single function
contains the co-occurrence -- and
`tests/unit/test_arch.py::TestForkPoolHazards.
test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs` now
regression-locks `src/frob/gates` at zero hazard findings, while the
synthetic fixtures keep proving each detector fires.

- **`pool-inside-pool`.** A `ProcessPoolExecutor`/`multiprocessing.Pool`
  construction reachable in the same function as a `ThreadPoolExecutor`
  construction, or a `threading.Thread(...)` construction plus a
  `.start()` call. Presence-only (no ordering requirement): a static
  syntactic scan cannot see submit-before-open ordering or
  `mp_context=spawn` safety nets, so it flags the co-occurrence
  conservatively.
- **`fork-after-threads`.** An explicit `os.fork()` (or a
  `multiprocessing.get_context("fork")`/`set_start_method("fork")` call)
  reachable AFTER a `Thread(...).start()` on the same function's
  source-line order -- fork inherits only the calling thread, so a
  sibling thread holding a lock at fork time never releases it in the
  child.
- **`pipe-wait-deadlock`.** A `subprocess.Popen(...)` constructed with a
  `PIPE` stdout/stderr stream, followed by a bare `.wait()` with no
  `.communicate()` anywhere in the function -- unbounded child output
  fills the pipe buffer and deadlocks both processes.
- **`self-join-deadlock`.** A function that is itself submitted/started
  as a pool/thread task somewhere in the module (`.submit(f)`,
  `.map(f, ...)`, `.apply_async(f, ...)`, `Thread(target=f)`) whose OWN
  body calls `.join()`/`.shutdown()`/`.close()` on some pool/thread
  object -- a worker blocking on the dispatcher running it. The
  submitted-callee corpus is built once per module (a submit site and
  its callee can live in different functions), matched against each
  candidate function's bare name AND its `Class.method` qualified name;
  this is a name-based heuristic, not full data-flow, so it can over-
  fire on an unrelated `.join()` inside a dispatched function -- treat a
  finding as "investigate", not "definitely this exact pool".

### Async event-loop hazards: `blocking-call-in-async` / `nested-event-loop` / `unawaited-coroutine` / `async-zero-awaits` / `sequential-independent-awaits` (T-0696, T-1027)

<a id="async-event-loop-hazards"></a>
<!-- frob:describes src/frob/arch/_async_hazards.py::_check_async_event_loop_hazards -->

`frob.arch._async_hazards` is child 3 of the T-0693 concurrency-hazard
umbrella (the fork/pool family above is child 1/2). Same posture as that
family: every finding is a FAIL-CLOSED syntactic co-occurrence heuristic
over one parsed python file's function bodies, on the same unwaivable
advisory channel every other `frob.arch` category is on
(`frob.gates._waive._unwaivable_channel_rules`) -- a structural shape that makes
an event-loop hazard possible, never a runtime proof that it fires.

- **`blocking-call-in-async`.** A curated blocking call (`time.sleep`,
  `requests.get/post/put/delete/patch/head/request`, `urllib`'s
  `urlopen`, `subprocess.run/call/check_call/check_output`, a bare
  `.result()` future/Future wait, or the builtin `open(...)`) reachable
  inside an `async def` body, UNLESS the call site is itself the callable
  argument to a `run_in_executor`/`to_thread` dispatch (which correctly
  offloads it off the event loop). MODEL LIMIT: `open`/`.result()` are
  curated by name alone -- this scan cannot distinguish a large blocking
  read from a trivial one, or a `concurrent.futures.Future.result()` from
  an unrelated `.result()` accessor; both stay advisory-tier for exactly
  that reason.
- **`nested-event-loop`.** `asyncio.run(...)`/`.run_until_complete(...)`
  reachable inside an `async def` body -- a coroutine is by construction
  already running on a loop when it executes, so either call raises
  `RuntimeError: ... cannot be called from a running event loop`.
- **`unawaited-coroutine`.** A call to a function this module itself
  defines as `async def`, used as a bare expression statement -- neither
  awaited, gathered (`asyncio.gather`/`asyncio.ensure_future`/
  `asyncio.create_task` wrap it as an ARGUMENT, so the bare top-level
  statement is a different call shape), nor stored/returned -- the call
  constructs a coroutine object whose body silently never runs.
- **`async-zero-awaits`.** An `async def` whose body contains no `await`
  expression anywhere in its OWN scope (not crossing into a nested
  function's body -- that nested function is visited separately) -- it
  never actually suspends back to the loop, so it should probably be a
  plain `def` (feeds T-0698's IO/CPU-bound model-mismatch advisory too).
- **`sequential-independent-awaits`** (T-1027, T-0698's own disclosed
  cut). A MINIMAL def-use check over 2+ `await` statements that are
  direct statement children of the SAME `block` node (a branch already
  puts its body in a separate `block`, out of scope), in source order.
  An await statement is either a bare `await CALL(...)` expression
  statement or `NAME = await CALL(...)` (a non-identifier assignment
  target, or a `return`/`yield` of an await, is left alone). Two awaits
  are INDEPENDENT when the earlier one's bound NAME does not appear as
  an identifier anywhere inside the later one's `call` node (callee text
  AND every argument -- deliberately broader than "argument" alone, so a
  bound value read as a call's RECEIVER, e.g. `a.close()`, still counts
  as a real dependency). A MAXIMAL contiguous run of 2+ mutually
  independent awaits fires ONE `suggestion`-severity finding naming every
  awaited call site and proposing `asyncio.gather`. MODEL LIMIT
  (disclosed): a NAME-identity check, not a real def-use/alias analysis
  -- it cannot see through indirection (`some_dict[name]` reading a name
  an earlier await bound), and a bare `await CALL(...)` with no LHS is
  always treated as independent of every later await in its run (nothing
  for a later await to depend on).

### Lock-ordering hazards: `lock-order-cycle` / `lock-identity-unresolved` (T-0694)

<a id="lock-ordering-hazards"></a>
<!-- frob:describes src/frob/arch/_lock_ordering.py::_check_lock_ordering_hazards -->

`frob.arch._lock_ordering` is child 2 of the T-0693 concurrency-hazard
umbrella (fork/pool is child 1, async event-loop is child 3 -- both
above). Same posture as those two families: a structural, INTERPROCEDURAL
scan for the classic AB/BA two-lock deadlock shape, generalized to fire
even when the second acquisition happens inside a callee rather than the
same function body. It never traces at runtime -- every finding is a
FAIL-CLOSED heuristic on the same unwaivable advisory channel every other
`frob.arch` category is on (`frob.gates._waive._unwaivable_channel_rules`): a
shape that makes a deadlock POSSIBLE, not a proof it fires.

The model, in order:

1. **Lock identity.** A lock is statically identifiable only when its
   construction site is a curated ctor (`threading`/`multiprocessing`'s
   `Lock`/`RLock`/`Semaphore`/`BoundedSemaphore`, or `anyio`/`asyncio`'s
   `Lock`), assigned either at module level (`lock = threading.Lock()`)
   or as a `self.<attr>` assignment inside a class's own method body. A
   module-level name's canonical id is its bare name; a class-attribute
   lock's canonical id is `ClassName.attr`, resolved at a use site only
   when that use site's own enclosing class matches -- a `self.attr` read
   outside the class that assigned it, or naming a different attr, does
   not alias.
2. **Per-function lock events.** Every `with <expr>:` item and every
   explicit `<expr>.acquire()` call in a function's OWN body (program
   order, crossing `if`/`for`/`try`/`with` but not descending into a
   nested function/class) resolves against the module's lock-identity
   table. A use site that merely LOOKS lock-shaped (a name containing
   "lock"/"mutex"/"semaphore", case-insensitive) but does not resolve is
   recorded as an unresolved advisory instead of silently dropped; a
   plain `with open(...) as f:` matches neither and is ignored.
3. **Interprocedural propagation.** A call to a resolvable same-module
   function is treated, at its call-site position, as acquiring every
   lock that function's own transitively-expanded reachable-lock set
   reaches -- a monotonic chaotic-iteration fixpoint over the same-module
   call graph, mirroring `frob.arch._mayraise.compute_may_raise`'s
   cycle-safe fixpoint but propagating a lock SET instead of a may-raise
   set. This deliberately over-approximates: any lock reachable anywhere
   inside a callee counts as reachable at the call site, not ordered
   against the callee's own internal sequence.
4. **Order-pair extraction.** A function's event sequence becomes
   totally-ordered "slots" (an own lock event is a one-lock slot; a call
   event's slot is the callee's reachable-lock set). Every `(lockA,
   lockB)` pair where `lockA` occupies an earlier slot than `lockB`
   (excluding same-lock pairs -- reentrant use via the same `RLock` never
   counts) becomes a directed edge `lockA -> lockB`, tagged with the
   contributing function's symref and `lockA`'s line.
5. **Cycle detection.** Every function's edges feed one global directed
   graph over lock canonical ids (whole-module resolution boundary,
   matching `_mayraise`/`_fallibility`'s own disclosed limit). Any cycle
   (`lockA -> lockB -> ... -> lockA`) is a potential deadlock: two call
   paths that acquire the same locks in opposite orders can deadlock if
   they ever run concurrently. A consistent global order across every
   call path produces no back-edge and stays silent.

- **`lock-order-cycle`.** Fires on the first reciprocal pair found (some
  `A -> B` edge and some `B -> A` edge, from the same or different
  functions) -- the classic AB/BA shape. The finding message names both
  contributing symrefs and the acquisition-site line for each direction.
- **`lock-identity-unresolved`.** One advisory-tier finding per function
  (deduplicated, not per site) when that function has lock-shaped usage
  the resolver could not statically identify -- declare the lock as a
  module-level or `self.<attr>` assignment of a curated ctor so
  lock-order-cycle detection can account for it.

MODEL-LIMIT DISCLOSURE (same house convention as the sibling families
above): same-module only, no cross-file call resolution; a lock passed as
a function PARAMETER or returned from a factory is not identity-tracked;
release ordering is not modeled at all -- only acquisition order, since a
deadlock is caused by acquisition order, not release order.

Resolving (or waiving) a finding: this channel is unwaivable by design
(`frob.gates._waive._unwaivable_channel_rules` auto-adopts any new
`ArchCategory`, so no separate `frob.gates` change was needed to give
this category the same posture as its siblings) -- there is no `frob:waive`
escape hatch for `lock-order-cycle` or `lock-identity-unresolved`. The
sanctioned remediation is structural, mirroring the fork/pool family's own
T-0767 precedent: establish one consistent global acquisition order for
every call path that needs both locks (restructure so the same two locks
are always acquired in the same order), or, for
`lock-identity-unresolved`, declare the lock via one of the curated ctors
at module or `self.<attr>` scope so the resolver can track it instead of
guessing from a name-shaped heuristic.

### SRP/cohesion checks: `low-cohesion-class` / `god-module` / `mixed-concern-function` (T-0616)

<a id="srp-cohesion-checks"></a>
<!-- frob:describes src/frob/arch/_srp.py::check_lcom4 -->
<!-- frob:describes src/frob/arch/_srp.py::check_god_module -->
<!-- frob:describes src/frob/arch/_srp.py::check_mixed_concern_function -->
<!-- frob:describes src/frob/arch/_srp.py::run_srp_checks -->

`frob.arch._srp` (EPIC T-0329's ARCH1xx SRP family, T-0616) is the first
check module written ONCE against the T-0609 normalized model
(`frob.arch._normalized.NormalizedModule`) instead of a per-language
tree-sitter walk -- every check below fires identically for `PythonAdapter`,
`TypeScriptAdapter`, `RustAdapter`, and `KotlinAdapter` output with no
per-language branch in the check itself (`tests/unit/test_arch_srp.py`'s
`TestCrossLanguage` proves this against `TypeScriptAdapter` output
directly, alongside hand-built `NormalizedModule` fixtures for the
language-agnostic unit tests).

Like `pattern-recommendation`/`anti-pattern-escape`, all three categories
are advisory only and waivable via the existing T-0289 reasoned-override
mechanism (`frob:waive ARCHxxx reason="..." [ceiling=N]`); nothing here is
build-blocking on its own.

**Wiring (T-0728).** T-0616 built these three checks but disclosed leaving
them un-dispatched by `analyze_project` and un-registered as gate rules
(out of that ticket's scope). T-0728 closes that gap: `analyze_project`
now runs all three against every python file's `PythonAdapter`-built
`NormalizedModule` (`frob.arch._run_srp_checks_python`), `frob.gates.
_arch.arch_gate` channels the same three categories into `ARCH101`/
`ARCH102`/`ARCH103` `Violation`s exactly like `long-function`/`ARCH001`
already were, and all three thresholds are `[arch]` `frob.toml`-tunable
via `frob.app.config.load_arch_config` (see
[Configuration](#frob-toml-arch-config) below). Wiring for the other
`LanguageAdapter`s (`TypeScriptAdapter`/`RustAdapter`/`KotlinAdapter`) is
still open -- `analyze_project`'s per-file dispatch only builds a
`NormalizedModule` on the python branch today, matching how every other
normalized-model check already wired into `analyze_project` (the T-0617
OCP family) is python-only in production despite being written
language-agnostic.

| Category | ARCH id | Signal | Severity |
|---|---|---|---|
| `low-cohesion-class` | ARCH101 | a class's field-using methods partition into 2+ disjoint field-usage components (LCOM4, a connectivity graph over `self.<field>` reads/writes) | warning |
| `god-module` | ARCH102 | a module's top-level exports (free functions + classes) number 10+ AND partition into 3+ disjoint naming/usage clusters | warning |
| `mixed-concern-function` | ARCH103 | one function/method body containing an I/O-capability call, a string-formatting call, AND 2+ of its own decision points (branches/loops) | suggestion |

**`low-cohesion-class` (ARCH101, `check_lcom4`).** Skips classes below
`LCOM4_MIN_METHODS` (6) methods or with fewer than
`LCOM4_MIN_FIELD_USING_METHODS` (4) field-touching methods -- a small
class, or one where most methods touch no field at all, is not a real
SRP question. The graph itself: one node per field-using method, an edge
between two methods that share at least one field name, connected
components via union-find. 2+ components means the class bundles
independent responsibilities under one name; `metric` carries the
component count, `symref` is now `f"{module.path}::{class_name}"` (T-0977
-- previously the bare class name, which could never match
`frob.graph.dsl._enclosing_src`'s `path::qualname` waiver-binding shape,
so a `frob:waive ARCH101` placed above the class silently never matched
anything; fixed alongside `mixed-concern-function`'s `symref` below).
T-0977 also promoted `ARCH101` to `[gates.severity] ARCH101 = "error"` in
`frob.toml` once its 2 live findings (both false positives from a
`frob.arch._python` field-access extraction bug -- see that module's
`_py_is_self_attribute`) were fixed at the root cause; see
docs/audits/gates-quality.md's T-0977 section for the measured evidence.

**`god-module` (ARCH102, `check_god_module`).** Skips modules with fewer
than `GOD_MODULE_MIN_EXPORTS` (10) top-level exports. Clustering combines
two signals per the ticket's "naming/usage disjointness" phrasing: a
naming-prefix union (the first `_`-delimited token of a `snake_case`
name, or the leading capitalized run of a `CamelCase` name) AND a usage
union (an edge between two exports where one calls the other, by callee
name) -- two exports that call each other are never split into different
clusters regardless of naming, and two exports sharing a naming family
are never split regardless of whether they call each other. `GOD_MODULE_
MIN_CLUSTERS` (3) disjoint clusters after both unions is the "does
everything" shape this check targets; `metric` carries the cluster count.
T-0977 excludes a zero-method class (`_is_data_only_class`) from the
export/cluster count entirely before either union runs: a pure data
container (a pydantic `BaseModel`, `dataclass`, `StrEnum`, `ErrorSet`
variant bundle) calls nothing, so it can never form a usage edge, and its
only naming signal is its own unique class name -- a conventional flat
`_models.py` catalogue of N such classes inevitably clustered into N
singleton groups pre-fix regardless of real cohesion (docs/audits/
gates-quality.md finding 4's named blind spot for this heuristic,
confirmed against this repo's own `cve/_models.py`/`dup/_models.py`/
`gates/_models.py`/`strata/_ast.py`). This check stays advisory (not
promoted) -- see docs/audits/gates-quality.md's T-0977 section for the
11 real findings still open and the promotion criterion.

**`mixed-concern-function` (ARCH103, `check_mixed_concern_function`).**
Requires ALL THREE of: an I/O-capability call (`_is_io_call` -- the
`open`/`input`/`print` builtins, a call into a well-known I/O-surface
module prefix like `os.`/`socket.`/`requests.`/`logging.`, or a call
ending in a stream-verb method like `.write`/`.read`/`.send`), a
string-formatting call (`_is_format_call` -- `str`/`repr`, or a
`.format`/`.join` method call), and at least `MIXED_CONCERN_MIN_
DECISION_POINTS` (2) of the function's OWN branches/loops (not counting
nested functions, which become their own `NormalizedFunction`). Any one
or two of the three alone is ordinary code (a function that prints a
formatted string is not a smell); only all three together is the
"one body, three unrelated concerns" shape this check targets -- the
same STRONG-HALLMARK-ONLY posture `frob.arch._patterns` already uses.
`symref` is now `f"{module.path}::{qualname}"` (T-0977, same
waiver-binding fix as `low-cohesion-class` above). T-0977 burned 22 of
this rule's 24 live findings down via a reasoned per-site
`frob:waive ARCH103`; the last 2 (`_fmt_directives.py::format_paths`,
`natives/_build.py::build_natives`) are deliberately left live pending a
concurrent sibling ticket's ARCH001 work on the same functions -- see
docs/audits/gates-quality.md's T-0977 section. `[gates.severity] ARCH103`
stays `"warning"` until those 2 clear.

**`run_srp_checks(module) -> list[ArchSuggestion]`** runs all three above
against one `NormalizedModule` and returns the combined findings. T-0728's
`analyze_project` wiring calls `check_lcom4`/`check_god_module`/
`check_mixed_concern_function` individually rather than through this
convenience wrapper, so each threshold can be threaded from `_Limits`
(and, transitively, `frob.toml`) independently; `run_srp_checks` itself is
unchanged and still useful for a caller that wants all three at their
plain module defaults.

### ARCH001: a reasoned per-function override (T-0289)

`long-function` is the one `frob.arch` category channeled into a real
gate `Violation` (`frob.gates._arch.arch_gate`, rule id `ARCH001`) --
every other category stays an advisory, unwaivable-channel suggestion
(see `frob.gates._waive._unwaivable_channel_rules`'s docstring, T-0101). A
long-AND-complex function that is genuinely justified takes the same
reasoned, auditable waiver every other gate rule does:

```python
# frob:waive ARCH001 reason="one big dispatch table, splitting it hides more than it reveals" ceiling="120"
def configure_all_the_things(...):
    ...
```

- `reason=` is mandatory -- an unreasoned `frob:waive ARCH001` is
  rejected exactly like any other rule (`WAIVE001`), not silently
  ignored.
- `ceiling=` is optional and re-fires the finding once the function
  outgrows it: `frob.gates.Violation` carries the function's current
  line count as `metric`, and `frob.gates._match_waiver`'s `_ceiling_ok`
  helper only honors the waiver while `metric <= ceiling` -- a waived
  120-line function that balloons to 400 lines fires again, keeping the
  exception honest instead of a permanent mute. No `ceiling=` means the
  waiver covers the function at any size (the same behavior every other
  `frob:waive` directive has).

  <!-- frob:invariant INV-006 -->
- No qualname table in `frob.toml` -- the waiver lives at the function it
  excuses, travels with a rename (bound via `frob.graph.dsl`'s
  following/enclosing resolution, the same as every other directive), and
  disappears the moment someone deletes the function it's no longer
  attached to.

### Check-stage summary is waiver-aware for ARCH001 (T-0375)

The `frob-arch` stage of `frob check` (`frob.check._python._run_arch`)
used to report every `warning`-severity suggestion raw ("`N warnings, M
suggestions`"), including `long-function` findings already carrying a
reasoned `frob:waive ARCH001` -- inflating the headline against a waiver
that should have made it honest. `_run_arch` now builds the same ARCH001
`Violation`s `frob.gates._arch.arch_gate` would (reusing the suggestions it
already computed, not a second `analyze_project` pass) and runs them
through `frob.gates._apply_waivers` against the obligation graph's WAIVE
edges -- `ceiling=` included, identical semantics to the real gate. A
waived long-function is excluded from the warning headline and rendered as
a `note` diagnostic (`[waived: <symref>]`) instead of `warning`; the
summary line is `"N warnings (M waived), K suggestions"`. Every other arch
category (`god-class`, `high-coupling`, `deep-nesting`,
`abstraction-opportunity`, `large-file`) stays on T-0101's unwaivable
channel and is unaffected -- only `long-function`/ARCH001 has a symref a
waiver can bind to.

## Parsing

`analyze_project` parses every collected file once through
`frob.lang.raw_tree` (one grammar-loading mechanism shared with every
other `frob.lang` consumer -- see docs/modules/lang.md) inside a
`frob.logging.quiet.quiet_stdout_logs()` block, so `frob arch --json`'s
machine-readable stdout payload is never corrupted by `frob.lang`'s
per-parse INFO/DEBUG log lines. C/C++ function/class walks share
`frob.lang.cpp_function_nodes` with `frob.dup._legacy`'s Type-1/2 scanner
-- one C/C++ function-declaration walk, not two.

## Normalized code model (T-0609)

<a id="normalized-code-model"></a>
<!-- frob:describes src/frob/arch/_normalized.py::NormalizedModule -->
<!-- frob:describes src/frob/arch/_normalized.py::LanguageAdapter -->

EPIC T-0329's foundation: today `_python.py`/`_cpp.py` each hand-walk their
own tree-sitter grammar for every check -- adding a language means
re-deriving every detector's walk against a new grammar's node-type names.
`src/frob/arch/_normalized.py` defines a language-agnostic shape a check
can be written against exactly once, plus a `LanguageAdapter` protocol
each per-grammar walker implements to produce it:

| Type | Represents |
|---|---|
| `NormalizedModule` | one source file: path, language label, imports, top-level classes/functions |
| `NormalizedImport` | one import/include/use: module text, line, imported names |
| `NormalizedClass` | one class/struct: name, base-class names, fields, methods |
| `NormalizedField` | one class-level or instance field: name, type, first-assignment line |
| `NormalizedFunction` | one function/method: name, params, return type, `is_method`, `overrides` (base-method name, when determinable), and its flattened body events below |
| `NormalizedParam` | one parameter: name, optional type, whether it has a default |
| `NormalizedBranch` | one decision point (`if`/`elif`/ternary/short-circuit): line + condition source text |
| `NormalizedLoop` | one `for`/`while`: line + kind |
| `NormalizedCall` | one call site: callee name, line, and `declared_raises` (T-0689 -- a `# frob:callee-raises A, B` comment's parsed exception-name set, renamed from `frob:raises` by T-0931; `None` when absent; see [may-raise resolver](#may-raise-resolver)) |
| `NormalizedFieldAccess` | one field read/write inside a body: name, line, `is_write` |
| `NormalizedReturn` | one `return`: line, optional value text |
| `NormalizedRaise` | one `raise`/`throw`: line, exception type name where determinable |
| `NormalizedCatch` | one `except`/`catch`: line, caught exception type name where present |

`LanguageAdapter` is a `typing.Protocol` (`runtime_checkable`): one
`language` label (a `frob.lang` grammar name) and one method,
`adapt(tree, source, rel) -> NormalizedModule`, that maps a parsed
tree-sitter `Tree` onto the model above.

**Scope of T-0609 -- model and protocol only, no migration yet.** No
adapter is registered or wired into `analyze_project` in this ticket:
`_python.py`/`_cpp.py` keep parsing and checking directly against
tree-sitter, unchanged. Migrating the existing python/cpp checks onto the
model (the first concrete `LanguageAdapter` implementations) is T-0610;
TypeScript/Rust/Kotlin adapters built against this same protocol are
EPIC T-0329's remaining children (T-0611 onward). The model's field set
was derived directly from what `frob.arch._patterns`'s T-0332 detectors
already walk (isinstance-chain and state-field-chain need branches +
field accesses; telescoping-ctor needs `__init__` params; wrap-delegate
needs fields + method-body call targets; scattered-construction needs
cross-file call sites) so that migration has no missing entity to
retrofit.

<!-- frob:describes frob-core/src/arch_python.rs::py_function_metrics -->

T-1222 (rust arch python metrics single-pass walk, extraction only --
rule evaluation stays entirely in Python, same design line T-1221's
capability resolver states explicitly): `frob_core.py_function_metrics
(source: bytes) -> [(span, nesting, cyclomatic, events)]` computes the
same per-function body walk `_py_max_nesting`/`_py_cyclomatic`/`_py_
collect_body_events` perform today (`_run_python_checks` measured at 97
pct of archgate's own cost, `_py_build_module` alone 31 pct) natively via
`tree-sitter`, one entry per python function (module-level, method, or
nested -- FLATTENED into one output list rather than `NormalizedFunction.
nested_functions`'s own tree shape) in source order. `events` is an
8-tuple of `branches`/`loops`/`calls`/`field_accesses`/`returns`/
`raises`/`catches`/`subscripts` lists, matching `NormalizedBranch`/
`NormalizedLoop`/`NormalizedCall`/`NormalizedFieldAccess`/
`NormalizedReturn`/`NormalizedRaise`/`NormalizedCatch`/
`NormalizedSubscript`'s own field shapes exactly, MINUS `NormalizedCall.
declared_raises` (see below). Deliberately narrower than
`NormalizedFunction` itself -- no `name`/`params`/`return_type`/
`is_method`/`overrides`, each O(1) to read directly off the
`function_definition` node and left Python-side; this kernel replaces
only the expensive body-walk portion `_py_build_function`/`_py_build_
module` currently perform as three separate Python recursions per
function.

Golden-tested byte-identical against `_py_max_nesting`/`_py_cyclomatic`/
`_py_collect_body_events`'s combined output across this repo's own
`_python.py` plus synthetic fixtures (0 mismatches,
`tests/unit/test_arch_python_native.py::TestPyFunctionMetricsParity`).

One disclosed deviation: `NormalizedCall.declared_raises` (T-0689's
`# frob:callee-raises A, B` same-line comment convention) is never
populated by this kernel -- a raw-text pattern layered on top of the tree
walk, not a tree-sitter extraction concern; `_frob_raises_declaration` is
a five-line pure function over already-available `(call_line,
source_lines)` a consumer can still run Python-side post-hoc, cheaply,
without threading it through the FFI boundary as a second kernel input.
No consumer is rewired to this kernel yet (T-1219's job).

## Public API

<a id="public-api"></a>
<!-- frob:describes src/frob/arch/__init__.py::analyze_project -->

```python
# frob/arch/__init__.py
def analyze_project(
    root: Path,
    *,
    max_function_lines: int = 30,
    max_class_methods: int = 12,
    max_local_imports: int = 8,
    max_nesting_depth: int = 4,
    max_file_lines: int = 500,
) -> ArchResult
    # Walks `root` (honoring [graph].exclude and the standard skip-dir
    # list, same as every other frob file walker) and returns every
    # suggestion found. Never raises on a per-file parse failure -- an
    # unparseable file is skipped (logged at DEBUG), not a whole-scan abort.
```

**Single-file-mode parity (T-1102).** `root` may be a single file
(`frob arch <file>`, or `frob.gates._arch.arch_gate` invoked narrowly
against one path), not only a directory. Before T-1102, a plain file
`root` silently produced ZERO candidates: `_collect_files`/`frob.excludes.
iter_files` both assume a directory (`(root / ".git").exists()` and
`os.walk(root)` are no-ops on a file), so `frob arch <file>` printed "no
architectural issues found" for every category, not just `large-file` --
the exact gap that made a 4346-line `strata-core/src/parse/mod.rs` invisible
to a single-file scan even after `large-file` existed as a category.
`analyze_project` now detects `root.is_file()` and, in that case, resolves
the walk root to `root.parent` (every relative-path/exclude-glob
computation downstream stays identical to a directory walk that happened
to contain only this one file) and seeds the candidate list with just
`root` itself instead of calling `_collect_files` at all -- the
single-file finding runs through the exact same `_analyze_one_file` path
a directory walk uses, so its category/message shape is byte-identical,
never a parallel single-file code path that could drift from the
directory one (`tests/test_arch_gate.py::TestArchGateLargeFile::
test_single_file_mode_matches_directory_walk`).

**`large-file` / `LARGE001` (T-0368/T-0372 advisory, T-1102 gate wiring).**
Any file (any `frob.lang`-supported language) over `max_file_lines`
(`frob.toml`'s `[arch]` table, or the calibrated default) is flagged
`info`-severity `large-file` by `analyze_project` itself; test files and
`fixtures/`-rooted data files stay exempt. `frob.gates._arch.arch_gate`
channels this same category into a real gate `Violation` (`LARGE001`,
WARN first-turn-on given this repo's own pre-existing over-threshold file
corpus at filing time) -- previously advisory-only text/JSON output,
invisible to `frob check`/`frob:waive` entirely. A file-level finding has
no function/class symbol, so a `frob:waive LARGE001 reason="..."` binds
by file/line, not `symref`. See docs/modules/gates.md's rule catalog entry
for the gate-side detail (turn-on count, waiver shape).

<a id="arch-suggestion"></a>
<!-- frob:describes src/frob/arch/_models.py::ArchSuggestion -->

```python
class ArchSuggestion(BaseModel):
    file: str
    line: int | None = None
    category: ArchCategory   # one of the 57 rows in the checks table above
    severity: ArchSeverity   # "warning" | "suggestion" | "info" | "error"
    message: str
    detail: str | None = None
    # T-0289: set for checks about exactly one symbol (currently
    # long-function) so frob.gates._arch.arch_gate can bind a
    # `frob:waive ARCH001` directive to the precise function.
    symref: str | None = None
    # T-0289: the raw measured value (a long-function's line count) --
    # lets a waiver's `ceiling=N` re-fire once the function outgrows it.
    metric: int | None = None
```

<a id="arch-result"></a>
<!-- frob:describes src/frob/arch/_models.py::ArchResult -->

```python
class ArchResult(BaseModel):
    root: str
    suggestions: list[ArchSuggestion]
    files_examined: tuple[str, ...] = ()   # T-1921, see below

    def as_text(self) -> str: ...   # human-readable report
    def as_json(self) -> str: ...   # machine-readable, `frob arch --json`
```

**`files_examined` (T-1921).** The repo-relative paths (same form
`ArchSuggestion.file` uses) that `analyze_project` actually reached far
enough to parse and check, NOT merely every path its walk collected as a
candidate -- a file skipped early (unreadable, no tree-sitter grammar for
its extension, or a parse failure) is deliberately excluded, even though
`_analyze_one_file` was called on it. This backs `frob.gates.
_coverage_sites`'s per-site analysis-coverage substrate
(docs/modules/gates.md#data-models's `GateStats.examined_sites`), filed
from T-1904's investigation of the falsified T-1579 WAIVE004 escape that
deleted 55 live waivers by proving only "the rule fired somewhere",
never "this specific site was re-analyzed" -- reporting a file examined
here that `_analyze_one_file` actually skipped would repeat that same
unsound shape one layer down, so this reflects `_analyze_one_file`'s own
real per-file success/failure return value, not its candidate list.
`frob.gates._arch.arch_examined_sites` is the reader that turns this
into the `"archgate"` entry of `GateStats.examined_sites`.

<!-- frob:describes src/frob/arch/_models.py::ArchResult.as_text -->
<!-- frob:describes src/frob/arch/_models.py::ArchResult.as_json -->
`as_text`/`as_json` are the two render paths every CLI output mode uses;
covered by `tests/unit/test_arch.py::TestArchResultFormat`.

## Configuration: `frob.toml` `[arch]` table (T-0373)

<a id="frob-toml-arch-config"></a>
<!-- frob:describes src/frob/app/_config_meta.py::load_arch_config -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_MAX_FUNCTION_LINES -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_MAX_CLASS_METHODS -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_MAX_LOCAL_IMPORTS -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_MAX_NESTING_DEPTH -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_MAX_FILE_LINES -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_LCOM4_MIN_METHODS -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_LCOM4_MIN_FIELD_USING_METHODS -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_GOD_MODULE_MIN_EXPORTS -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_GOD_MODULE_MIN_CLUSTERS -->
<!-- frob:describes src/frob/app/_config_meta.py::ARCH_DEFAULT_MIXED_CONCERN_MIN_DECISION_POINTS -->

`analyze_project`'s keyword defaults above (30/12/8/4/500) are library
fallbacks for a caller with no `frob.toml` in scope. `frob check`'s ARCH
gate (`frob.gates._arch.arch_gate`) does not use them directly -- it calls
`frob.app.config.load_arch_config(root)` first, which reads the `[arch]`
table from `root/frob.toml` and defaults every unset key to this repo's
calibrated values instead: `max_function_lines=60`, `max_class_methods=12`,
`max_local_imports=8`, `max_nesting_depth=4`, `max_file_lines=800`
(`ARCH_DEFAULT_MAX_*` in `frob.app.config`). A missing or malformed
`frob.toml`, or a `frob.toml` with no `[arch]` table, is not an error --
`load_arch_config` just returns the calibrated defaults, same posture as
every other per-section `frob.toml` reader in this codebase (e.g.
`frob.gates._dup._dup_config`, moved there by T-1174).

T-0728 extends the same `[arch]` table with five more keys for T-0616's
ARCH1xx SRP/cohesion family: `lcom4_min_methods` (default 6),
`lcom4_min_field_using_methods` (default 4), `god_module_min_exports`
(default 10), `god_module_min_clusters` (default 3), and
`mixed_concern_min_decision_points` (default 2) -- identical to `_srp.py`'s
own module-level defaults, since no separate calibration decision has
been made for this repo's own source yet.

```python
# frob/app/config.py
def load_arch_config(root: Path) -> dict[str, int]
    # Returns a kwargs dict: analyze_project(root, **load_arch_config(root))
```

This repo's own `frob.toml` carries an explicit `[arch]` table set to
these same calibrated values -- not strictly required (they equal the
defaults), but present as disclosure of the calibration decision.

## frob:tests

<!-- frob:tests frob.arch.analyze_project tests/unit/test_arch.py -->
`tests/unit/test_arch.py` exercises every category in the table above
against `tests/fixtures/arch_python` (issues expected) and
`tests/fixtures/simple_python` (clean project, no false positives), plus
`as_text`/`as_json` output-shape checks.

## Dependencies and integration points

- `frob.lang` (`raw_tree`, `cpp_function_nodes`, `extract_imports`,
  `resolve_local_import`) for every parse and import-resolution step --
  no bespoke tree-sitter grammar loading of its own.
- `frob.excludes` for the same `[graph].exclude`/skip-dir walk semantics
  every other file-collecting command uses.
- `frob.logging.quiet` to keep `--json` output clean.
- CLI: `frob arch [--json]` (`frob.app.arch_runner`).
