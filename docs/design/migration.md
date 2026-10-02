# Migration from v1 and rollout

Status: DRAFT (T-0001, a v1-format id that migrates with an alias).

Milestone 1 (D36) migrates only this repository's own tickets, by a
one-off script that mints ULIDs and writes the ledger; the verbs and
consumer-repo tooling below are Milestone 2 or later (D36).

## 1. What migrates

| v1 artifact | v2 handling |
|---|---|
| `tickets/T-####/ticket.md` + done-report.md (YAML) | `frob migrate tickets`: new ULID per ticket, minted from the v1 `created` timestamp plus random bits with ties inside a day broken by v1 number (so ULID order equals v1 order; v1 dates have day granularity, so ids cluster by day); `aliases = ["frob:T-0042"]` namespaced by source repo so a second imported ledger (`crunk:T-0042`) cannot collide, a bare `T-0042` resolving only when exactly one source has it; state/kind/tier mapped to type + status + outcome; audit tuples become event files; sprint strings become cycle objects when `YYYY-Www`, otherwise labels; semver sprints become milestones (release objects) |
| `frob:ticket T-0042` and friends in code | resolve through aliases; `frob migrate directives` rewrites them to the full ULID on request, otherwise aliases keep working while a TICK note lists them |
| `frob.lock` | re-emitted: refs unchanged, digests recomputed (BLAKE3); only acks that were current under v1 are carried (each is re-verified with v1 hashing first) with a migration note in the ack log, and acks that were already stale are reported, never re-blessed; there is no bulk `ack --all` |
| `frob.toml` | `frob migrate config`: known keys mapped and split into `frob.toml` and `grimble.toml` by family (boundaries.md), `[gates.severity]` collapsed to the rows that differ from v2 defaults, profile mapped per rules.md section 7, unknown keys reported |
| `frob:waive RULE` ids | rule id map in `docs/migration/rule-ids.md` (many-to-one where a family collapsed); `frob migrate exceptions` rewrites waivers into exceptions (exceptions.md section 7), maps merged ids, and deletes waivers for dropped rules, reporting each |
| `design/*.strata` (v1) | `grimble migrate` accepts the v1 grammar and emits `design/*.grmb`: `code` to `owns` (fnmatch to path globs with a report of semantic changes), `attr interface=[...]` to `surface`, `may ... via` to `may ... at`; constructs with no v2 equivalent are listed, never silently dropped |
| `invariants/INV-*.md` | unchanged format; frontmatter validated; `decisions/` moves to `docs/decisions/<date>-<slug>.md` |
| `.frob/` | deleted; rebuilt |
| `fleet.toml` | unchanged shape |
| v1 tickets' kind/tier | mapped to type and flavour; stories lacking structured user-story fields or quality-objective fields land in `triage` with PM003/PM020 findings rather than being refused, so history imports cleanly and the backlog is cleaned up through the normal triage flow |

## 2. Rollout

1. v2 reaches self-hosting on this repo (its own tickets, its own check).
2. Install side by side as `frob2`; run both on typani and crunk;
   compare findings (`frob2 compare --against frob`) until the diff is
   explained.
3. Consumer repos migrate one at a time with `frob2 migrate`; v1 stays
   installed until the fleet is converted.
4. `frob2` becomes `frob`; v1 archived as the `v1` branch.

## 3. Compatibility promises

- Symref grammar unchanged, so directives in consumer code keep working.
- Rule family names unchanged; ids inside families mapped.
- Old `T-####` ids resolve forever through source-namespaced aliases
  (`frob:T-0042`, `crunk:T-0042`); a bare `T-0042` resolves only when
  exactly one imported source has it.
