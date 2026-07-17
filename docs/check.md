# frob check

Aggregate quality gate. Runs all static analysis tools in sequence, surfaces
errors first, and exits non-zero if any tool reports errors.

## Usage

```bash
frob check src/                        # Python (auto-detected)
frob check src/ --type python          # force Python mode
frob check src/ --type cpp             # C++/CMake mode
frob check src/ --type rust            # Rust/Cargo mode
frob check src/ --json                 # machine-readable output
```

## Python mode

Runs in order:
1. `ruff check` -- lint errors
2. `ruff format --check` -- format violations
3. `ty check` -- type errors
4. `frob cycle` -- import cycles
5. `frob dup` -- duplicate code blocks
6. `frob arch` -- architectural violations (long functions, god classes)
7. `frob bind` -- pybind11/PyO3 BIND coverage
8. `frob exports` -- missing `__init__.py` exports
9. PyCharm inspection (if auto-located)
10. `gates` -- `frob.gates.run_gates` (docs/gates.md): drift, coverage, scope,
    pre-work, invariant, test, and policy rule violations. A load failure
    (e.g. not a git repo, no `tickets/`) is a soft skip, not a check failure;
    any `ERROR`-severity violation fails the stage like any other tool.

Output order: errors first, then warnings, then notes. Each tool gets a
one-line summary. Fails fast if errors are found.

### Skip flags

```bash
frob check src/ --skip-ruff
frob check src/ --skip-ty
frob check src/ --skip-cycle
frob check src/ --skip-dup
frob check src/ --skip-arch
frob check src/ --skip-bind
frob check src/ --skip-exports
frob check src/ --skip-gates
```

### Gates integration flags

```bash
frob check --ticket T-0042             # explicit ticket context for scope/pre-work gates
frob check --base main                 # base ref for the drift/coverage diff (default: main)
frob check --only gates                # run only the gates stage (repeatable; any stage name)
frob check --only ruff --only gates    # run ruff and gates only
frob check --stamp-coverage            # record coverage.xml as the current stamp, then exit
```

`--only` accepts any stage name (`ruff`, `ty`, `cycle`, `dup`, `arch`, `bind`,
`exports`, `gates`); when omitted, every non-skipped stage runs
(gates included). `--stamp-coverage` is how `make coverage` records
`.frob/coverage-stamp` after `pytest --cov` runs; TEST006 compares the stamp
against the live graph snapshot on later `frob check` runs.

## Cycle severity

`frob cycle` uses size-based severity for detected import cycles:

| Cycle size | Severity |
|-----------|---------|
| 1-2 nodes | info |
| 3-5 nodes | warning |
| 6+ nodes | error |

Cycles are reported in multi-line format, one symbol per line:

```
=== CYCLE (warning) ===
frob.edit
  -> frob.ast.python
  -> frob.ast.common
  -> frob.edit
```

## C++ mode (auto-detected from `CMakeLists.txt`)

Runs in order:
1. CMake configure + build
2. `clang-tidy` on all sources
3. `clang-format --check` on all sources
4. `ctest` (optionally with `valgrind`)

```bash
frob check . --type cpp
frob check . --type cpp --valgrind
frob check . --type cpp --build-dir build/
frob check . --type cpp --skip-build --skip-clang-format
```

## Rust mode (auto-detected from `Cargo.toml`)

Runs in order:
1. `cargo check`
2. `cargo clippy`
3. `cargo fmt --check`
4. `cargo test` (optionally with `valgrind`)

```bash
frob check . --type rust
frob check . --type rust --valgrind
frob check . --type rust --skip-clippy
```

## Auto-detection

| Sentinel file | Detected type |
|--------------|--------------|
| `Cargo.toml` | rust |
| `CMakeLists.txt` | cpp |
| `pyproject.toml` | python |
| (none) | python (fallback) |

## Output format

Text output groups by severity:

```
=== ERRORS (3) ===
src/frob/edit/__init__.py:42: error [ruff E501] line too long
...

=== WARNINGS (1) ===
src/frob/edit/__init__.py:10: warning [ty] possibly-unbound

=== TOOL SUMMARY ===
ruff check    2 errors
ty            1 warning
cycle         ok
dup           ok
arch          ok
```

JSON output (`--json`) includes the full structured `CheckResult` with per-tool
`ToolResult` entries containing `Diagnostic` objects.

## Use in CI

```bash
frob check src/ && echo "all clear"
# Exits 0 only if zero errors across all tools.
```
