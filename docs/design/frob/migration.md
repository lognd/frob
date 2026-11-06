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
existing developer importer (`cargo run -p frob-evidence --example import_v1` with a
selection file, as this repository did) or recreate them, and rewrite
directives and waivers as they are touched. The section 1 table stays as
the mapping a person follows. There is no `.strata` migration path (D136):
because grimble is not strata's successor and strata is deprecated, a `.strata`
model is rewritten by hand as `.grmb`, with no tool.

## 1. What migrates

| v1 artifact | v2 handling |
|---|---|
| `tickets/T-####/ticket.md` + done-report.md (YAML) | `frob migrate tickets`: new ULID per ticket, minted from the v1 `created` timestamp plus random bits with ties inside a day broken by v1 number (so ULID order equals v1 order; v1 dates have day granularity, so ids cluster by day); `aliases = ["frob:T-0042"]` namespaced by source repo so a second imported ledger (`crunk:T-0042`) cannot collide, a bare `T-0042` resolving only when exactly one source has it; state/kind/tier mapped to type + status + outcome; audit tuples become event files; sprint strings become cycle objects when `YYYY-Www`, otherwise labels; semver sprints become milestones (release objects) |
| `frob:ticket T-0042` and friends in code | resolve through aliases; `frob migrate directives` rewrites them to the full ULID on request, otherwise aliases keep working while a TICK note lists them |
| `frob.lock` | re-emitted, but only after the digest scheme is final (shared/universal-model.md 7.1, open question 5; shared/build-test-ci.md Milestone 2 item 3): refs unchanged, digests recomputed under the final scheme with `digest_scheme` recorded (BLAKE3); only acks that were current under v1 are carried (each is re-verified with v1 hashing first) with a migration note in the ack log, and acks that were already stale are reported, never re-blessed; there is no bulk `ack --all` |
| `frob.toml` | `frob migrate config`: known keys mapped and split into `frob.toml` and `grimble.toml` by family (shared/charter.md), `[gates.severity]` collapsed to the rows that differ from v2 defaults, profile mapped per docs/design/shared/rules.md section 7, unknown keys reported |
| `frob:waive RULE` ids | rule id map (planned, `docs/design/shared/rules.md` section 7) (many-to-one where a family collapsed); `frob migrate exceptions` rewrites waivers into exceptions (docs/design/shared/rules.md section 10.7), maps merged ids, and deletes waivers for dropped rules, reporting each |
| `invariants/INV-*.md` | unchanged format; frontmatter validated; `decisions/` moves to `docs/decisions/<date>-<slug>.md` |
| `.frob/` | deleted; rebuilt |
| `fleet.toml` | unchanged shape |
| v1 tickets, open | selective (section 1.1): only tickets that carry requirements import as open work, labelled `v1-cluster:<id>` (plus `area:crunk` or `area:grimble` for the moved web-app and system-design families, D88 and D89); the rest are listed with a reason, not imported |
| v1 tickets' kind/tier | mapped to type and flavour; stories lacking structured user-story fields or quality-objective fields land in `triage` with PM003/PM020 findings rather than being refused, so history imports cleanly and the backlog is cleaned up through the normal triage flow |

### 1.1 Selective ticket import

Owner decision 2026-10-04: the 970 open v1 tickets are not imported wholesale. The importer reads a checked-in selection file, reviewed like any other change, so the choice of what becomes open work is data and cannot silently go stale (an unmapped open ticket stops the run). The mechanics live in the migration pages, kept there once: [selection files](../../migration/selection.md) (dispositions, overrides, flags, redaction), [v1 ticket import](../../migration/v1-import.md) and [crunk ticket import](../../migration/crunk-import.md). The step-by-step for a consumer repository is the [upgrade guide](../../migration/upgrade-from-v1.md).

## 2. Rollout

The original rollout plan (side-by-side `frob2`, then the rename) is kept in [v1 migration history](../../history/migration-v1.md); v1 consumers now follow the [upgrade guide](../../migration/upgrade-from-v1.md).

## 3. Compatibility promises

- File-based symrefs unchanged, so directives in consumer code keep
  working; the new locator forms and anonymous-unit indexes of
  docs/design/shared/code-model.md section 2 are additive.
- Rule family names unchanged; ids inside families mapped.
- Old `T-####` ids resolve forever through source-namespaced aliases
  (`frob:T-0042`, `crunk:T-0042`); a bare `T-0042` resolves only when
  exactly one imported source has it.

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D95

Owner decision 2026-10-05: the consumer `frob migrate` verbs (tickets, config, directives, exceptions; migration.md section 1) are dropped, not deferred; v1 repositories move to v2 by hand, using `frob init`, the section 1 mapping table and the developer importer `cargo run -p frob-evidence --example import_v1`; epic ~7EHD37P closed wont-fix; `grimble migrate` for `.strata` was unaffected here, removed later by D136

### D136

Owner decision 2026-10-09: grimble is not strata's successor and strata is deprecated; the `.strata` migration path is removed (no `grimble migrate`, no v1 grammar import), and a `.strata` model is rewritten by hand as `.grmb`; drops ~X85A7ZD
