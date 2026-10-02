# Coordinator state (survives context summarization; keep current)

Role: the main session coordinates; Sonnet `implementer` agents do the
work one ticket at a time inside frob worktrees; `reviewer` agents
verify done-reports only when something smells wrong.

## Ground rules for every implementer dispatch

- Ticketing uses the INSTALLED v1 frob (`frob ticket ...`, never hand-edit
  `tickets/`). Ticket ids are v1 `T-####` in this repo until v2 self-hosts;
  the v2 design's ULID ids apply to repos frob v2 manages.
- Work in a worktree per ticket (`frob ticket work T-####`), stay in scope,
  commit with the conventional format, no Co-Authored-By, ASCII only.
- Rust rules from the design: deny `missing_docs` and clippy doc lints from
  the first commit; `Result` with typed error sets (trial `error_set`
  in frob-ledger first, else `thiserror`); `tracing` not `println!`
  outside renderers; no `std::process` outside `gob-git` and `gob-exec`;
  `cargo nextest`; `insta` snapshots; markdown corpora via `gob-mdtest`.
- Design is authoritative: docs/design/*.md (README.md is the index and
  decision log). Evidence: notes/. Audit findings: notes/audit-design.md.
- A ticket's done-report must cite the design section it implements and
  record any deviation as a decision-log entry proposal.

## Milestone 1 (self-hosting): frob v2 checks this repository

Decision D36; cut table at the end of notes/audit-design.md. Epic T-0002
(milestone 2.0.0). Children, in dependency order (blocked-by edges are
in the ledger; `frob ticket doable` is the dispatch queue):

| Ticket | Crates | Pts | Blocked by |
|---|---|---|---|
| T-0003 | workspace skeleton, gob-dev stub, gob-text stub | 5 | - |
| T-0004 | gob-text | 3 | T-0003 |
| T-0005 | gob-rules, gob-macros (Rule derive) | 8 | T-0004 |
| T-0006 | gob-config (+ConfigTable derive) | 5 | T-0005 |
| T-0007 | gob-log | 2 | T-0003 |
| T-0008 | gob-diagnostics | 5 | T-0005 |
| T-0009 | gob-exec | 3 | T-0007 |
| T-0010 | gob-git | 8 | T-0007, T-0009 |
| T-0011 | gob-walk, gob-cache | 5 | T-0004 |
| T-0012 | gob-languages | 5 | T-0004 |
| T-0013 | gob-symbols | 13 | T-0012, T-0011 |
| T-0014 | gob-directives (+Directive derive) | 8 | T-0013, T-0005 |
| T-0015 | gob-mdtest | 3 | T-0005 |
| T-0016 | gob-dev gen, GEN001 | 5 | T-0006, T-0008, T-0014, T-0015 |
| T-0017 | gob-cli, frob bin (+Command derive) | 5 | T-0006, T-0008 |
| T-0018 | frob-ledger (+TicketField derive) | 13 | T-0010, T-0017 |
| T-0019 | frob-lease, frob-worktree | 8 | T-0018 |
| T-0020 | frob-evidence, frob-tests | 8 | T-0018, T-0009, T-0013 |
| T-0021 | gob-lock, frob-ack | 8 | T-0013, T-0014, T-0017 |
| T-0022 | frob-obligations | 8 | T-0021, T-0018, T-0015 |
| T-0023 | frob-check | 8 | T-0022, T-0020, T-0011, T-0015 |
| T-0024 | frob-land | 8 | T-0023, T-0019 |
| T-0025 | self-host switch | 5 | T-0024 |

Milestone 2 backlog to file when M1 closes: salsa par_map spike (audit
M11), ast-grep tree-sitter unification spike (M26), gob-ir and universal
rules, grimble crates, crunk crates, serve/GUI, daemon, PM cycles and
forecasts, exception kinds hotfix and baseline, migration tooling.

## Implementer workflow (v1 frob drives v2 work)

1. Coordinator runs `frob ticket work T-#### --worktree ../frob-v2-wt/t-####
   --foreground` from the primary root (lease holder is the coordinator's
   identity; one worktree per ticket; base and land target = experimental).
2. Implementer works only inside that worktree and only inside the ticket
   scope (`frob ticket show T-####` lists it). Design docs are read from
   the primary checkout path /home/logan/projects/frob-v2/docs/design
   until they are committed there.
3. Verification inside the worktree: `cargo fmt --check`, `cargo clippy
   --all-targets -- -D warnings`, `cargo nextest run`, `RUSTDOCFLAGS="-D
   warnings" cargo doc --no-deps`.
4. Close dance (order matters): commit -> `frob ticket close T-####
   --evidence-cmd "<cargo nextest command>" --accepts 1 --accepts 2 ...`
   is run by the COORDINATOR after review of the implementer report, then
   `frob ticket land T-####` from the primary root. Rust-only scopes are
   allowed cmd evidence (v1 T-3156 rule). Implementers do not close or
   land; they commit and report.
5. Cargo.lock is an append-shared registry file (frob.toml
   `[tickets] registry_files`), exempt from leases.

### v1 land quirks learned on T-0003 (apply to every land)

- Run `frob ticket land T-#### --worktree ../frob-v2-wt/t-####` from the
  primary root; the primary must be clean (no uncommitted files of any
  other ticket's scope).
- Deletions are matched against literal scope paths, not globs: a ticket
  that deletes a file must list the exact path in its scope at filing
  time (scope changes made later do not reach the worktree ledger copy).
- The land merges experimental into the worktree before checking, and
  its touched set is computed from the original fork point, so a branch
  that has absorbed experimental merges counts everything merged in as
  its own. If a land refuses on files the ticket never touched, rebase
  the worktree branch onto experimental first (ticket.md conflicts: keep
  both sides).
- The land-time DOC006 check matches any finding whose message contains
  a touched file name; config-pointer messages all contain "Cargo.toml",
  so any DOC006 anywhere blocks any land touching Cargo.toml. Planned
  paths and config tables in docs/notes carry inline
  `<!-- frob:waive DOC006 reason="..." -->` on the line above. Ticket
  bodies must not contain `[section.key]` TOML pointers.
- A removed `frob:waive` comment in a deleted or rewritten v1 file must
  be named in the done-report text (file:RULE) or the land refuses.

## Status log (newest first)

- 2026-10-02 (evening): landed T-0004 T-0007 T-0026 T-0009 T-0012 T-0005
  T-0011 (9/24 done, 66 tests). Land takes experimental's Cargo.lock, so
  the coordinator regenerates and commits the lock after every land; do
  NOT pre-merge experimental into worktrees. File deletions are done by
  the coordinator in the primary after the land. Design reconciliation
  owed: cache file name (architecture.md says cache.db, code uses
  cache.sqlite); tree-sitter pinned at core 0.27.0 with ast-grep-core
  0.45.3 compatible (audit M26 answered). Dispatched T-0006 T-0008
  T-0010 T-0013 T-0015 in parallel.

- 2026-10-02 (later): docs/notes committed under T-0001 (fe510db);
  T-0003 landed (fc3dd9e) after four v1 land refusals (see quirks
  above); T-0026 filed for .github cleanup and .gitattributes; T-0004
  and T-0007 worktrees created and implementers dispatched in parallel.

- 2026-10-02: audit received (9 H / 36 M / 22 L); decisions D23-D37
  written in docs/design/README.md; fixer agent propagating them through
  docs/design and writing notes/audit-resolution.md. Gutting committed
  (d45ba3a) so worktrees start clean; check_base = experimental. M1 epic
  T-0002 and children T-0003..T-0025 filed. T-0003 worktree created at
  ../frob-v2-wt/t-0003; implementer dispatched. docs/ and notes/ are
  still uncommitted in the primary (commit after the fixer finishes).

- 2026-10-02: design set complete (17 files); audit dispatched; waiting
  to file the M1 ticket tree from its milestone-1 cut.
