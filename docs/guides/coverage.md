# Measure coverage across languages

Status: current
Owner: frob
Decisions: none
Audience: developer

How-to guide (Diataxis: task). Read this to collect line coverage for Rust,
Python, JavaScript/TypeScript and C# with one flag, merge it into a single lcov
file, and have `frob check` hold each part of the tree to a minimum (rule
COV004). Design background is in [testing.md](../design/testing.md) section 9.

## 1. Collect coverage

Coverage rides on evidence capture. Add `--coverage` to
`frob ticket evidence add` for any test provider:

```
frob ticket evidence add '~ABC1234' --provider nextest --ref "-p my-crate" --coverage
frob ticket evidence add '~ABC1234' --provider pytest  --ref "tests/" --coverage
frob ticket evidence add '~ABC1234' --provider vitest  --ref "src/a.test.ts" --coverage
frob ticket evidence add '~ABC1234' --provider dotnet  --ref "cs/Calc.Tests" --coverage
```

There is no `--coverage` flag on `frob test`; the flag lives on
`ticket evidence add`, which runs the tests and then the coverage tool.

| Language | Provider | Tool it needs | Also needs |
| --- | --- | --- | --- |
| Rust | `nextest` | `cargo-llvm-cov` | a root `Cargo.toml` |
| Python | `pytest` | `coverage` (pytest-cov) | a `test_*.py` or `*_test.py` file |
| JavaScript/TypeScript | `vitest`, `jest` | `node` | the runner in `node_modules/.bin`; for vitest also `@vitest/coverage-v8` or `-istanbul` |
| C# | `dotnet` | `dotnet` | a project referencing `coverlet.collector` |

Each run writes its own file, `.frob/coverage/<language>.info` (languages:
`rust`, `python`, `javascript`, `csharp`). Paths are normalised to repo-relative
form, and dependency and build-output records (`node_modules`, `bin`, `obj`) are
dropped. Every `.info` file is then merged into the `[coverage] report` file
(default `lcov.info`), which is the one COV004 reads. The evidence record keeps
a summary per language.

A missing tool is recorded as "not run", never as a failure.

## 2. Set thresholds

In `frob.toml`:

```toml
[coverage]
report = "lcov.info"
require_reports = true

[[coverage.threshold]]
scope = "src/**"
line = 75

[[coverage.threshold]]
scope = "py/**"
line = 80
branch = 60
```

`scope` is a file or glob matched against the report's repo-relative paths;
`line` and `branch` are minimum percentages. See
[config.md](../reference/config.md) for the keys.

## 3. Read COV004

`frob check` reports one finding per threshold that is not met, naming the
scope, the metric, and measured against required:

```
scope `py/**`: line coverage 80.00% (4/5) is below the required 81.00%
```

Two further outcomes, per language that has tests:

- Tool not installed: an Unresolved finding, `<language> coverage not run:
  <tool> is not installed`.
- Tool ran (or a report is otherwise owed) but no report exists, with
  `require_reports = true`: an error, `<language> has tests but no coverage
  report`. Set `require_reports = false` to stop owing reports.

## 4. Unity editor tests

Unity editor (edit-mode and play-mode) coverage is not supported. The C#
provider measures `dotnet test` projects only. It is tracked as ticket
~KDCJJ4K, "Unity editor coverage under the unity provider".

## 5. Tested end to end

`crates/frob/tests/it/coverage_e2e.rs` builds a fixture repository with Rust,
Python, JavaScript and C# tests, feeds each real provider reader a seeded raw
report, merges them, and runs the real `frob check` to assert that COV004
reports every language against its own threshold. The coverage tools
themselves are not run, so the test needs none of them installed.
