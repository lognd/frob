# frob parse

Parse raw tool output into a compact, structured summary.

## Usage

```
# From stdin (pipe from the tool directly)
pytest tests/ 2>&1 | frob parse pytest --exit-code $?

# From a file
frob parse ruff < ruff_output.txt
frob parse clang build.log --exit-code 1

# JSON output for programmatic use
frob parse ty --json < ty_output.txt

# In a pipeline: propagate the tool's failure exit code
pytest ... 2>&1 | frob parse pytest --exit-code $? --passthrough || exit 1
```

## Supported tools

| Tool | Input format | Notes |
|------|-------------|-------|
| `pytest` | Terminal output | Parses PASSED/FAILED lines + failure blocks |
| `ruff` | Text or JSON (`--output-format json`) | JSON auto-detected |
| `ty` | Terminal output | Parses `error[code]` lines |
| `cargo` | JSON (`--message-format json`) or plain text | Auto-detected; plain text parses `test ... ok/FAILED` lines |
| `clang-tidy` | Text diagnostics | Deduplicates by location+check, strips ANSI |
| `valgrind` | Text or XML (`--xml=yes`) | Auto-detected; extracts leak summary and invalid access blocks |
| `clang` / `clang++` | GCC-format diagnostics | Strips ANSI codes |
| `gcc` / `g++` | GCC-format diagnostics | Same as clang |
| `junit` / `gtest` / `catch2` | JUnit XML | `pytest --junit-xml`, gtest `--gtest_output=xml`, Catch2 XML reporter |

## Default output

Failures, errors, and warnings only -- passing items are hidden:

```
[pytest]  1 failed, 44 passed (0.45s)
  FAIL    tests/test_stub.py::test_target_not_found: AssertionError: assert False

[ruff]  2 errors, 0 warnings
  error   src/frob/ast/python.py:3:8  F401  `os` imported but unused
  error   src/frob/app/config.py:47:89  E501  Line too long

[ty]  1 errors, 1 warnings
  error   src/frob/app/config.py:23:5  incompatible-types  Argument of type "str"...
  warn    src/frob/ast/python.py:41:12  possibly-undefined  Name "node" is possibly unbound

[clang]  1 errors, 1 warnings
  error   src/engine.cpp:12:5  use of undeclared identifier 'foo'
  warn    src/engine.cpp:15:10  unused variable 'x'
```

## Flags

| Flag | Meaning |
|------|---------|
| `--exit-code N` | Exit code the tool returned; affects `passed` status |
| `--verbose` | Also show passing tests and notes |
| `--json` | Emit structured JSON instead of text |
| `--passthrough` | Exit non-zero if the tool failed (useful in CI/pipelines) |

## Why it exists

Raw tool output is noisy. A pytest run with 150 tests generates ~300 lines even
on success. Claude reads that whole thing to find the 3 relevant failure lines.
`frob parse` compresses a 300-line pytest run to ~5 lines, delivering the same
actionable information at 1/60th the token cost.

## Typical agentic use

```bash
# Python
pytest tests/ --tb=short 2>&1 | frob parse pytest --exit-code $?
ruff check src/ --output-format json | frob parse ruff
ty check src/ 2>&1 | frob parse ty

# Rust
cargo test 2>&1 | frob parse cargo --exit-code $?
cargo clippy 2>&1 | frob parse cargo --exit-code $?

# C++
clang-tidy src/**/*.cpp -- 2>&1 | frob parse clang-tidy --exit-code $?
valgrind --xml=yes --xml-file=/tmp/vg.xml ./myapp; frob parse valgrind < /tmp/vg.xml

# Claude reads compact summaries (~50 tokens) instead of raw output (~2000 tokens)
```

## Integration with frob check

`frob check` runs all relevant parsers internally and surfaces results in
severity order. Use `frob parse` directly only when running individual tools
outside the `frob check` pipeline.
