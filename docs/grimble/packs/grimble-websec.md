# The grimble-websec pack

`packs/grimble-websec` is a data pack (packs.md tier 1 manifest, GRL rules) for server-side web
code. It is embedded by `grimble_check::websec_pack` so it ships in the binary.

## Layout

| Path | Content |
|---|---|
| `packs/grimble-websec/pack.toml` | name, version, families, `provides.rules` |
| `packs/grimble-websec/rules/SEC101.grl` | WEBSEC: TLS verification disabled |
| `packs/grimble-websec/rules/websec/SEC102.grl` | WEBSEC: cookie set with Secure or HttpOnly off |
| `packs/grimble-websec/rules/websec/SEC103.grl` | WEBSEC: CORS allows any origin |
| `packs/grimble-websec/rules/websec/SEC104.grl` | WEBSEC: unsafe deserializer (pickle, marshal, yaml.load) |
| `packs/grimble-websec/rules/SQL101.grl` | SQL: query built by interpolation |
| `packs/grimble-websec/rules/sql/SQL102.grl` | SQL: query built with `.format()` |
| `packs/grimble-websec/rules/sql/SQL103.grl` | SQL: query built by `+` or `%` |
| `packs/grimble-websec/rules/sql/SQL104.grl` | SQL: raw ORM SQL built by interpolation |
| `packs/grimble-websec/rules/COMPLY101.grl` | COMPLY (with PII): personal data in a log call |
| `packs/grimble-websec/rules/ROUTE101.grl` | ROUTE: GET and a state-changing method on one route |
| `packs/grimble-websec/rules/route/ROUTE102.grl` | ROUTE: debug server exposed (`run(debug=True)`) |
| `packs/grimble-websec/rules/route/ROUTE103.grl` | ROUTE: TRACE or CONNECT accepted on a route |
| `packs/grimble-websec/rules/route/ROUTE104.grl` | ROUTE: view exempted from CSRF protection |
| `packs/grimble-websec/rules/comply-pii/PII101.grl` | PII: personal data sent to a third-party service |
| `packs/grimble-websec/rules/comply-pii/PII102.grl` | PII: personal data in an exception or error message |
| `packs/grimble-websec/rules/comply-pii/PII103.grl` | PII: personal data cached with no expiry |
| `packs/grimble-websec/rules/WEBPERF201.grl` | WEBPERF (server): blocking sleep in an async handler |
| `packs/grimble-websec/rules/webperf-server/WEBPERF202.grl` | WEBPERF (server): unbounded `fetchall()` |
| `packs/grimble-websec/rules/webperf-server/WEBPERF203.grl` | WEBPERF (server): unbounded ORM `objects.all()` |
| `packs/grimble-websec/rules/webperf-server/WEBPERF204.grl` | WEBPERF (server): `send_file()` without `max_age` |

Every rule has a firing, a clean and a not-applicable example and an `explain` with `## Remedy`;
a rule without a firing and a clean example fails to compile (GRL011).

SQL102 to SQL104 are the first SQL slice (string-built queries and raw ORM calls in Python; the store-shape rules STORE103 and STORE104 stay in sysdesign; other languages are NotApplicable or Unresolved, never clean). SEC102 to SEC104 are the first WEBSEC slice (Python call shapes; injection sinks, unsafe HTML and client-side secrets need the shared web engine and are follow-ups). PII101 to PII103 are the first PII slice (Python call shapes; consent-marker and retention-schedule rules need
a data-flow adapter and are follow-ups). ROUTE102 to ROUTE104 are the first ROUTE slice and read Flask-style Python calls. Auth-on-route
and handler-exposure rules need framework adapters (route tables, decorators); until an adapter
exists, other languages and frameworks are NotApplicable (the markdown example) or Unresolved,
never clean.

## Namespaces

WEBSEC is a family of the pack, but its rule ids live in the SEC namespace (`SEC1xx`), so
`grimble rule catalog` shows family `WEBSEC` with namespace `SEC`. WEBPERF server rules use
`WEBPERF2xx` (WEBPERF202 to WEBPERF204 are the first slice and read Python calls; other languages are NotApplicable or Unresolved, never clean), to stay clear of the markup rules `WEBPERF1xx` in crunk-web.

The capability atoms `db.query` and `net` are owned by core-effects; this pack declares no
atoms and an empty `[effects]` table.

## Lock

`websec_pack::locked(root, read)` returns the lock entry: the BLAKE3 tree digest over every file
under the pack directory. `websec_pack::verify_tree` refuses a tree that differs from the
embedded copy.

## Design gaps recorded

- SEC and PII family rows: the only machine-readable family registry for grimble is a pack
  manifest's `families` list, so SEC and PII are registered there (PII101 to PII103 are the first PII rules). boundaries.md assigns SEC and PII to a `grimble-security` data pack and rules.md lists
  them under code+deps; that crate does not exist. Whether the rows belong in this pack or in
  grimble-lints is an owner decision; moving them is a manifest edit.
- WEBPERF is also a crunk-web family; enabling both packs in one loader raises PACK004.
- No `grimble.packs.lock` file exists yet and std-pack enablement (`[packs] enabled`) is not
  wired to GRL packs, so the pack is registered in code (`grimble_check::websec_pack`) and not
  yet switched on from `grimble.toml`.
