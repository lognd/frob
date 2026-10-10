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

## Implementer workflow (frob v2 self-hosted, from 2026-10-04)

The repository is checked and ticketed by the v2 binary. Build it with
`CARGO_TARGET_DIR=<worktrees>/.target cargo build -p
frob-cli` and call `$CARGO_TARGET_DIR/debug/frob` (alias F). Verbs:
`F ticket doable`, `F work <handle>` (worktree under ../frob-v2-wt/,
branch ticket/<handle>, lease taken), implement, `F test --base
experimental`, `F ticket evidence add <handle> --provider command --ref
"<cargo nextest ...>" --accepts N`, `F check --ticket <handle>`, then
the coordinator runs `F land <handle>`. Ticket ids are ULIDs; handles
are `~` plus the unique suffix; directives use full ULIDs. The v1 tool
is no longer used in this repository. The old section below is kept
for history.

## Implementer workflow until the cutover (v1 frob drove v2 work)

1. Coordinator runs `frob ticket work T-#### --worktree ../frob-v2-wt/t-####
   --foreground` from the primary root (lease holder is the coordinator's
   identity; one worktree per ticket; base and land target = experimental).
2. Implementer works only inside that worktree and only inside the ticket
   scope (`frob ticket show T-####` lists it). Design docs are read from
   the primary checkout path docs/design
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

### Resource rules (learned 2026-10-03 after a disk-full event)

- Every worktree builds its own target/ (15-19 GB each). The disk event
  came from 24 v1 worktrees that were never removed; `frob land` now
  removes each worktree with its target/. A SHARED target dir was tried
  and retired (2026-10-04): diverging worktrees reuse each other's
  workspace-crate artifacts (phantom compile errors), and the landing
  binary got overwritten by agent builds. The landing binary is
  F=<frob-v2>/target/debug/frob, built only in the
  primary from experimental. <worktrees>/.cargo/
  config.toml caps jobs at 4 and sets no target-dir.
- At most two implementers building at once.
- Two Claude Code crashes (one Bun bus error) happened while long
  background shells ran; keep shell steps short and in the foreground.

### Disk-full prevention (decided 2026-10-04 after the third disk event)

- A user-level PreToolUse hook (~/.claude/hooks/disk-guard.py, matcher
  Bash|Agent) refuses builds, test runs, frob work/test/land/check,
  uvx, worktree creation and agent dispatches when free space on / is
  under 80 GB (DISK_GUARD_MIN_GB); cleanup and inspection always pass.
- Worktree builds use line-tables-only debug info and no incremental
  cache (<worktrees>/.cargo/config.toml).
- At most two building agents; delete a stopped worktree's target/
  immediately; never recreate a shared target dir.

### Evidence covers the whole workspace (decided 2026-10-04)

The land gate runs `frob check`, not the test suite, and per-package
evidence let a ticket land while other crates' tests were broken (the
directive ticket left three frob-cli tests stale). Code tickets record
evidence with `cargo nextest run --profile ci` over the WHOLE workspace;
the coordinator runs the full suite on experimental after each land
that touches shared crates.

### Format-bump lands (decided 2026-10-04 on G05)

A ticket that changes an on-disk format the landing binary reads (for
example frob.lock version 2) is landed with a copy of the binary built
in that ticket's worktree, because the old binary cannot read the new
format; immediately afterwards the landing binary is rebuilt from
experimental. Record such lands in the status log.

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

- 2026-10-07 (night): owner: profile every command, profiling in CI, fix
  experimental, audit, adjust plan, burn down; follow scrum with frob
  enforcing it; usable for another project soon. CI red since 10-06 16:25
  (Windows ui_rule_attr OS error text, ~1ZE1H1X). Stale cycle ~VCCMDF6
  closed with retro; sprint ~XAFQ008 (10-07..10-09) planned; every
  dispatched ticket must be a sized cycle member. Global frob = v2 debug
  copy (~/.local/opt/frob-v2/current), v1 kept as frob-v1 for MCP serve and
  the vet hook. Audit: notes/review/audit-2026-10-07.md, epic ~TNT2Q1E.
  Until ~GHMWDGG lands, check `gh run list` on experimental before each
  land batch (lands must not go onto a red base).

- 2026-10-06 (evening): 36 landed today (web engine through gob-frameworks,
  C#, product front end, ruff/ty test infrastructure, CI hygiene, GRL
  printer, ticket-branch bootstrap, crunk COLOR001, grimble SYS013). Design
  D96-D107. Owner paused goway at the end; agents use local scoped builds.
  Unlanded: ~9R52NCF spike (works; needs remote evidence), ~2DRPX3B,
  ~A6JJ764 (CLI trim). Resume point and next dispatch order: memory file
  frob-v2-session-2026-10-06. Land recovery recipes: E-LAND-NOT-LEASED ->
  requeue from primary + start from worktree; E-DONE-NO-CRITERIA -> add
  criteria + re-record evidence; match errors case-insensitively.

- 2026-10-06 (later): 15 landed: ~DYEVJPW ~MDZJQZQ ~13MJ53F ~JEN2C8Q
  ~ECEBCQ1 ~4N35GSV ~BVCRKXA ~7BT4W67 ~PVJ9SQM ~17ZVW3R ~G436171 ~2JVWF8Y
  ~YNC30Q8 ~1B4EEQZ ~BGB8V55; D99, D100 recorded; M1 and design epics
  closed. Land procedure that worked: one serial chain script per batch
  (evidence then `land --wait 900`), no ledger writes while a land runs
  (each write forces a ~7 min re-check), push experimental after (lands do
  not push). Evidence ref: `goway run --with-git --needs cores:8 --wait 20m
  -- cargo nextest run --profile ci --workspace` (goway on PATH is the dev
  build; goway ~41CG5RF fits jobs to helper memory). Brief pitfalls fixed:
  `--accepts` takes criterion indexes, every ticket needs a changelog
  fragment (REL003).

- 2026-10-06: 0.532.0 crates.io publish finished after the owner widened
  the registry token (first run: 403 on gob-fs; job re-run, 41 published,
  2 already present, one 429 retried). Wave dispatched: ~JEN2C8Q (C#
  usings and calls), ~ECEBCQ1 (.sln/.csproj), ~MDZJQZQ (ci sibling
  binaries), ~DYEVJPW (missing ledger ref); shared brief in the session
  scratchpad. Owner asked for a repo map, abstractions, sensible language
  engines and ruff/ty-style tests and CI: design D96 (language-engines.md:
  facts about what is written live in gob; markup, style, const_value,
  project_model capabilities; gob-frameworks), D97 (products.md 7:
  gob-check::sibling, gob-product), D98 (build-test-ci.md 6). Epics
  ~N4R2XN5 (web engine; the four crunk-epic engine tickets re-parented,
  ~XPMQ50D dropped as superseded), ~VX11TG4 (product front end; ~YDDKPEY
  superseded), ~M9NHDJP (ruff/ty tests and CI). Pitfall: `ticket update
  --set parent=$EMPTY` clears the parent (~V5F85PC); the show JSON keeps
  the id under data.summary.id.

- 2026-10-03: ~CFM8QB0 changed the fold (acceptance bound only from
  measured passing evidence, through the moved maps), so every ticket
  with evidence drifted under the new binary and the new binary's land
  check refused (TICK001 x75). Procedure that worked, now the rule for
  any fold change: copy the worktree binaries (frob and grimble) to the
  scratchpad, run `ticket doctor --fix` with them (74 reconcile commits,
  zero drift after), then land with the same binary, then rebuild the
  landing binary in the primary. Since the last entry: design D76-D85
  accepted (plugins, diagnostics, mirror, GRL, navigation, security
  incl. trust UX, releases, doc consistency, consistency pass 2); mirror
  protocol v2 from an adversarial audit plus a TLA+ model
  (docs/design/models/mirror); 0.532.0 release slice planned (epic
  ~P2QNP8T, label release:0.532.0); landed code: gob-ir stack safety and
  scope cache, cross-crate calls and type inference (COV001 284 -> 35),
  engine-scoped caches, grimble binding cache (warm 0.09 s release),
  SYS applicability predicates, ticket acceptance edits, gob-trust,
  gob-plan lexer, ledger append API, hand-written release workflow.

- 2026-10-04 (after compaction): freed another ~174 GB (324 -> 150 GB
  used): v1 worktree build output, then all 135 v1 frob worktrees
  removed with branches kept (3 with uncommitted state backed up to
  ~/frob-v1-worktree-backup), uv cache cleared. Repaired ticket/EHPFVKD:
  26 empty objects deleted, branch reset to 201ae0c6d with the lost
  commit's files re-staged from disk, stale reflog expired; git fsck
  --full is clean. Resumed the G09 and FileInfo agents.

- 2026-10-04 (disk event 3, hotfix): the disk filled again; the session
  died with two agents running (G09 grimble binary ~EHPFVKD, agent
  a9b427f4bd9c7e96e; FileInfo rules ~5NFTK3H, agent ad3e84f860845fc38).
  Reclaimed ~130 GB (retired shared .target, primary incremental, both
  worktrees' target/). 26 loose git objects are EMPTY (truncated writes);
  the ONLY damaged ref is ticket/EHPFVKD (its tip commit object is empty).
  experimental and all other branches read cleanly. The G09 worktree
  files are intact and backed up to
  ~/frob-v2-recovery/EHPFVKD-20261002-2001 (tar + reflog).
  NEXT SESSION: (1) repair: in the EHPFVKD worktree, reset the branch to
  the newest readable commit from the saved reflog with `git reset
  --soft` (keeps the files), re-commit the work, then delete the 26
  empty objects (`find .git/objects -type f -size 0 -delete`) and
  `git fsck --full` must be clean; (2) resume both agents with
  SendMessage (their transcripts persist); (3) continue milestone 2.

- 2026-10-04 (milestone 2): landed gate, grmb spec, gob-ir, tool
  bindings, G02, G03, G04, follow-ups, gob-symbols over U, scope-diff
  fix, manifest-dir fix, G06 gob-check, G07 selectors, G05 digest
  scheme (format-bump land with its own binary). Shared target dir
  retired. Tool gaps filed: ~V5F85PC (empty --set wipes scope; show
  --json lacks scope), ~KDR4ZBR (scope change does not refresh lease;
  lease edited by hand twice), ~YBM7WZC (land refusal lists warnings).

- 2026-10-04 (cutover): design review integrated (D56-D64). Cutover
  done: experimental fast-forwarded to t-0025 (re-imported final v1
  ledger, 35 tickets, v2 frob.toml, notes/ excluded from check); v2
  doctor, ticket doctor and check are clean on the primary; 359 tests.
  T-0025 closed with the v2 binary. All v1 worktrees removed. Milestone
  2 is filed next with the v2 binary in the order of
  build-test-ci.md "Milestone 2".

- 2026-10-04 (review pause, closing): owner asked for (1) a survey of
  paradigms and a universal model with coverage proofs, (2) loud
  failure on anything incomputable, (3) a neatness lint family from
  Logan Smith's channel and his references plus the ruff PR 29076
  dispatcher example, (4) a CI/CD survey of about 1000 repos. Delivered
  universal-model.md, neatness.md, cicd.md, grimble-model.md section 9,
  four research notes, two reviews, D56-D60. A consistency review (12 H
  / 24 M / 9 L) is being applied by a fixer with decisions D1-D11 (see
  notes/review/design-consistency-resolution.md). Owner: resume
  implementation once integrated and reviewed. Next: cutover (merge
  experimental into t-0025 keeping the v2 ledger, re-import the final
  v1 ledger, verify, merge), then file milestone 2 with the v2 binary
  in the order of build-test-ci.md "Milestone 2".

- 2026-10-04: T-0035 landed (29 done). T-0025 (self-host switch) is
  complete on branch t-0025 and NOT merged: the cutover must re-import
  T-0035/T-0036 and merge by hand after the owner review. Design work
  during the pause: docs/design/universal-model.md (DRAFT) with three
  research notes and a reading list under notes/research/. The research
  notes lack web verification; `[verify]` tags mark uncertain citations.

- 2026-10-03 (night): OWNER PAUSE. After T-0035 and T-0025 land, no new
  dispatches. The owner reviews (1) what has been done and (2) the
  design docs afresh, with one stated concern: the IR (code-model.md
  section 5, gob-ir, milestone 2) must support esoteric languages, not
  only tree-sitter-shaped ones. T-0036 stays queued. Review entry
  points: this file; docs/design/README.md decision log D1-D55;
  notes/audit-resolution.md; per-ticket done-reports under tickets/;
  `frob check --timing --text` and `frob doctor` from the v2 binary.

- 2026-10-03 (evening): landed T-0028 (TicketSchema derive on a mirror
  struct), T-0029 (design reconciled, D38-D55), T-0023 (frob-check;
  warm fresh-process run 0.66 s on this repo). 27 done; T-0032/T-0033
  are dropped v1 sweep drafts. `frob check` on this repo today: DSL001
  for v1 frob:waive comments in notes, DSL002 for T-#### ids in config
  comments, TEST001 symref forms in frob-ack tests, DOC002 corpus links,
  198 COV001 warnings: the T-0025 cleanup list. Two more Claude Code
  kills happened (one mid-agent); agents resume from transcripts with
  SendMessage. Scope changes must run from the lease-holding worktree.
  The gob-dev rule pages now carry a v1 DOC004 waiver above embedded
  examples. T-0024 dispatched; T-0025 is the last M1 ticket.

- 2026-10-03 (later): T-0031 and T-0022 landed (25/31 done, 320 tests).
  v1's post-land sweep filed a draft about its own Python-era gates
  over Rust files; dropped with reason. Disk filled by per-worktree
  target dirs; cleaned (147 GB). T-0023 worktree created.

- 2026-10-03: landed T-0014 T-0016 T-0018 T-0030 T-0021 T-0019 T-0020
  (23/31 done, 292 tests). Verb wiring was split out as T-0031 so
  lease, evidence/tests and ack crates ran in parallel; each exposes
  register(Cli) -> Cli. T-0030 fixed LocalEdits under core.autocrlf via
  gix's filter pipeline. Open design reconciliation items are listed in
  T-0029 (add: [lease]/[worktree]/[evidence] table names, Defer because=
  vs reason=, evidence events written outside frob-ledger pending an
  EventBody::Evidence variant, gob-cli two-word verb limit, generated
  doc paths). Dispatched T-0031 and T-0022; next T-0023, T-0024, T-0025,
  T-0028, T-0029.

- 2026-10-02 (night): landed T-0008 T-0015 T-0006 T-0010 T-0013 T-0027
  T-0017 (16/27 done, 146 tests). T-0027 fixed a real gix bug: shared
  index snapshot refreshed by mtime only; gob-git now opens a fresh
  handle for status and local-edit checks. T-0028 (TicketField derive)
  split from T-0018 so T-0014 and T-0018 run in parallel without a
  gob-macros lease collision; T-0029 (design reconciliation) filed and
  is done last. Both implementers dispatched. Coordinator rule from the
  owner: no manual code or doc edits by the coordinator; route fixups
  to agents.

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
