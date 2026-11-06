# Ticket import selection files

Status: current
Owner: frob
Decisions: D95
Audience: contributor

The importers read a selection file instead of importing every open ticket: [v1-selection.toml](v1-selection.toml) for the frob v1 ledger ([v1 ticket import](v1-import.md)) and [crunk-selection.toml](crunk-selection.toml) for crunk ([crunk ticket import](crunk-import.md)). Both use one format. Design rationale is in [Migration from v1 and rollout](../design/frob/migration.md); the consumer-repository steps are in the [upgrade guide](upgrade-from-v1.md).

## Format and behaviour

Owner decision 2026-10-04: the 970 open v1 tickets are not imported wholesale.
`cargo run -p frob-evidence --example import_v1` reads `docs/migration/v1-selection.toml`, a
checked-in mapping generated from `notes/v1/gap/B-backlog.md` and
reviewed like any other change. The selection is data:

- Closed v1 tickets (done, archived, dropped) always import as closed history,
  outcome preserved, v1 id as alias (`history-done`, `history-dropped`).
- Each cluster of the report names its v1 ids and one disposition.
  `import-open` is for DESIGNED and MISSING clusters: the ticket imports as
  open work with the label `v1-cluster:<id>`; the system-design (B1) and
  web-app (B2) families also get an `area:` label per D89: `area:crunk` for
  A11Y, SEO, LAUNCH and front-end WEBPERF, `area:grimble` for WEBSEC, SQL,
  COMPLY, ROUTE, server WEBPERF and all of B1. The cluster carries the default
  and the `[area]` table sets single tickets by family.
  `skip-dropped-on-purpose`, `skip-built`, `skip-v1-internal`,
  `skip-ticketed` and `skip-superseded` import nothing and are listed in the
  dry run with their reason. `wont-fix-history` imports a closed wont-fix
  ticket carrying the reason, for a cluster the owner wants kept as history.
- An `[override."T-nnnn"]` entry moves one ticket out of its cluster's
  disposition (a live gap the report names inside a built or internal cluster,
  or a ticket v2 already tracks).
- An open v1 ticket that no cluster or override names stops the run, so the
  selection cannot silently go stale.
- `--dry-run` prints counts per disposition, the skipped tickets per
  cluster, every open ticket that would import with its cluster, and the
  redaction notes; `--all` restores the unselective import.

- `--merge` lets `--to` be an existing v2 ledger instead of an empty one: only
  new ticket directories are written, and the run refuses up front, before
  writing anything, if any generated id or alias collides with the ledger.
  Redaction and the home-path rule apply as for a fresh import. The importer
  does not commit; the files are left for the caller to commit.
- `--open-category triage|todo` (default `todo`) sets the category in the
  create event of imported open tickets; closed history is unaffected.

Imported text is redacted before it becomes an event, with the same rules as
the ledger write path: absolute home paths become `<repo>`, `~` or `~other`,
and local private-term rules (`privacy.toml` in the user config and the git
common dir) replace each term with its label. Hits are reported by rule label
and hash, never by the matched text; a path that survives redaction blocks a
real import. A dry run can only find private terms that the local rule files
already hold, so run it on the machine that has them.
