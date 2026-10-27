# Agent ground rules

Status: current
Owner: frob
Decisions: D36
Audience: agents

How-to (Diataxis: task). The rules an implementer agent follows in this repository. The state
log and dispatch tables of the milestone-1 build are gone; the history is in the ledger and in
`git log`.

## Workflow

- Tickets are driven by the `frob` binary (`frob ticket ...`, `frob work`, `frob land`); never
  hand-edit the ledger (the `frob-tickets` branch). Ticket handles are `~` plus the unique suffix of the ULID.
- One worktree per ticket: `frob work <handle>` takes the lease and creates `../frob-wt/<id>` on
  branch `ticket/<id>`. Work only inside it and only inside the lease scope; widen with
  `frob lease widen <handle> --glob <path>` when SCOPE001 fires.
- Verify with `frob test --base experimental` and `frob check --ticket <handle>`, bind evidence
  with `frob ticket evidence add`, and let the coordinator run `frob land`. Do not pre-merge
  experimental by hand except as the ticket asks.
- A done-report cites the design section it implements and records any deviation as a
  decision-log proposal in [../design/README.md](../design/README.md).

## Rust rules

- Deny `missing_docs` and the clippy doc lints; one-line docstring on every public symbol.
- Fallible operations return `Result` with typed error sets; `tracing`, not `println!`, outside
  renderers (clippy denies `print_stdout`, `print_stderr`, `dbg_macro`); no `std::process` outside `gob-git` and `gob-exec`.
- Test with `cargo nextest`; `insta` snapshots; markdown corpora through `gob-mdtest`.

## Commits and files

- Conventional commit format, imperative summary of at most 72 characters, no `Co-Authored-By`
  line, ASCII only in every file.
- Docs in `docs/` are normative; notes under `notes/` are frozen evidence and are never edited
  after their decision lands (see [../../notes/README.md](../../notes/README.md)).
- Moved or removed docs are recorded in [../MOVED.toml](../MOVED.toml); see
  [moving-docs.md](moving-docs.md).

## Build hygiene

- Build one crate at a time with two jobs (`CARGO_BUILD_JOBS=2 cargo <verb> -j2 -p <crate>`),
  never the whole workspace, and prefer the release binary for `frob` itself.
