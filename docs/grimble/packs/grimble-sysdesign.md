# The grimble-sysdesign pack

`packs/grimble-sysdesign` is a data pack (packs.md tier 1 manifest, GRL rules) that lints stores,
data and infrastructure design. It is embedded by `gob_packs::sysdesign` so it ships in the
binary.

## Layout

| Path | Reads | Content |
|---|---|---|
| `packs/grimble-sysdesign/pack.toml` | - | name, version, families, `provides.rules` |
| `packs/grimble-sysdesign/rules/STORE101.grl` | code (python, typescript) | STORE: Redis `KEYS` call, use `SCAN` |
| `packs/grimble-sysdesign/rules/SYSDESIGN101.grl` | `.grmb` model (`lang -`, `model.selectors`) | SYSDESIGN: a node owning `**` |
| `packs/grimble-sysdesign/rules/GRAMMAR101.grl` | `.grmb` model (`lang -`, `model.nodes`) | GRAMMAR: a node kind outside the core kinds |
| `packs/grimble-sysdesign/rules/grammar/GRAMMAR102.grl` | `.grmb` model (`lang -`, `model.nodes`) | GRAMMAR: a node name that is not lower snake_case |
| `packs/grimble-sysdesign/rules/grammar/GRAMMAR103.grl` | `.grmb` model (`lang -`, `model.nodes`) | GRAMMAR: a placeholder node name (`misc`, `tmp`) |
| `packs/grimble-sysdesign/rules/grammar/GRAMMAR104.grl` | `.grmb` model (`lang -`, `model.nodes`) | GRAMMAR: a node named after its own kind (advisory) |

Rules over store and infrastructure code join STORE, rules over the declared design join
SYSDESIGN, and rules over the model vocabulary itself join GRAMMAR. The model-reading rules use
`model` example inputs and `needs model`. Every rule has a firing and a clean example (the GRAMMAR102-104 rules also a not-applicable one) and an
`explain` with `## Remedy`; a rule without a firing and a clean example fails to compile
(GRL011).

## Lock

`sysdesign::locked(root, read)` returns the lock entry: the BLAKE3 tree digest over every file
under the pack directory. `sysdesign::verify_tree` refuses a tree that differs from the embedded
copy. `sysdesign::catalog()` yields the `grimble rule catalog` rows, one per family.

## Notes

- Family labels may be up to 12 letters (`SYSDESIGN`); the manifest family limit follows the
  rule id limit.
- A python call nested in `return` inside a `def` did not match `call` in the STORE101 firing
  example; the example uses a bare statement call.
- The pack is registered in code (`gob_packs::sysdesign`), like grimble-websec; `grimble.toml`
  enablement of GRL packs is not wired yet.
- GRAMMAR102 to GRAMMAR104 are the first slice of the family: naming discipline over `model.nodes`.
  Rules over fields and edges of the model language wait on richer model relations; GRL cannot put
  side relations inside quantifiers.
