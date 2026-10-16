# Tool stages (`[[check.tool]]`)

Status: current
Owner: frob
Decisions: none
Audience: user

A tool stage runs an external command after the built-in rules of `frob check`. Design: `docs/design/cicd.md` section 3.

| Key | Default | Meaning |
|---|---|---|
| `name` | required | Stage name; prefixes every message (`zizmor/unpinned-uses: ...`). |
| `def` | unset | Name of a std-pack tool definition (`zizmor`, `actionlint`, `ruff`); see Tool definitions. |
| `command` | required (unset with `def`) | Program on `PATH` (no separators); the allowlist is the set of stage commands. |
| `args` | `[]` | Arguments, no shell. |
| `timeout_secs` | `300` | Kill limit. |
| `fail_on_nonzero` | `true` | A failing stage is `TOOL001` (Error); a missing binary is `TOOL001` Unresolved and required. |
| `parser` | `none` | `zizmor-json-v1`, `actionlint-json`, `stylelint-json`, `sarif`, `cargo-json`, `ruff-json`, `ty-gitlab`, `pyright-json` or `typos-json`: turn stdout into findings. |
| `labels` | `[]` | actionlint runner labels the repository defines. |
| `id_map` | `{}` | Tool finding id to rule id, merged over the parser default. |
| `min_version`, `max_version` | unset | Inclusive dotted-number range of trusted tool versions. |
| `version_args` | parser default | Arguments of `command` that print the version (needed behind `uvx`). |
| `optional` | `false` | A missing binary is Unresolved but not required. |
| `tier` | `ticket` | Earliest check level that runs the stage: `ticket` (also under `frob check --ticket --quick`), `train` (a plain `--ticket` run, which is the land and train check) or `ci` (only the unscoped check). Levels widen, so a `ci` stage never delays a land. |

## Tool definitions

A stage with `def = "<name>"` takes every key it leaves unset from a tool definition shipped in the std pack (`crates/gob-packs/src/std/tools/*.toml`; design: `docs/design/tool-binding.md` section 2). A definition holds the pinned version, the version probe, the trusted range, the default argv, argv variants keyed by version range, exit classes (`success`, `findings`; any other status is `TOOL001`), the parser id, the input and configuration globs, the native suppression pattern, an id map and an optional fix command. `{version}` in an argv stands for the pinned version. Keys the stage sets itself win; `id_map` and `inputs` are merged. The configuration globs join `inputs`, so editing a tool's config re-runs the stage and changes its cache key (file digests, pinned version and range, command line). The version is probed first and the first `[[variant]]` whose inclusive `min_version`..`max_version` holds the probed version replaces the default argv (a stage with its own `args` is never swapped).

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

The cargo-json severity is the rustc level: `error` is Error, `warning` is Warn. Summary lines (`aborting due to`, `warnings emitted`) are not findings; build artifacts and other non-diagnostic lines are skipped. A diagnostic repeated for each cargo target is reported once per site.

ruff-json reads `ruff check --output-format=json`. A diagnostic without a rule code (a syntax error) is dropped and is not a finding; only unparseable stdout fails the stage (`TOOL001`). An `id_map` entry for a ruff code wins over the table above.

ty-gitlab reads `ty check --output-format gitlab` and pyright-json reads `pyright --outputjson` (error and warning diagnostics only, 0-based ranges shifted to 1-based). Both map every finding to `LINT001` (Advisory) unless `id_map` says otherwise, and normal exits are 0 and 1. Their findings also decide which Python files are type-clean for `[types] trust`. `frob check` runs the first such stage (fixed argv, no placeholders) once while building the snapshot graph and feeds the clean-file set to the graph build; if the stage is absent, cannot run, exits other than 0 or 1, or prints unreadable output, no file is clean and annotations stay claims (May). With `trust` other than `checked` the stage is not consulted for facts.

## `[types]`

| Key | Default | Meaning |
| --- | --- | --- |
| `trust` | `checked` | How far a parameter annotation narrows a Python method call. `checked`: the call resolves exactly (Must) only when the bound checker reported nothing on the caller's file and the call's line has no `# type: ignore`, `# pyright: ignore` or `# ty: ignore`; otherwise the annotated class is a claim (May). `annotated`: always a claim (May). `none`: annotations are hints only and the call is not narrowed. |

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
