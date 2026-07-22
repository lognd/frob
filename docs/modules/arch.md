# frob.arch -- lightweight architectural-smell scanner

One sentence: `frob.arch.analyze_project` walks a source tree through
`frob.lang`'s single grammar-dispatch mechanism and reports structural
smells (long functions, god classes, high coupling, deep nesting, large
files, and cross-file signature-abstraction opportunities) as advisory
`ArchSuggestion`s -- it is a report, not a gate; nothing here fails a build.

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
| `pattern-recommendation` | a strong structural HALLMARK (isinstance chain, state-field chain, telescoping constructor, scattered construction, wrap-and-delegate class) matches a registered `frob.arch._patterns` rule | suggestion |
| `anti-pattern-escape` | a strong structural ANTI-PATTERN (god object, stringly-typed comparison chain) matches a registered `frob.arch._patterns` rule | suggestion |
| `low-cohesion-class` (ARCH101, T-0616) | a class's field-using methods split into 2+ disjoint field-usage components (LCOM4) -- written once against the normalized model, fires across languages | warning |
| `god-module` (ARCH102, T-0616) | a module's 10+ top-level exports partition into 3+ disjoint naming/usage clusters -- written once against the normalized model | warning |
| `mixed-concern-function` (ARCH103, T-0616) | one function body mixes an I/O call, a string-formatting call, and 2+ of its own decision points -- written once against the normalized model | suggestion |

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

`frob.arch._python._is_dispatch_family` detects this off tree-sitter
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
unwaivable-channel categories (`frob.gates._unwaivable_channel_rules`,
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

`frob.arch._python._check_abstraction_opportunities` now requires one of
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
bool` signature) and specific-signature families like the `(Path) ->
tuple[Violation, ...]` gate group still flag in full.

### Design-pattern recommender: `pattern-recommendation` / `anti-pattern-escape` (T-0332)

<a id="design-pattern-registry"></a>
<!-- frob:describes src/frob/arch/_patterns.py::PatternRuleSpec -->
<!-- frob:describes src/frob/arch/_patterns.py::PATTERN_REGISTRY -->
<!-- frob:describes src/frob/arch/_patterns.py::new_construction_accumulator -->

`frob.arch._patterns` is a positive complement to the smell categories
above: instead of only flagging a structural problem, it maps a strong
structural HALLMARK to a recommended GoF/modern PATTERN, or a detected
ANTI-PATTERN to a concrete ESCAPE route. Both directions are pure
ADVISORY findings -- `severity="suggestion"`, never an error, and both
categories stay on the unwaivable advisory channel every other
`frob.arch` category is on (`frob.gates._unwaivable_channel_rules`,
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
- **`PatternRuleSpec`** (a frozen dataclass) is the registry's row shape:
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
| `god-object` | escape | a class already flagged `god-class` (more methods than `max_class_methods`) | SRP decompose |
| `stringly-typed` | escape | a plain identifier (never `self.<attr>` -- that is `state-field-chain`'s territory) compared via `==` against 4+ distinct string literals across one `elif` chain | newtype (Enum / typed value object) |

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

**Deferred rows.** T-0332's plan enumerates 8 hallmark->pattern rows and 5
anti-pattern->escape rows; the 7 above are implemented with real,
precision-checked detectors. The remaining 6 (`incompatible-interface-
bridging -> Adapter`, `expensive-object-reuse -> Flyweight/pool`,
`manual-callback-list -> Observer`, `anemic-domain-model -> move behavior
to data`, `poltergeist/lava-flow -> delete`, `sequential-coupling ->
explicit state`) need fuzzier signals that risk the STRONG-HALLMARK-ONLY
constraint above without a larger detector investment -- deferred, not
silently dropped; see `tickets.md`'s T-0332 Done report and T-draft-4fb8deee
(the filed follow-up ticket) for the remaining rows.

### OCP checks: `type-dispatch-smell` / `non-exhaustive-enum-match` (T-0617)

<a id="ocp-checks"></a>
<!-- frob:describes src/frob/arch/_ocp.py::_check_type_dispatch_smell -->
<!-- frob:describes src/frob/arch/_ocp.py::_check_non_exhaustive_enum_match -->

`frob.arch._ocp` is the OCP (Open/Closed Principle) slice of T-0330's
SOLID catalog (the ARCH1xx family). Both checks stay on the same
unwaivable advisory channel every other `frob.arch` category is on
(`frob.gates._unwaivable_channel_rules`) until a future ticket wires a
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
component count, `symref` the class name (so a `ceiling=N` waiver can
re-fire once the class's cluster count grows further).

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

**`run_srp_checks(module) -> list[ArchSuggestion]`** runs all three above
against one `NormalizedModule` and returns the combined findings -- the
single entry point a future orchestration-wiring ticket will call per
parsed file (`analyze_project`'s per-language dispatch and `frob.app.
config`'s `[arch]` table are both out of T-0616's scope; every threshold
above is a plain keyword argument with a calibrated module-level default,
ready for that follow-up wiring to thread through `frob.toml` the same
way the existing five knobs are).

### ARCH001: a reasoned per-function override (T-0289)

`long-function` is the one `frob.arch` category channeled into a real
gate `Violation` (`frob.gates._arch.arch_gate`, rule id `ARCH001`) --
every other category stays an advisory, unwaivable-channel suggestion
(see `frob.gates._unwaivable_channel_rules`'s docstring, T-0101). A
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
| `NormalizedCall` | one call site: callee name, line |
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

<a id="arch-suggestion"></a>
<!-- frob:describes src/frob/arch/_models.py::ArchSuggestion -->

```python
class ArchSuggestion(BaseModel):
    file: str
    line: int | None = None
    category: ArchCategory   # one of the six rows in the table above
    severity: ArchSeverity   # "warning" | "suggestion" | "info"
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

    def as_text(self) -> str: ...   # human-readable report
    def as_json(self) -> str: ...   # machine-readable, `frob arch --json`
```

<!-- frob:describes src/frob/arch/_models.py::ArchResult.as_text -->
<!-- frob:describes src/frob/arch/_models.py::ArchResult.as_json -->
`as_text`/`as_json` are the two render paths every CLI output mode uses;
covered by `tests/unit/test_arch.py::TestArchResultFormat`.

## Configuration: `frob.toml` `[arch]` table (T-0373)

<a id="frob-toml-arch-config"></a>
<!-- frob:describes src/frob/app/config.py::load_arch_config -->
<!-- frob:describes src/frob/app/config.py::ARCH_DEFAULT_MAX_FUNCTION_LINES -->
<!-- frob:describes src/frob/app/config.py::ARCH_DEFAULT_MAX_CLASS_METHODS -->
<!-- frob:describes src/frob/app/config.py::ARCH_DEFAULT_MAX_LOCAL_IMPORTS -->
<!-- frob:describes src/frob/app/config.py::ARCH_DEFAULT_MAX_NESTING_DEPTH -->
<!-- frob:describes src/frob/app/config.py::ARCH_DEFAULT_MAX_FILE_LINES -->

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
`frob.gates._dup_config`).

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
