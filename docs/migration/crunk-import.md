# crunk ticket import

Status: current
Owner: frob
Decisions: none
Audience: contributor

Selective import of the crunk repository's tickets into frob, built for the crunk retirement (~JBTM6EF). The conversion is the v1 importer ([v1 ticket import](v1-import.md)) with a source namespace; only the selection differs.

## Source

crunk keeps no GitHub issues. Its tickets are a v1 `tickets/T-NNNN/{ticket.md,done-report.md}` tree on `main` of `lognd/crunk`. The runner makes one shallow, read-only `gh repo clone lognd/crunk -- --depth=1 --branch=main` (no pagination, no truncated trees) and reads its `tickets/`. `--from <dir>` uses an existing `tickets/` directory instead.

GitHub `main` holds T-0001..T-0141 (116 done, 9 dropped, 15 open). The retirement ticket talks of about 250 tickets up to T-0294; the rest is unpushed local state. Push crunk first and re-run the dry run: the selection already names those ids, and any open ticket it does not name stops the run.

## Run

```
cargo run -p frob-evidence --example import_crunk                 # dry run, fetches with gh
cargo run -p frob-evidence --example import_crunk -- --from DIR   # dry run on an extracted tree
cargo run -p frob-evidence --example import_crunk -- --write      # the real import (retirement step)
```

The dry run prints the count per disposition, every open ticket that would import, and every open ticket kept out of open work with its disposition, cluster and reason. It writes nothing.

## Dispositions

`docs/migration/crunk-selection.toml` maps each open crunk ticket. Closed tickets (done, dropped) import as closed history.

| Disposition | Meaning |
|---|---|
| `import-open` | created as open work (area crunk) |
| `wont-fix-history` | created closed, outcome wont-fix, reason kept; used for frob-friction trackers and repo housekeeping |
| `skip-ticketed` | already covered by a frob ticket, nothing imported |

## Identity

Every imported ticket gets the alias `crunk:T-nnnn` and the labels `component:crunk` and `source:crunk`. Aliases resolve by exact string, so `crunk:T-0042` can never be a frob `T-0042`. New ULIDs are minted from the crunk created date, so ids do not collide either.

## Re-runs

The write merges into the existing ledger and refuses on any id or alias collision before writing anything, so a second `--write` fails with the colliding aliases instead of duplicating tickets.
