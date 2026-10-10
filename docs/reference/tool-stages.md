# Tool stages (`[[check.tool]]`)

Status: current
Owner: frob
Decisions: none
Audience: user

A tool stage runs an external command after the built-in rules of `frob check`. Design: `docs/design/cicd.md` section 3.

| Key | Default | Meaning |
|---|---|---|
| `name` | required | Stage name; prefixes every message (`zizmor/unpinned-uses: ...`). |
| `command` | required | Program on `PATH` (no separators); the allowlist is the set of stage commands. |
| `args` | `[]` | Arguments, no shell. |
| `timeout_secs` | `300` | Kill limit. |
| `fail_on_nonzero` | `true` | A failing stage is `TOOL001` (Error); a missing binary is `TOOL001` Unresolved and required. |
| `parser` | `none` | `zizmor-json-v1` or `actionlint-json`: turn stdout into findings. |
| `labels` | `[]` | actionlint runner labels the repository defines. |
| `id_map` | `{}` | Tool finding id to rule id, merged over the parser default. |
| `min_version`, `max_version` | unset | Inclusive dotted-number range of trusted tool versions. |
| `version_args` | parser default | Arguments of `command` that print the version (needed behind `uvx`). |
| `optional` | `false` | A missing binary is Unresolved but not required. |

## Parsed stages

With a `parser` the stage exit status no longer decides: tools exit nonzero when they have findings, so only a signal, a timeout or unparseable stdout is a stage failure (`TOOL001`). Findings carry the file and span the tool printed (zizmor byte offsets, actionlint line and column), so `frob:accept` applies to them like native findings (a file whose language frob scans for directives; YAML is not yet one).

| Parser | Tool id | Rule | Severity |
|---|---|---|---|
| zizmor | `unpinned-uses` | `CI001` | Warn |
| zizmor | `excessive-permissions` | `CI003` | Warn |
| zizmor | `dangerous-triggers` | `CI006` | Error |
| zizmor | `template-injection` | `CI007` | Error |
| zizmor | `artipacked` | `CI010` | Advisory |
| zizmor | any other id | `TOOL002` | Advisory |
| actionlint | every kind | `CI014` | Warn |

actionlint `runner-label` findings are dropped when the label is listed in `labels`; with no `labels` configured they are Advisory (they cannot be told apart from custom-label noise); with `labels` configured and the label absent they stay Warn. The filter runs inside frob, so the tool needs no config file.

## Version range and schema lag

The version is read with `version_args` (default `--version` for zizmor, `-version` for actionlint). Outside `min_version`..`max_version`, or unreadable while a range is set, the stage is skipped and yields one `TOOL001` Unresolved finding saying schema lag. It is not a required Unresolved, so it never fails the default gate.

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
