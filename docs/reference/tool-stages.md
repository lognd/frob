# Tool stages (`[[check.tool]]`)

Status: current
Owner: frob
Decisions: none
Audience: user

A tool stage runs an external command after the built-in rules of `frob check`. Design: `docs/design/cicd.md` section 3.

| Key | Default | Meaning |
|---|---|---|
| `name` | required | Stage name; prefixes every message (`zizmor/unpinned-uses: ...`). |
| `def` | unset | Name of a std-pack tool definition (`zizmor`, `actionlint`, `ruff`, `rustfmt`, `ruff-format`, `prettier`, `dotnet-format`, `cargo-semver-checks`, `griffe`); see Tool definitions. |
| `command` | required (unset with `def`) | Program on `PATH` (no separators); the allowlist is the set of stage commands. |
| `args` | `[]` | Arguments, no shell. |
| `timeout_secs` | `300` | Kill limit. |
| `fail_on_nonzero` | `true` | A failing stage is `TOOL001` (Error); a missing binary is `TOOL001` Unresolved and required. |
| `parser` | `none` | `zizmor-json-v1`, `actionlint-json`, `stylelint-json`, `sarif`, `cargo-json`, `ruff-json`, `ty-gitlab`, `pyright-json`, `tsc-text`, `eslint-json`, `roslyn-sarif`, `typos-json`, `formatter-list`, `semver-checks-text` or `griffe-text`: turn stdout into findings. |
| `labels` | `[]` | actionlint runner labels the repository defines. |
| `id_map` | `{}` | Tool finding id to rule id, merged over the parser default. |
| `min_version`, `max_version` | unset | Inclusive dotted-number range of trusted tool versions. |
| `version_args` | parser default | Arguments of `command` that print the version (needed behind `uvx`). |
| `optional` | `false` | A missing binary is Unresolved but not required. |
| `tier` | `ticket` | Earliest check level that runs the stage: `ticket` (also under `frob check --ticket --quick`), `train` (a plain `--ticket` run, which is the land and train check) or `ci` (only the unscoped check). Levels widen, so a `ci` stage never delays a land. |

## eslint stages

`parser = "eslint-json"` reads `eslint -f json` (exit 1 for lint errors is a normal exit; a message without a rule id, such as a parse error, is skipped). `frob init` in a repository whose `package.json` names eslint adds two stages: `eslint` (the repository config: jsx-a11y, react-hooks, react and syntax-level typescript-eslint rules) and `eslint-typed` (`tier = "train"`, `optional`, its own `eslint.typed.config.mjs` with the type-aware typescript-eslint rules). The type-aware rules cost a type check, so they are a separate stage; every tool stage is timed apart from the `[perf]` budget (`timing.stages` with `budgeted = false`), so the type check never counts against the 2 s budget.

## dotnet stage

`parser = "roslyn-sarif"` reads the Roslyn SARIF error log of `dotnet build` (the SARIF reader, plus the id mapping below; exit 1 for build errors is a normal exit). Roslyn writes the log to a file, so the stage runs `dotnet build` with `-p:ErrorLog=<file>%2Cversion=2.1` and prints the file. `frob init` in a repository with a root `.sln` or `.csproj` (a Unity project's generated solution counts) adds that `dotnet` stage with `EnforceCodeStyleInBuild` and `EnableNETAnalyzers` on. Reference `Microsoft.Unity.Analyzers` and `Microsoft.VisualStudio.Threading.Analyzers` as `PackageReference`s: the USP suppressors ship in the Unity package and mark `IDE0051`/`IDE0052` results for engine-called messages and serialized fields as suppressed, so they never become `DEAD001` findings (a suppressed result is kept aside for EXC017, as for every SARIF stage). The log is a single file, so a multi-project build keeps the last project's.

## Skipping stages

`frob check --skip-tools` runs no `[[check.tool]]` stage at all. CI passes it from the `check` step (`cargo dev ci --step check`) because fmt, clippy, docs, gen, zizmor, actionlint, deny, shear and typos each already run as a dedicated step; the built-in rules still run. It also passes `--trust-from origin/experimental`, so a pack absent from `frob.packs.lock` at that ref is reported as Unresolved `untrusted-in-change`; no other trust flag is used.

## Tool definitions

A stage with `def = "<name>"` takes every key it leaves unset from a tool definition shipped in the std pack (`crates/gob-check/src/tools/*.toml`; design: `docs/design/tool-binding.md` section 2). A definition holds the pinned version, the version probe, the trusted range, the default argv, argv variants keyed by version range, exit classes (`success`, `findings`; any other status is `TOOL001`), the parser id, the input and configuration globs, the native suppression pattern, an id map and an optional fix command. `{version}` in an argv stands for the pinned version. Keys the stage sets itself win; `id_map` and `inputs` are merged. The configuration globs join `inputs`, so editing a tool's config re-runs the stage and changes its cache key (file digests, pinned version and range, command line). The version is probed first and the first `[[variant]]` whose inclusive `min_version`..`max_version` holds the probed version replaces the default argv (a stage with its own `args` is never swapped).

```toml
[[check.tool]]
name = "ruff"
def = "ruff"
```

The suppression pattern and fix command are recorded in the definition; EXC017 and the tier A fix runner do not read them yet.

## Parsed stages

With a `parser` the stage exit status no longer decides: tools exit nonzero when they have findings, so only a signal, a timeout or unparseable stdout is a stage failure (`TOOL001`). Findings carry the file and span the tool printed (zizmor and cargo byte offsets, actionlint, stylelint and ruff line and column, SARIF regions), so `frob:accept` applies to them like native findings (a file whose language frob scans for directives; YAML is not yet one).

| Parser | Tool id | Rule | Severity |
|---|---|---|---|
| zizmor | `unpinned-uses` | `CI001` | Warn |
| zizmor | `excessive-permissions` | `CI003` | Warn |
| zizmor | `dangerous-triggers` | `CI006` | Error |
| zizmor | `template-injection` | `CI007` | Error |
| zizmor | `artipacked` | `CI010` | Advisory |
| zizmor | any other id | `TOOL002` | Advisory |
| actionlint | every kind | `CI014` | Warn |
| stylelint | `no-descending-specificity`, `selector-max-compound-selectors`, `selector-max-specificity` | `WCSS001` | Advisory |
| stylelint | `selector-max-id` | `WCSS002` | Advisory |
| stylelint | `declaration-no-important` | `WCSS003` | Advisory |
| stylelint | any other id | `TOOL002` | Advisory |
| eslint | `jsx-a11y/*` | `A11Y001` | Warn |
| eslint | `react-hooks/*`, `react/*` | `REACT001` | Warn |
| eslint | `@typescript-eslint/` `no-floating-promises`, `no-misused-promises`, `await-thenable`, `require-await` | `CONC001` | Warn |
| eslint | `@typescript-eslint/` `no-explicit-any`, `no-unsafe-*` | `TYPING001` | Warn |
| eslint | any other rule id | `LINT001` | Advisory |
| roslyn-sarif | `UNT*` (Microsoft.Unity.Analyzers) | `UNITY101` | Warn |
| roslyn-sarif | `IDE0051`, `IDE0052`, `IDE0060`, `IDE0005`, `CS8019`, `CS0168`, `CS0219` | `DEAD001` | Warn |
| roslyn-sarif | `VSTHRD*` | `CONC001` | Warn |
| roslyn-sarif | `RS0016` and `RS0017` (PublicApiAnalyzers) | `VERSION001` | Error |
| roslyn-sarif | any other id (CA, IDE, CS) | `LINT001` | Advisory |
| sarif | any id (the stage `id_map` names the rule) | `TOOL002` | Advisory |
| cargo-json | `unused_*`, `dead_code` | `DEAD001` | rustc level |
| cargo-json | `too_many_arguments` | `NEAT002` | rustc level |
| cargo-json | clippy correctness lint (deny-by-default) | `LOGIC001` | rustc level |
| cargo-json | any other lint, or a code-less rustc error | `LINT001` | rustc level |
| ruff-json | `F401`, `F841`, `ARG*` | `DEAD001` | Warn |
| ruff-json | `S110` | `ERR001` | Warn |
| ruff-json | `BLE001`, `E722` | `ERR003` | Warn |
| ruff-json | `ASYNC*` | `CONC001` | Warn |
| ruff-json | `PT*` | `TESTQ001` | Warn |
| ruff-json | `B` plus digits (bugbear) | `LOGIC001` | Warn |
| ruff-json | `PLR2004` | off (dropped) | none |
| ruff-json | any other code | `LINT001` | Advisory |
| typos-json | any typo | `SPELL001` | Advisory |
| formatter-list | every file the formatter would rewrite (one per file) | `FMT001` | Warn |
| semver-checks-text | every public item cargo-semver-checks reports as broken | `VERSION001` | Error |
| griffe-text | every breakage `griffe check` reports | `VERSION001` | Error |

The cargo-json severity is the rustc level: `error` is Error, `warning` is Warn. Summary lines (`aborting due to`, `warnings emitted`) are not findings; build artifacts and other non-diagnostic lines are skipped. A diagnostic repeated for each cargo target is reported once per site.

ruff-json reads `ruff check --output-format=json`. A diagnostic without a rule code (a syntax error) is dropped and is not a finding; only unparseable stdout fails the stage (`TOOL001`). An `id_map` entry for a ruff code wins over the table above.

ty-gitlab reads `ty check --output-format gitlab` and pyright-json reads `pyright --outputjson` (error and warning diagnostics only, 0-based ranges shifted to 1-based). Both map every finding to `LINT001` (Advisory) unless `id_map` says otherwise, and normal exits are 0 and 1. Their findings also decide which Python files are type-clean for `[types] trust`. `frob check` runs the first such stage (fixed argv, no placeholders) once while building the snapshot graph and feeds the clean-file set to the graph build; if the stage is absent, cannot run, exits other than 0 or 1, or prints unreadable output, no file is clean and annotations stay claims (May). With `trust` other than `checked` the stage is not consulted for facts.

tsc-text reads `tsc --strict --noEmit --pretty false` (`path(line,col): error TSnnnn: message`; indented continuation lines join the message; exits 0 to 2 are normal). It only counts as a type-fact source when its args contain `--strict`; without it the stage is skipped for facts. Every TypeScript or JavaScript file the compiler did not report on is type-clean, except a file with `@ts-nocheck`. A line with `@ts-ignore`, `@ts-expect-error` (that line and the next), `as any`, `as unknown`, `<any>` or `<unknown>` is demoted to a claim. Python and TypeScript stages are independent: the first strict stage per language is run and the clean sets are merged.

## `[types]`

| Key | Default | Meaning |
| --- | --- | --- |
| `trust` | `checked` | How far a parameter annotation narrows a Python or TypeScript method call. `checked`: the call resolves exactly (Must) only when the bound checker reported nothing on the caller's file and the call's line has no `# type: ignore`, `# pyright: ignore` or `# ty: ignore` (TypeScript: `@ts-ignore`, `@ts-expect-error`, `as any`; a file with `@ts-nocheck` is never clean); otherwise the annotated class is a claim (May). `annotated`: always a claim (May). `none`: annotations are hints only and the call is not narrowed. A TypeScript parameter annotated `any` is a dynamic call (an unresolved edge with reason Dynamic) unless `trust` is `none`. |

`gob_check::type_facts_from_output` turns a checker's stdout into the clean-file set the symbol graph consumes (`SymbolGraph::from_files_typed`).

`frob init` in a repository with a `pyproject.toml` adds a pinned `ruff` stage: `uvx ruff@0.14.1 check --output-format=json --no-cache .`, parser `ruff-json`, with the range 0.14.0..0.14.99 and `inputs` covering Python sources and the ruff config files.

typos-json reads `typos --format json` (exit 2 for typos is a normal exit); the correction is in the message, and the repository's `typos.toml` allowlist is applied by typos itself, so allowlisted words never reach the parser.

stylelint runs as `stylelint --formatter json` (exit 2 for lint errors is a normal exit; the stage exit status does not decide). `crunk check` reads `[[check.tool]]` from `crunk.toml`, so the same stage binds under the crunk ids.

actionlint `runner-label` findings are dropped when the label is listed in `labels`; with no `labels` configured they are Advisory (they cannot be told apart from custom-label noise); with `labels` configured and the label absent they stay Warn. The filter runs inside frob, so the tool needs no config file.

## Version range and schema lag

The version is read with `version_args` (default `--version` for zizmor and stylelint, `-version` for actionlint). Outside `min_version`..`max_version`, or unreadable while a range is set, the stage is skipped and yields one `TOOL001` Unresolved finding saying schema lag. It is not a required Unresolved, so it never fails the default gate.

## Running behind uvx

```toml
[[check.tool]]
name = "zizmor"
command = "uvx"
args = ["zizmor@1.30.1", "--offline", "--format", "json-v1", "--no-exit-codes", "."]
parser = "zizmor-json-v1"
version_args = ["zizmor@1.30.1", "--version"]
min_version = "1.30.0"
max_version = "1.30.99"
```

## Formatter stages

`parser = "formatter-list"` reads the check mode of a formatter and reports one `FMT001` per unformatted file. It reads stdout and stderr together (prettier writes its list to stderr) and recognises the `Diff in <path>:N:` lines of rustfmt, `Would reformat: <path>` of ruff format, `[warn] <path>` of prettier, `<path>(l,c): error ...` of dotnet format and a bare path. Exit 0 and 1 are normal. The std definitions `rustfmt`, `ruff-format`, `prettier` and `dotnet-format` carry `[fix] unattended = true`, so `frob check --fix` is a tier A fix: it runs the formatter's write command over the flagged files and re-checks. Only files inside the run's scope (`--ticket` scope globs) are passed to the formatter; a flagged file outside the scope is left alone and reported as skipped with its `frob lease widen` hint, and a file a formatter touches anyway (a rustfmt child module) is restored byte for byte. A formatter that is missing, untrusted or exits non-zero fails the fix with `E-CHECK-FIX-IO`.

`parser = "semver-checks-text"` reads the text report of `cargo semver-checks` (stdout and stderr together) and reports one `VERSION001` Error per item under a `Failed in:` list, named in the message with its lint and located at the file and line the tool gives (`Cargo.toml` when it gives none). A crate whose `Checking` header reports a breaking change (a major bump, or a minor bump below 1.0) yields no finding, so a bumped version is accepted. The std definition `cargo-semver-checks` compares against the registry baseline; pass `--baseline-rev <ref>` in the stage `args` to compare against a git ref. Exit 0 and 1 are normal.

`parser = "griffe-text"` reads `griffe check` one-line breakages (`path:LINE: object: message`) as `VERSION001` Errors. griffe does not report version bumps, so a major bump is not recognised: scope the stage to releases that keep the major version, or accept the finding. Name the package and baseline in the stage `args`. api-extractor is not bound yet.
