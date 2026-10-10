# Migration from v1 and rollout

Status: draft
Owner: frob
Decisions: D36, D95
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias).

Milestone 1 (D36) migrates only this repository's own tickets, by a
one-off script that mints ULIDs and writes the ledger; the verbs and
consumer-repo tooling below are Milestone 2 or later (D36).

D95 (owner decision 2026-10-05): the `frob migrate` verbs in section 1
(`tickets`, `config`, `directives`, `exceptions`) are dropped, not
deferred. Consumer repositories move from v1 to v2 by hand, one at a
time: write a fresh v2 `frob.toml` and `grimble.toml` from `frob init`
and the v1 file as reference, import tickets worth keeping with the
existing developer importer (`cargo dev import-v1-tickets` with a
selection file, as this repository did) or recreate them, and rewrite
directives and waivers as they are touched. The section 1 table stays as
the mapping a person follows; `grimble migrate` for `.strata` files is
unaffected.

## 1. What migrates

| v1 artifact | v2 handling |
|---|---|
| `tickets/T-####/ticket.md` + done-report.md (YAML) | `frob migrate tickets`: new ULID per ticket, minted from the v1 `created` timestamp plus random bits with ties inside a day broken by v1 number (so ULID order equals v1 order; v1 dates have day granularity, so ids cluster by day); `aliases = ["frob:T-0042"]` namespaced by source repo so a second imported ledger (`crunk:T-0042`) cannot collide, a bare `T-0042` resolving only when exactly one source has it; state/kind/tier mapped to type + status + outcome; audit tuples become event files; sprint strings become cycle objects when `YYYY-Www`, otherwise labels; semver sprints become milestones (release objects) |
| `frob:ticket T-0042` and friends in code | resolve through aliases; `frob migrate directives` rewrites them to the full ULID on request, otherwise aliases keep working while a TICK note lists them |
| `frob.lock` | re-emitted, but only after the digest scheme is final (universal-model.md 7.1, open question 5; build-test-ci.md Milestone 2 item 3): refs unchanged, digests recomputed under the final scheme with `digest_scheme` recorded (BLAKE3); only acks that were current under v1 are carried (each is re-verified with v1 hashing first) with a migration note in the ack log, and acks that were already stale are reported, never re-blessed; there is no bulk `ack --all` |
| `frob.toml` | `frob migrate config`: known keys mapped and split into `frob.toml` and `grimble.toml` by family (boundaries.md), `[gates.severity]` collapsed to the rows that differ from v2 defaults, profile mapped per rules.md section 7, unknown keys reported |
| `frob:waive RULE` ids | rule id map in `docs/migration/rule-ids.md` (many-to-one where a family collapsed); `frob migrate exceptions` rewrites waivers into exceptions (exceptions.md section 7), maps merged ids, and deletes waivers for dropped rules, reporting each |
| `design/*.strata` (v1) | `grimble migrate` accepts the v1 grammar and emits `design/*.grmb`: `code` to `owns` (fnmatch to path globs with a report of semantic changes), `attr interface=[...]` to `surface`, `may ... via` to `may ... at`; constructs with no v2 equivalent are listed, never silently dropped |
| `invariants/INV-*.md` | unchanged format; frontmatter validated; `decisions/` moves to `docs/decisions/<date>-<slug>.md` |
| `.frob/` | deleted; rebuilt |
| `fleet.toml` | unchanged shape |
| v1 tickets, open | selective (section 1.1): only tickets that carry requirements import as open work, labelled `v1-cluster:<id>` (plus `area:crunk` or `area:grimble` for the moved web-app and system-design families, D88 and D89); the rest are listed with a reason, not imported |
| v1 tickets' kind/tier | mapped to type and flavour; stories lacking structured user-story fields or quality-objective fields land in `triage` with PM003/PM020 findings rather than being refused, so history imports cleanly and the backlog is cleaned up through the normal triage flow |

### 1.1 Selective ticket import

Owner decision 2026-10-04: the 970 open v1 tickets are not imported wholesale.
`cargo dev import-v1-tickets` reads `docs/migration/v1-selection.toml`, a
checked-in mapping generated from `notes/review/v1-gap/B-backlog.md` and
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

## 2. Rollout

1. v2 reaches self-hosting on this repo (its own tickets, its own check);
   this repository's own `frob.lock` is empty today and is regenerated
   once the digest scheme is final. The milestone-2 order that gates the
   later steps is build-test-ci.md, Milestone 2.
2. Install side by side as `frob2`; run both on typani and crunk;
   compare findings (`frob2 compare --against frob`) until the diff is
   explained.
3. Consumer repos migrate one at a time with `frob2 migrate`, blocked
   until the digest scheme is final (otherwise every imported ack would
   drift when the scheme lands); v1 stays installed until the fleet is
   converted.
4. `frob2` becomes `frob`; v1 archived as the `v1` branch.

## 3. Compatibility promises

- File-based symrefs unchanged, so directives in consumer code keep
  working; the new locator forms and anonymous-unit indexes of
  code-model.md section 2 are additive.
- Rule family names unchanged; ids inside families mapped.
- Old `T-####` ids resolve forever through source-namespaced aliases
  (`frob:T-0042`, `crunk:T-0042`); a bare `T-0042` resolves only when
  exactly one imported source has it.
