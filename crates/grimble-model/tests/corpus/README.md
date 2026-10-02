# The .grmb conformance corpus (grmb-spec 12)

Run by `tests/corpus.rs` (`cargo nextest run -p grimble-model`). One case is either

- a file `X.grmb` with a sibling `X.expect` (and optionally a golden `X.u`), or
- a directory holding an `expect` file (and optionally `expect.u`) and every `.grmb` input of
  the case; paths are relative to the directory, roots are the files declaring `module`.

Directories named in grmb-spec 12 keep those names (`lex/encoding/`, `include/*/`,
`u/encoding/<row of 9.2>/`, `fmt/idempotent/`, `fmt/order/`, `fmt/comments/`, `example/`).
Where the spec lists one file but the point needs several files (`version/header`,
`scope/unique`) the case is a directory of that name.

## `expect` lines

| Line | Meaning |
|---|---|
| `error: MDL001`, `warn: ..`, `advisory: ..`, `unresolved: ..` | one finding of that severity and rule; the set must match exactly |
| `walk: PATH ...` | the walk for MDL005 (repeatable); no `walk` line skips MDL005 |
| `rule: SYS004 ...` | extra rule ids accepted by exception clauses |
| `pack: ID VERSION [DIGEST] [atoms=a,b]` | an enabled pack |
| `root: PATH` | an explicit root (default: files declaring `module`) |
| `fmt: roundtrip` (default) | fmt is idempotent and `parse(fmt(x))` equals `x` in U (damaged files must be refused) |
| `fmt: unchanged` / `fmt: refuses` | the file is already canonical / fmt refuses it |
| `bind: FILE ANCHOR VERB` | a directive `ns:verb` binds to `ANCHOR` (`-` for any file) |

Every case also runs the round-trip contract on each file. A golden `.u` holds the indented term
(sort, operator, name, byte range, anchor, symref), every reference with its scope-graph
resolution, and the bound directives; regenerate with `GRMB_BLESS=1 cargo test -p grimble-model
--test corpus` and review the diff.
