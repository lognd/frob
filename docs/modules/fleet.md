# frob.fleet -- cross-repo status, gate rollup, and ticket routing (T-0573)

One sentence: `frob fleet status` reads a small `fleet.toml` manifest of
sibling repos, probes each one (git branch/dirty state, a `frob check
--json` gate summary, its own doable-ticket count), and rolls the result
into one reddest-first table or JSON payload; `frob fleet route` files a
ticket directly into a named sibling's own ledger.

## Why this exists

The 9-repo compliance campaign (frob plus 8 sibling repos each wired to
run `frob check`/`frob ticket` of their own) was coordinated by hand, from
coordinator memory files: "how red is the estate right now" and "which
repo does this finding belong in" were both answered by opening nine
terminals and eyeballing them, or by writing prose into a memory file that
drifted from reality the moment any sibling repo moved. `frob fleet` makes
both of those one command with a typed, testable answer.

## Manifest (`fleet.toml`)

```toml
[[repo]]
name = "frob"
path = "."

[[repo]]
name = "typani"
path = "../typani"
```

- `name` -- the short identifier used by `frob fleet route --repo NAME`.
- `path` -- the repo's filesystem path. A relative path is resolved
  against the MANIFEST FILE's own directory (not the process cwd), so a
  `fleet.toml` committed at a repo root with `path = "../typani"` always
  means "the sibling checkout next to this repo", regardless of where
  `frob fleet` happens to be invoked from.

Default manifest path is `./fleet.toml` (`frob.fleet.DEFAULT_MANIFEST_PATH`);
override with `--manifest PATH` on either subcommand, or `[tool.frob]
fleet_manifest` in `pyproject.toml`.

`load_manifest(path) -> Result[FleetManifest, FleetError]` (`frob.fleet`)
is the public entry point: `Err(ManifestNotFound)` when the file is
missing, `Err(ManifestMalformed)` on any TOML/schema failure -- never a
bare exception.

## Gate summary

`GateSummary` (`error_count`, `warn_count`, `exit_code`) is the
severity-bucketed violation count parsed from one repo's `frob check
--json` probe -- see Collect below for what a failed probe degrades to.

## Repo status

`RepoStatus` (`name`, `path`, `branch`, `dirty`, `gates`, `doable_count`,
`error`) is one repo's full collected row -- see Collect below.

## Fleet report

`FleetReport` (`repos: tuple[RepoStatus, ...]`) is `rollup`'s output --
see Rollup below for the reddest-first ordering.

## Collect

`collect_status(entry, *, probe_gates=True) -> RepoStatus` builds one
repo's full status row:

- **branch/dirty** -- a bare `git status --porcelain=v2 --branch`
  subprocess in the repo's own directory; a `git` failure (missing repo,
  detached HEAD, `git` unavailable) degrades to `branch=None`/`dirty=False`
  rather than raising.
- **gates** (`GateSummary`) -- `error_count`/`warn_count` parsed from a
  `uv run --project <repo> frob check --json` subprocess probe in the
  repo's own directory, bounded by a 120s timeout. The probe deliberately
  NEVER shells a bare `frob` off `PATH`: this machine's PATH `frob` is a
  documented stale global (docs/guides/agent-playbook.md section 2), and
  a bare-`frob` probe would silently report every sibling's gate counts
  from the WRONG binary while looking exactly as trustworthy as a correct
  one. `--project <repo>` pins `uv` to that sibling's own environment/
  pinned `frob`, matching the `uv run frob ...` convention this repo's
  own playbook mandates everywhere else. Any failure (missing `uv`,
  timeout, non-JSON output) degrades to a zeroed `GateSummary` rather than
  aborting the whole rollup -- pass `--skip-gates` (`frob fleet status
  --skip-gates`) to skip the probe entirely and only report git/ticket
  state, when a fast answer matters more than gate freshness.
- **doable_count** -- the repo's own `frob.tickets.doable` count, read
  directly via `frob.tickets.load_queue` (no subprocess) against that
  repo's `tickets.md`; a missing/malformed ledger degrades to `0` (logged),
  since a sibling with no ledger yet is not the fleet rollup's problem to
  fail on.

A nonexistent `entry.path` short-circuits to a zeroed `RepoStatus` with
`error` set, before any subprocess is attempted.

## Rollup

`rollup(manifest, *, probe_gates=True) -> FleetReport` calls
`collect_status` over every manifest entry and sorts REDDEST-FIRST: most
gate errors, then most warnings, then most doable tickets. The worst-off
repo in the estate is always row one -- the whole point of a fleet view is
never having to eyeball nine rows to find the one that is on fire.

`frob fleet status [--manifest PATH] [--json] [--skip-gates]` prints the
rollup as a table (repo/branch/dirty/errors/warns/doable/note) or, with
`--json`, the full `FleetReport` payload.

## Routing

`route_ticket(manifest, repo_name, spec) -> Result[str, FleetError]` files
one `frob.tickets.TicketSpec` directly into the named sibling's own ledger
via `frob.tickets.new_ticket(root=<that repo's path>, spec)` -- no second
`frob` process spawned, no copy-paste into a coordinator memory file.
Returns the new ticket's id on success.

`frob fleet route --repo NAME --title TEXT [--kind K] [--priority P]
[--scope GLOB...] [--body TEXT]` is the CLI form; `--kind` defaults to
`bug` and `--priority` to `medium` (matching `frob ticket new`'s own
defaults). Every routed ticket is filed with `origin=agent`.

Failure modes are typed, never a bare exception:

| `FleetError` | Meaning |
|---|---|
| `ManifestNotFound` | the manifest file does not exist |
| `ManifestMalformed` | the manifest failed to parse as `[[repo]]` TOML |
| `RepoNotFound` | no manifest entry with that name |
| `RepoPathMissing` | the manifest entry's path does not exist on disk |
| `RouteFailed` | the target has no ticket ledger at all (neither `tickets.md` nor a legacy `tickets/` dir -- not a frob-enabled repo), or the underlying `frob.tickets.new_ticket` call failed (a locked/malformed target ledger, an unleased worktree, ...) |

`route_ticket` checks for an existing ledger (`tickets.md` or a legacy
`tickets/` dir) BEFORE calling `new_ticket`, and refuses with
`RouteFailed` when neither exists. Without this check, routing into a
directory that was never wired for frob would silently BOOTSTRAP a
brand-new ledger there via `new_ticket`'s own create-on-first-write
behavior -- correct for a human deliberately initializing a repo, wrong
for a fleet-routed finding landing in some unrelated directory by typo.

## Not yet built

Routing files a ticket into a target repo's ledger one at a time, driven
by a caller who already knows which repo a finding belongs in. There is no
automatic classifier that reads a finding and decides which sibling owns
it -- that remains a human/agent judgment call, same as before T-0573.
