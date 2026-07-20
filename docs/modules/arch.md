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
