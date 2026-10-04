# crunk

crunk is the CSS and design-token product of the goblin family. This scaffold
ships the `crunk` binary and the `crunk-check` crate with an empty rule set; rule
families, the `crunk.toml` schema and the other verbs land in their own tickets.

## Verbs

| Verb | Needs `crunk.toml` | What it does |
|---|---|---|
| `crunk check` | yes | Runs the (empty) rule set and prints the `gob.sibling/1` document with `product = "crunk"` (`--json`), or a count summary. `--only`, `--fail-on`, `--base`, `--ticket-scope` as for `grimble check`. |
| `crunk doctor` | no | Reports the crunk version, the repository root and the state of `crunk.toml`. |
| `crunk schema` | no | Built-in: the JSON Schema of a verb's output. |

Global flags (`--json`, `--text`, `--format`, `--color`, `-v`, `--version`) come from
`gob-cli`; `--version` prints the workspace lockstep version.

## Exit codes (cli.md section 2)

| Code | Meaning here |
|---|---|
| 0 | ok |
| 1 | `check` found findings at or above `--fail-on` |
| 2 | usage error |
| 3 | `E-NO-CONFIG`: no `crunk.toml` at or above the working directory (an empty file is a valid config), or `E-CONFIG` for a malformed one |
| 4 | internal error |

## Boundary

No frob crate is a dependency of `crunk` or `crunk-check` (`crates/crunk/tests/boundary.rs`).
