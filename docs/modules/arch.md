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
| `abstraction-opportunity` | 3+ Python functions across the project sharing the same annotated parameter/return-type signature | suggestion |

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
<!-- frob:describes frob.arch.analyze_project -->

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
<!-- frob:describes frob.arch.ArchSuggestion -->

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
<!-- frob:describes frob.arch.ArchResult -->

```python
class ArchResult(BaseModel):
    root: str
    suggestions: list[ArchSuggestion]

    def as_text(self) -> str: ...   # human-readable report
    def as_json(self) -> str: ...   # machine-readable, `frob arch --json`
```

<!-- frob:describes frob.arch.ArchResult.as_text -->
<!-- frob:describes frob.arch.ArchResult.as_json -->
`as_text`/`as_json` are the two render paths every CLI output mode uses;
covered by `tests/unit/test_arch.py::TestArchResultFormat`.

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
