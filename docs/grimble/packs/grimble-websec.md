# The grimble-websec pack

`packs/grimble-websec` is a data pack (packs.md tier 1 manifest, GRL rules) for server-side web
code. It is embedded by `grimble_check::websec_pack` so it ships in the binary.

## Layout

| Path | Content |
|---|---|
| `packs/grimble-websec/pack.toml` | name, version, families, `provides.rules` |
| `packs/grimble-websec/rules/SEC101.grl` | WEBSEC: TLS verification disabled |
| `packs/grimble-websec/rules/SQL101.grl` | SQL: query built by interpolation |
| `packs/grimble-websec/rules/COMPLY101.grl` | COMPLY (with PII): personal data in a log call |
| `packs/grimble-websec/rules/ROUTE101.grl` | ROUTE: GET and a state-changing method on one route |
| `packs/grimble-websec/rules/WEBPERF201.grl` | WEBPERF (server): blocking sleep in an async handler |

Every rule has a firing, a clean and a not-applicable example and an `explain` with `## Remedy`;
a rule without a firing and a clean example fails to compile (GRL011).

## Namespaces

WEBSEC is a family of the pack, but its rule ids live in the SEC namespace (`SEC1xx`), so
`grimble rule catalog` shows family `WEBSEC` with namespace `SEC`. WEBPERF server rules use
`WEBPERF2xx`, to stay clear of the markup rules `WEBPERF1xx` in crunk-web.

The capability atoms `db.query` and `net` are owned by core-effects; this pack declares no
atoms and an empty `[effects]` table.

## Lock

`websec_pack::locked(root, read)` returns the lock entry: the BLAKE3 tree digest over every file
under the pack directory. `websec_pack::verify_tree` refuses a tree that differs from the
embedded copy.

## Design gaps recorded

- SEC and PII family rows: the only machine-readable family registry for grimble is a pack
  manifest's `families` list, so SEC and PII are registered there (metadata only, no PII rule
  yet). boundaries.md assigns SEC and PII to a `grimble-security` data pack and rules.md lists
  them under code+deps; that crate does not exist. Whether the rows belong in this pack or in
  grimble-lints is an owner decision; moving them is a manifest edit.
- WEBPERF is also a crunk-web family; enabling both packs in one loader raises PACK004.
- No `grimble.packs.lock` file exists yet and std-pack enablement (`[packs] enabled`) is not
  wired to GRL packs, so the pack is registered in code (`grimble_check::websec_pack`) and not
  yet switched on from `grimble.toml`.
