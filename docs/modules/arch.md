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
| `long-function` | a function/method body longer than `max_function_lines` | warning |
| `god-class` | a class with more than `max_class_methods` methods | warning |
| `high-coupling` | a file with more than `max_local_imports` distinct local module imports (via `frob.lang.extract_imports`/`resolve_local_import`) | suggestion |
| `deep-nesting` | a function whose `if`/`for`/`while`/`try`/`with` nesting exceeds `max_nesting_depth` | suggestion |
| `large-file` | any file longer than `max_file_lines` | info |
| `abstraction-opportunity` | 3+ Python functions across the project sharing the same annotated parameter/return-type signature | suggestion |

All thresholds are `analyze_project` keyword arguments with the defaults
shown in the Public API section below; there is no `frob.toml` table for
`frob.arch` yet (a `frob:todo` follow-up if this module grows a gate).

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
