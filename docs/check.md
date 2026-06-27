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
