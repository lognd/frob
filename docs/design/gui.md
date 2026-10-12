# Stateless GUI

Status: draft
Owner: frob
Decisions: D36
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction: eventually a GUI (TUI or a
small local server with a TypeScript/React front end) that runs the
CLI under the hood and gives Jira's interactability without Jira's
state.

Milestone 2 or later (D36): this whole file (web GUI, SSE, TUI).

## 1. Principle

The GUI holds no state. Every screen is a projection of repo files
through the same handlers the CLI uses; every action is a CLI verb
with the same validation, the same events, the same commits. Closing
the tab loses nothing; two people (or an agent and a person) can use
the GUI and the CLI at once because the ledger is the only truth.

## 2. Architecture

- `frob serve --http` (crate `frob-serve` on `gob-serve`, axum, the
  same tokio leaf as MCP)
  serves a static React SPA from the binary (embedded with
  `rust-embed`) and a JSON API that is a 1:1 mapping of the CLI verbs:
  `POST /api/ticket/update` carries the same arguments as `frob ticket
  update --json`, validated by the same clap-derived types, dispatched to
  the same handler in-process. No shelling out, no second code path.
- Reads use the warm salsa db; a file watcher (notify) invalidates
  inputs, debounced so a busy editor cannot cancel a long `check`
  (architecture.md section 9), and pushes changes to the browser over
  Server-Sent Events, so a ticket moved by an agent appears on the board
  within a second.
- Auth: `frob serve` is read-write, so it is never open. A random token
  is generated per launch and is mandatory on every request (printed URL
  carrying the token, then an HttpOnly cookie or an `Authorization`
  header). Origin and Host must match the bound address or the request
  is refused, which closes cross-site form posts and DNS rebinding.
  Mutations require `Content-Type: application/json`, a non-simple type
  a cross-site form cannot send. The server binds to localhost; a LAN
  bind is an explicit flag and still requires the token. There is no
  user model beyond git identity; the GUI records `actor` from `git
  config user.name` like the CLI, which is a label, so the token is the
  only access control.
- TypeScript types for every request and response are generated from
  the same schemars output as `--json`, so the front end cannot drift
  from the CLI (`cargo dev gen ts` writes `web/src/api.ts`).

## 3. Screens (first cut)

| Screen | Backed by |
|---|---|
| board (columns by status category, swimlanes by epic or assignee, WIP limits, drag to transition with the same guards) | `ticket query`, the transition verbs (`start`, `requeue`, `review`, `close`) |
| backlog (rank by drag, bulk update, cycle planning) | `ticket query`, `ticket update --set rank=...`, `cycle assign` |
| ticket page (frontmatter, body, events timeline, comments, evidence verdicts, links graph, lease holder) | `ticket show --json`, `comment`, `link` |
| doable and contention (what agents will pick next, hot files) | `ticket doable`, `contention` |
| landing (a land in progress seen through the land lock and events, LAND-PROOF, failures with remedy) | `land` (synchronous), `ticket show --events` |
| cycles and forecasts (velocity, capacity, burndown, P50/P85 dates, commitment ratio) | `cycle velocity`, `forecast`, `stats` (pm-enforcement.md) |
| triage inbox (accept, decline, snooze, duplicate) | `ticket triage ...` |
| design (grimble model graph with per-node drift, capability matrix) | `grimble status --json`, `grimble graph --json` (grimble is a sibling binary; the GUI calls it like any other verb) |
| check (findings grouped by rule with remedies, accept or defer from the UI writes the exception directive) | `check --json`, `fix` |

## 4. TUI

A separate binary, `frob-live` (crate frob-live, ratatui), shipped in the
frob wheel beside `frob` and reached as `frob board --live` and `frob stats
--live` (D104, D105): frob execs the sibling binary found next to itself, so
the `frob` binary links no TUI and there is no `tui` verb. It redraws the
same view types the text and JSON renderings use (frob-pm board, frob-metrics
stats), refreshing on ledger, worktree and file changes, like clocx's
`--live` mode.

## 5. What is deliberately not built

No notifications service, no accounts, no hosted mode, no database.
If a team needs sharing, they push the repo.
