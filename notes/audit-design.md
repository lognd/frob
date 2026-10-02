# Audit: frob v2 design set (docs/design/*.md)

Fresh pass over all 17 files in docs/design/ (read in full) against the
evidence in notes/ (v1 inventories KEEP lists, rust-ecosystem.md,
crunk.md, agent-usage.md). Supersession order used, as instructed:
products.md, boundaries.md, exceptions.md, documentation.md and
pm-enforcement.md win over earlier files where they disagree. Line
numbers are 1-based line numbers in the named file at the time of the
audit. No design file was edited.

## Summary

| Severity | Count |
|---|---|
| HIGH | 9 |
| MEDIUM | 36 |
| LOW | 22 |
| Total | 67 |

HIGH = a contradiction or hole that makes a stated invariant impossible,
loses or corrupts ledger/review data, gives agents a wrong contract, or
is a bypassable security control. MEDIUM = a real contradiction or gap
with bounded blast radius. LOW = naming, numbering, stale wording.

---

## HIGH

### H1. The "primary checkout owns the ledger" writer story breaks on branches, staged changes, land, CI, forks and offline clones

- Where: tickets.md section 2 lines 75-79 (writer story); git-io.md section 2 lines 37-42 (ledger commit = "write file, write blob, update index entry, write tree, commit, CAS ref"); tickets.md section 10 lines 238-245 (land CAS-publishes the ref and "resync the primary index"; push opt-in); README.md D7 line 52.
- Finding: the design commits ledger changes "in the primary checkout ... with a pathspec limited to the ticket's directory" but never says which ref is advanced, nor how the commit coexists with (a) a primary checkout that is on a feature branch or mid-rebase (humans work in the primary), (b) a primary index holding the user's own staged changes (git-io's sequence "update index entry, write tree" would sweep those staged hunks into the ledger commit), (c) a concurrent `land` that CAS-publishes the same branch ref from a detached worktree, (d) CI, which is a fresh clone with no "primary" and sees only pushed commits, (e) PR/fork flows where main is branch-protected and only changes via merge. Concrete: agent A runs `frob ticket update X` in worktree wt-a while the human's primary is on branch `feat/y` with `src/a.rs` staged -> the ledger commit lands on `feat/y` and contains `src/a.rs`. Or: ticket commit and `land` both move `main`; one CAS fails and the design has no retry/rebase rule for ledger commits. Or: push is opt-in, so `frob:ticket 01J9QK...` added by a land is pushed in a PR but the ticket commit that created 01J9QK only exists in the developer's local main; CI `frob check` reports a dangling ticket.
- Why it matters: this is the D7 decision that justifies deleting mirror/splice/overlay; if it does not hold, v1's four patches return. It is also silent data corruption (staged user changes committed under a ticket message).
- Suggested fix: specify the ledger ref explicitly (always the configured trunk ref, written by building a tree from that ref's tree plus the ticket dir, never from the primary index, then CAS on that ref with bounded retry), state what happens when the primary has trunk checked out (update its index/worktree for tickets/ only), and add a section for CI/fork/offline clones (ledger commits must be pushed before or with the PR; TICK rule for "referenced ticket not on remote trunk").

### H2. ULID "shortest unique prefix of at least 6 chars" is time-correlated, so persisted short ids become ambiguous within minutes

- Where: tickets.md section 2 lines 23-28; goals.md lines 96-99 (`frob ticket show 01J9`, "Humans and commit messages use the prefix"); migration.md line 10 (`frob migrate directives` rewrites to "the short ULID prefix"); code-model.md section 2 (ambiguity is an error).
- Finding: ULID chars 1-10 are the 48-bit millisecond timestamp (first char carries 3 bits). A 6-char prefix fixes only the top 28 bits, so every ticket created in the same ~17.5-minute window (2^20 ms) shares it; 8 chars still covers ~1 s. Unlike git hashes (random), the collision is deterministic for burst creation, which is exactly the agent pattern (agents file several follow-ups in a minute). Scenario: agent creates ticket A at 10:00, writes `frob:ticket 01J9QK` (unique then) into code and a commit message; at 10:05 it files ticket B, whose id also starts `01J9QK`; every later resolution of the directive is now "ambiguous, error with candidates" and the commit message is permanently ambiguous. Prefix display length also grows to 8-10 chars under bursts, defeating the "short handle" goal.
- Why it matters: directives and commit trailers are the binding between code and tickets; DRIFT/COV/TICK rules turn red on code nobody touched.
- Suggested fix: never persist an abbreviated id: directives, links, fragments and commit trailers store the full ULID (a fixer expands prefixes on write; a rule flags abbreviations in tracked text). If a short human handle is wanted, derive it from the random part (e.g. last 6 chars) or a hash, not from the time prefix.

### H3. Jobs have no executor and no storage without a daemon, and contradict "synchronous land"

- Where: cli.md section 3 lines 69-71 (`land` "returns immediately with a job id unless --wait"; "`job wait <id>` blocks server-side"; "`job status` is O(1)"); tickets.md section 10 lines 238-245 ("run the full check ... synchronously", "`land --wait` blocks on the land lock"); README.md D8 line 53 ("Synchronous land"), D13 line 57; git-io.md section 3 lines 44-52 (closed spawn list) and section 6 lines 86-91 (daemon optional); boundaries.md frob-land owns "jobs, wait".
- Finding: if `frob land` returns immediately, something must keep running the land after the CLI process exits. With no daemon (the default), that is a detached child process, which is not in the bounded spawn list and is exactly v1's `sweep-async` (removed in cli.md line 104). "Blocks server-side" has no server. Job id format, where job records live (which `.frob/`: primary or worktree), crash recovery of a half-finished land, and what `job wait` returns when the job failed are all undefined. tickets.md meanwhile describes `--wait` as waiting on the land lock, a different semantic from waiting on a job.
- Why it matters: land polling was 50 percent of v1 process invocations; an agent contract that cannot be implemented as written will be patched ad hoc.
- Suggested fix: pick one: (a) land is synchronous by default (no job ids, `--wait <secs>` only bounds lock acquisition), or (b) jobs exist and the design adds a job store under the git common dir (`.git/frob/jobs/<ulid>.json`, written by the land process itself while it runs in the foreground), with `job wait` implemented as a file-watch/poll inside one process and an explicit exit contract. Remove "server-side" unless the daemon is mandatory.

### H4. `work` idempotency hands an existing lease to a different agent, and lease acquisition has no atomicity rule

- Where: cli.md section 3 lines 57-59 ("`work` on a started ticket returns the existing lease and worktree"); tickets.md section 8 line 200; tickets.md section 6 lines 134-146 (`.git/frob/leases/<id>.toml`, overlap check, `--steal`).
- Finding: idempotency is defined by ticket id only, not by caller identity/session. Scenario: agents A and B both pick the same `doable` ticket; A runs `frob work X` and gets worktree W and the lease; B runs `frob work X` a second later and gets `ok: true, already: true` with the same worktree W. Both agents now edit W concurrently with a lease that both believe they hold. Separately, taking a lease is "read all lease files, compute overlap, write `<id>.toml`" with no stated lock or atomic create: two `work` calls on different tickets with overlapping scope can both pass the overlap check and both write their lease (TOCTOU).
- Why it matters: the scope lease is called "the crown jewel"; both cases silently produce two writers on the same files.
- Suggested fix: make `work`/`start` idempotent only for the same holder (actor + session or worktree identity carried in the lease); a different caller gets exit 3 `E-LEASE-HELD` with holder. Require lease acquisition under one lock file in the git common dir (or `O_EXCL` create of the lease plus re-check of overlaps after create, removing on conflict) and document it.

### H5. Exit-code contract contradicts itself across files and leaves 1 vs 3 undefined for common refusals

- Where: cli.md section 2 lines 42-48 (0 for findings; 1 only when asked via `--fail-on`, "the default in CI via FROB_CI"); rules.md section 4 line 175 ("8. Exit 1 on any Error") and section 1 line 25 ("exit code is errors only"); cli.md line 100 and notes/crunk.md section 1 (crunk "unchanged verb set", crunk check exits 1 on error violations); architecture.md lines 51-53; cli.md line 35 (`retry_after_ms`) vs architecture.md line 148 (`retry_after`).
- Finding: (a) rules.md still says `frob check` exits 1 on any Error, contradicting the D13 contract; crunk keeps its 0/1/2 contract while `frob check` merges crunk under gob-diagnostics' contract. (b) `FROB_CI` silently changes the exit contract from an environment variable, violating the "no invisible variables" principle (goals.md lines 86-89). (c) Undefined: is `ticket close` refused for missing evidence exit 1 (negative domain answer) or exit 3 (guard)? Is `retryable` true for it (retrying without changes never helps)? What does `--wait <secs>` return on timeout? What does `job wait` return when the land job failed its check (1, 3 or 4)? What does `cycle assign` over capacity return?
- Why it matters: agents branch on the code, not prose (cli.md line 48); the v1 data shows overloaded exit codes caused blind retries (56 percent of failures).
- Suggested fix: add one exit-code table in cli.md with a row per refusal class (guard-retryable-by-waiting, guard-needs-action, domain-negative, timeout, job-failed), define `retryable` as "same argv may succeed later without other action", fix rules.md step 8, state crunk adopts the shared contract, and replace `FROB_CI` with a materialized `[check] fail_on` knob plus explicit `--fail-on`.

### H6. Exceptions require grimble and crunk to know tickets, and frob to parse grimble/crunk namespaces

- Where: exceptions.md section 1 lines 21-24 (`defer` exits when "the named ticket reaches a terminal state"; `hotfix` carries an auto-filed ticket), section 2 lines 39-54 (`grimble:defer ARCH001 ticket=01J9QK`, `grimble:hotfix ... ticket=`, shared `exceptions.toml`, "a ticket cannot close while a defer still points at it"), section 4 line 85 (budget per component); versus products.md line 13 and line 21 (grimble "has no idea tickets exist"), boundaries.md section 1 lines 20-23, code-model.md section 4 line 154 ("A product never parses another product's namespace"), grimble-model.md section 7 heading ("grimble never knows about tickets").
- Finding: EXC005/EXC007 for a `grimble:defer` need ticket state; the close guard in frob needs to find every `grimble:defer ticket=X` and `crunk:defer ticket=X` in code; per-component budgets need frob's component registry. None of these can be evaluated by the product that owns the namespace without crossing the boundary the later files declare. The design also gives grimble's own `.grmb` a third waiver form (`waive SYS012 on cli reason ...`, grimble-model.md line 55) with no kind.
- Why it matters: exceptions are the debt-visibility mechanism (D21); as specified, a grimble-only repo cannot evaluate its own defers and frob cannot enforce its close guard without violating D18.
- Suggested fix: state explicitly that exception exits referencing tickets are evaluated by frob only: grimble/crunk parse the exception, treat `ticket=` as opaque and emit it in `--json`; frob's orchestrated check evaluates ticket-bound exits and the close guard from that JSON. Standalone grimble reports such exceptions as Unresolved-exit. Put grimble-model's `waive` under the same four kinds.

### H7. grimble drift findings depend on an ack store and ack verb that only frob has

- Where: grimble-model.md section 4 lines 124-125 (SYS-CONTRACT-SKEW "between producer and consumer acks"; SYS-CHANGED "since last ack (same ack mechanism as frob.lock)"); boundaries.md lines 71 (frob-ack owns `frob.lock`), 134-135 (`why` frob only); products.md line 12 (frob owns `frob.lock` acks); exceptions.md line 63 (REATTEST "-> ack with reason").
- Finding: grimble has no lock file, no `ack` verb (cli.md lines 98-99 list none), and may not read frob.lock under D18. Two core drift findings are therefore unimplementable as written, and the `accept` REATTEST exit for grimble exceptions has no attestation store either (see M15).
- Why it matters: SYS-CHANGED and SYS-CONTRACT-SKEW are the cross-language contract checks that justify grimble's existence (goals.md goal 3).
- Suggested fix: move the lock format and ack mechanics into a substrate crate (e.g. `gob-lock`, per-product file `grimble.lock`), give grimble an `ack` verb, and keep frob.lock frob-only; update grimble-model.md section 4 and boundaries.md 2.1/2.3.

### H8. The GUI HTTP API mutates the ledger on localhost with no CSRF/Origin protection, and contradicts the "read-only" non-goal

- Where: gui.md section 2 lines 18-30 (`POST /api/ticket/set`, "bound to localhost by default; `--token` for a LAN session"); goals.md non-goals lines 66-67 ("an optional read-only HTTP/MCP server is a thin view"); gui.md section 3 (land, waive-from-UI, `fix`).
- Finding: a localhost HTTP server without a mandatory token or Origin/Host check is reachable from any web page the user visits (cross-site form POST or DNS rebinding). Scenario: user runs `frob serve --http`; a malicious page POSTs to `http://127.0.0.1:<port>/api/...` and closes tickets, writes waivers into source via the UI waive action, or triggers `fix` writes and commits. Actor is recorded as the server's `git config user.name`, so the forged change is attributed to the user.
- Why it matters: authz bypass of every guarded mutation; ledger commits forged under the owner's identity.
- Suggested fix: always require a per-launch random token (printed URL with token, cookie or header), reject requests whose Origin/Host is not the bound address, use non-simple content types for mutations, and update goals.md to say the server is read-write.

### H9. The #1 goal (warm full check < 2 s, ticket reads < 50 ms) has no mechanism for a fresh CLI process

- Where: goals.md goal 1 lines 33-35; architecture.md section 2 lines 41-48 and table lines 58-65; rules.md section 1 lines 20-23 (findings "memoized on (file digest, rule set version, side-input digests)"); git-io.md section 6 (daemon optional); notes/rust-ecosystem.md line 359 and line 434 ("Persisting salsa memos is not supported"; "Memos are in-memory only").
- Finding: salsa memos die with the process and only parse artifacts are persisted to SQLite. A warm CLI `frob check` therefore re-runs every rule on 100k lines, plus repo-scope rules (cycles, dup R1-R5, dead code), plus test collection, plus `[[check.tool]]` and the documentation gates that documentation.md section 8 puts "all inside frob check" (cargo doc, mdbook, lychee, typos, clippy). No persisted findings cache, no invalidation key for repo rules, and no budget for tool stages is designed; "warm" is never defined (daemon-warm vs cache-warm).
- Why it matters: speed is the ranked first goal and the reason for the rewrite; without a mechanism the target will be quietly missed and the v1 `--budget` chunking will come back (rules.md line 181).
- Suggested fix: define "warm" (fresh process with populated `.frob/` cache), add a persisted per-file findings table keyed by (file digest, rule id, rule version, side-input digest) and a repo-rule key (graph digest), exclude external tool stages and doc gates from the 2 s budget explicitly, and make the bench crate measure the fresh-process case.

---

## MEDIUM

### M1. frob needs imports and the call graph, so the gob-symbols / gob-ir split premise is false
- Where: boundaries.md section 4 line 174 ("frob needs only symbols and digests ... keeps frob's build free of IR code"); code-model.md section 3 lines 78-79 (imports and call graph live in gob-ir, "frob builds without it"); boundaries.md lines 69 (frob-tests touched-set "from the graph"), 116 (INV `no_import` evaluated "inside frob" with import edges), 150 (public-API graph for semver); rules.md table lines 84-85 (AFFECT dependent symbol, COV private-reach), code-model.md section 6 lines 199-207 (affects/test-evidence reach over the call graph).
- Finding: AFFECT, COV private-reach, touched-set test selection, INV forbidden-import and semver inference all need imports/calls, which are placed in gob-ir.
- Why it matters: the crate graph and the "frob builds without IR" claim cannot both hold; implementers will discover it after the split.
- Suggested fix: move imports and the call graph to gob-symbols (or a `gob-graph` crate) and leave only the structural IR (IrNode/IrKind, ir_map) in gob-ir.

### M2. The `bundle` feature makes frob depend on grimble and crunk, and sibling discovery silently changes check results
- Where: boundaries.md section 6 lines 196-201; architecture.md lines 27-29; products.md lines 66, 101-107; build-test-ci.md section 4 line 82 (self check merges grimble and crunk); README.md D18.
- Finding: "products never depend on each other" is immediately excepted for the default distribution (the PyPI wheel bundles in-process). Consequences not addressed: frob releases must pin grimble/crunk crate versions (breaks "released independently"); a crates.io `frob-cli` built without `bundle` behaves differently from the wheel; when a sibling is absent `frob check` simply omits its families, so a check is green locally and red in CI (or the reverse) with no signal; a sibling on PATH at another version may emit an incompatible `--json`.
- Why it matters: "the one command an agent runs" gives different answers depending on install channel.
- Suggested fix: state the exception honestly in the dependency rules; when a sibling is configured (its config file exists) but unavailable, emit one Unresolved finding per missing product; version-check sibling `--json` output (schema version field) and refuse on mismatch.

### M3. The exceptions redesign was not propagated: waiver vocabulary still v1 in five files
- Where: code-model.md section 4 lines 123-133 (`#[directive(verb = "waive")]` with `preset`, `until`, `ceiling`; exceptions.md line 28 removes presets) and line 153 (`crunk:waive`); rules.md lines 27 ("Waivers ... are kept"), 95 (WAIVE family), 235-237 (DEBT in frob-obligations), no EXC row; products.md line 66 (WAIVE, DEBT for frob); boundaries.md lines 70 ("DEBT ... WAIVE hygiene") and 121-127 ("hygiene rules about waivers are in gob-rules", "waive audit" is frob); grimble-model.md line 55 (`waive SYS012`); migration.md line 13 (`frob migrate waivers`, vs exceptions.md line 134 `frob migrate exceptions`); cli.md line 91 (`waive audit`, `pool`); monorepo.md line 46.
- Why it matters: the derive example in code-model.md is the template implementers will copy; it encodes the removed model.
- Suggested fix: replace the Waive derive example with the exception directive (kind as verb, `because`, `ticket`, `until`), drop WAIVE/DEBT rows in rules.md, products.md and boundaries.md in favour of EXC, name the crate that owns EXC (gob-rules for parsing and reason checking, frob for ticket-bound exits per H6), and rename the migrate subverb consistently.

### M4. Rule families with no owning crate, families owned twice, and one family split across two products
- Where: boundaries.md section 2.2 line 70 (frob-obligations family list) vs rules.md lines 81-101 and 235-244; documentation.md section 4 (NARR) and 3/8 (GEN001), architecture.md line 136 (CFG001), git-io.md line 56 (PROC001), exceptions.md section 6 (EXC), rules.md line 86 (PARSE, DSL), line 93 (CROSSTICKET), line 94 (REL, VERSION), documentation.md lines 95 and 104 (DEC004, REL003), build-test-ci.md line 69 (GEN001); rules.md line 101 vs boundaries.md lines 152-157 (POL).
- Finding: NARR, GEN, CFG, PROC and EXC appear in no crate map; PARSE, DSL, CROSSTICKET, REL, VERSION are missing from boundaries.md's frob-obligations; PARSE/DSL fire for all three products (malformed `grimble:` directive) yet are placed in frob-obligations. POL is split between grimble-lints (code) and frob-obligations (tickets/docs) under one family prefix and one generated id scheme `POL-<slug>`, which can collide, contradicting boundaries.md section 5 (families namespaced per product). Policy file location is given three ways: `frob.toml [policy]` (rules.md line 101), `[[policy]]` in grimble.toml (boundaries.md line 154), `rules/*.grl.toml` next to grimble.toml (rules.md line 113).
- Why it matters: unowned rules do not get built; colliding ids break waivers and baselines.
- Suggested fix: one authoritative family-to-crate table in boundaries.md covering every family named anywhere (including crunk's COLOR/SPACE/TYPE/RADIUS/SIZE/LAYER/CONTRAST/ORG/TW/BP/GALLERY), PARSE/DSL in gob-directives emitted under the parsing product's namespace, and two distinct prefixes (e.g. `GPOL` for grimble, `POL` for frob) with one documented file location each.

### M5. Rule id formats disagree for the same findings
- Where: grimble-model.md section 4 lines 116-127 (`SYS-UNRESOLVED`, `CAP-EXCEEDS`, `CAP-STALE`, `CAP-UNEXCUSED`) and line 55 (`waive SYS012`); code-model.md section 7 lines 230-231 (`CAP001` undeclared Error, `CAP002` declared-unused Warn), section 6 line 198 (`BIND001`, `BIND002`); rules.md line 142 (`POL-<slug>`), line 76-77 ("ids inside a family are renumbered only where v1 ids were duplicates").
- Finding: the same capability findings have two ids and two meanings (CAP002 Warn vs CAP-STALE shrink-only); grimble uses name-suffixed ids while everything else is FAMILYNNN; "renumber only duplicates" conflicts with collapsing SYS's 51 ids into a few parametric ones (rules.md line 97).
- Why it matters: ids are the waiver/baseline keys and the migration map target (migration.md line 13).
- Suggested fix: choose one id grammar for all products (FAMILYNNN with a slug alias, or slug-only), rewrite grimble-model section 4 and code-model section 7 to one table, and state in rules.md that migration maps many-to-one where families were collapsed.

### M6. Config ownership and "no invisible variables" are violated in several places
- Where: grimble-model.md section 5 lines 147-148 (`[grimble] packs = [...]` in `frob.toml`) and section 8 line 177 (`[grimble] strict`), vs boundaries.md lines 25-26 (each product owns its config file); exceptions.md line 45 (`exceptions.toml` shared by three products, not in architecture.md storage table lines 69-79); goals.md lines 86-89 and architecture.md lines 130-138 (every enforcement knob materialized); hard-coded enforcement constants: cli.md line 59-60 (10-minute `new` dedupe window), tickets.md lines 24-25 (6-char minimum prefix) and line 229 (16 KiB inline evidence), exceptions.md line 126 (EXC004 "14 days"), line 140 (migration "within 14 days"), rules.md lines 167-168 (`--ticket` "one hop"), 207-208 ("one release" Warn), pm-enforcement.md line 80 ("more than N tickets"), exceptions.md line 104 (N exceptions); environment variables that change behaviour: cli.md line 45 (`FROB_CI`), tickets.md line 46 (`FROB_AGENT`), architecture.md line 106 (`FROB_LOG`, harmless).
- Finding: also no file collects the config surface; knobs are scattered (`[tickets]`, `[tickets.workflow]`, `[tickets.custom_fields]`, `[evidence] store`, `[perf]`, `[telemetry]`, `[check]`, `[[check.tool]]`, `[land]`, `[git] run_hooks`, `[pm]`, `[pm.personas|attributes|metrics|ready|done|wip]`, `[exceptions]`, `[rules.<id>]`, components, labels, triage rules, saved queries, agent identities with capability flags, auto-archive thresholds, mega-glob threshold, lease TTL, honoured directive namespaces (monorepo.md line 48-49), webhook).
- Why it matters: CFG001 makes a missing materialized knob an Error, so an unlisted knob is either invisible or a surprise error after upgrade.
- Suggested fix: add a config inventory table (key, product file, materialized yes/no, default, owning crate) to architecture.md section 6; move grimble knobs to grimble.toml; turn every constant above into a materialized knob or justify it as non-enforcement; put exceptions.toml in the storage table with product sections.

### M7. Ticket workflow model contradicts itself
- Where: tickets.md section 5 lines 121-130 (transitions "declared in `[tickets.workflow]` per type with guards"; a repo can add statuses and transitions) vs section 7 line 160 ("guards are predicates on `close`, not a transition graph"); section 3 line 94 (`resolution`) vs section 5 line 123 and section 7 line 161 (`outcome`); section 7 line 162 (priority `P0-P4`) vs cli.md line 61 (`--set priority=high`); section 5 line 122 (`blocked` derived) vs section 7 line 160 (`blocked` a fixed category); section 3 line 93 and line 102 (`milestone` is both a release object field and a ticket type, pm-enforcement.md line 12 treats it as a type with PM001); section 3 line 93 (`sprint (object)`) vs pm-enforcement.md (`cycle`), migration.md line 9 ("sprint objects"); section 4 lines 112-115 vs section 7 line 166 (link types `discovered-from`, `duplicate-of`, `enabler_for` (pm-enforcement.md line 86) are not in the declared link list; `causes`, `splits` are not in section 7).
- Finding: also undefined: whether `close` or `land` moves a code-changing ticket to done, and when a ticket is ever in `landing` if land is synchronous.
- Why it matters: `#[derive(TicketField)]` generates schema from one declaration; the declaration does not exist yet because the prose disagrees.
- Suggested fix: decide transition graph vs category-plus-guards, one field name (`outcome`), one priority enum, `blocked` derived only, milestone as release object only (or as type only), one term (`cycle`), and one canonical link table including inverses and topology constraints.

### M8. Event kinds referenced but never defined
- Where: tickets.md section 2a lines 43-44 (kinds: transition, field, comment, link, evidence, lease, review, exception, cycle, attempt); referenced elsewhere: `attempt-failed` (tickets.md line 130), `carried` (pm-enforcement.md line 129), over-commit reason event (line 121), `reviewed` (exceptions.md line 21), budget-raise reason event (exceptions.md line 85), audit verdict events (exceptions.md lines 70-71), flavour-change reason event (pm-enforcement.md line 81), comment subtypes note/decision/question/answer/evidence and "blocked-on-question events" (tickets.md lines 171, 186), ack events (migration.md line 11 "recorded as events"), cost/token events (tickets.md line 207), triage accept/decline/snooze.
- Finding: no per-kind schema, and several events (accept review, budget raise, audit verdict, ack) have no ticket to live under although events are stored only at `tickets/<id>/events/`. `ticket_rev` (line 50) will disagree with the frontmatter after any merge of concurrent changes, so `frob ticket doctor` will report false corruption.
- Why it matters: velocity, forecasts, cycle reports and exception audits are all computed from events.
- Suggested fix: add an event-kind table (kind, subject, required fields, producer verb, consumers) and a home for non-ticket events (e.g. `events/` at repo root or under `exceptions/`); define `ticket_rev` checks as "frontmatter equals fold of events", not digest equality.

### M9. Lease semantics: resolved file sets miss new files, TTL vs long runs, no cross-clone visibility, WIP default with shared identity
- Where: tickets.md section 6 lines 134-148; pm-enforcement.md section 6 lines 164-166; tickets.md line 46 (actor from git identity unless `FROB_AGENT`); notes/v1/tickets.md line 566 ("keep glob-overlap proof").
- Finding: (a) "Overlap is computed on resolved file sets, not glob text": two tickets scoped to `src/newmod/**` where no files exist yet resolve to empty sets and never overlap, so both are granted; v1's glob-overlap proof is dropped without saying so. (b) Heartbeat is "renewed by any verb from that worktree"; an agent running a 40-minute build or test with no frob call goes stale and can be stolen; TTL default is not named. (c) Leases live in `.git/frob/leases`, invisible to another clone or machine. (d) If `[pm.wip] in_progress_per_identity = 1` is the materialized default and agents run without `FROB_AGENT`, every parallel agent is "logan" and the second `work` refuses. (e) Symbol-level scopes do not say who owns edits outside any symbol (imports, module headers).
- Why it matters: lease correctness is the multi-agent safety property.
- Suggested fix: compute overlap on globs with a resolved-set refinement (overlap if globs intersect OR resolved sets intersect), define TTL as a materialized knob with heartbeat from the worktree's frob process and the daemon, state leases are single-clone, default WIP limit off or per worktree, and assign non-symbol regions to file-level scope.

### M10. SQLite single writer across processes, worktrees and the daemon is unspecified
- Where: architecture.md lines 38, 79, 176 ("one writer connection behind a channel"); boundaries.md line 52; code-model.md section 8 lines 243-246; tickets.md lines 72-74 (index); git-io.md section 6 lines 86-91.
- Finding: "one writer" is per process. Parallel agents in N worktrees, the daemon, and CLI fallbacks are N writers. Not specified: whether `.frob/` is per worktree (N cold caches, N ticket indexes of a ledger that lives in the primary) or shared via the common dir (then cross-process locking, `SQLITE_BUSY`, WAL on network or WSL-mounted filesystems); whether a cache write failure is fatal; that persistence must happen outside salsa tracked functions (side effects inside queries break memo purity).
- Why it matters: the read targets (< 50 ms) and the "reads never take locks" claim depend on it.
- Suggested fix: state the location (recommend parse cache per worktree plus a ticket index keyed to the primary ledger tree id), set `busy_timeout` and make cache writes best-effort with a logged miss, and persist from the command layer after queries return.

### M11. salsa plus rayon plus a watcher-driven server: API and cancellation assumptions unverified
- Where: architecture.md section 9 line 171 (salsa "`Snapshot`/`par_map`"), line 175 ("no locks around the derived state (v1's deadlock class)"); gui.md line 25-27 (watcher invalidates inputs); notes/rust-ecosystem.md line 439 ("keep salsa queries single-threaded per db or use salsa's parallel support").
- Finding: current salsa (0.2x) removed `Snapshot` in favour of cloned database handles; setting an input cancels in-flight queries on every other handle and blocks until they unwind. In `frob serve`, every file-watch event during a long `check` cancels it; with an active editor the check may never finish. salsa also blocks threads waiting on queries in flight on other threads, so "no locks" is not true of the derived state.
- Why it matters: D16 and the daemon option rely on this interaction.
- Suggested fix: add a short "concurrency model" subsection: handle cloning per request, cancellation catching and retry policy, debounce of watcher input writes, and a spike ticket that validates salsa par_map on rayon before committing to it.

### M12. Capacity and forecasting break with little history
- Where: pm-enforcement.md section 4 lines 113-124 (`capacity = rolling_mean - k * stddev`), lines 132-133 (agent throughput per identity), section 5 lines 142-147 (`min_history` fallback "uses points-based capacity").
- Finding: in a fresh repo there is no completed cycle: mean and stddev are undefined (or 0), so every `cycle assign` refuses and needs `--over-commit --reason`, which goals.md goal 6 ("zero-config start ... sensible defaults") forbids. The forecast fallback to "points-based capacity" is circular because capacity is derived from velocity. Agent identities that change per session never accumulate throughput.
- Why it matters: first-use experience and the "measured forecasts" promise.
- Suggested fix: specify bootstrap: capacity unenforced (PM010 advisory) until `min_history` cycles exist unless `capacity_points` is set; forecast below `min_history` reports Unresolved with the sample count; throughput pooled per identity class when per-identity samples are short.

### M13. PM021 drivers stop resolving once the objective succeeds; telemetry-based drivers and baselines are machine-local
- Where: pm-enforcement.md section 2a lines 62-64 and 74 (`finding:<fingerprint>`, `metric:<name>` "whose current value is outside a declared bound", `by = "telemetry:check"`); architecture.md line 114 (telemetry in untracked `.frob/telemetry.jsonl`).
- Finding: a quality objective that fixes its driving finding removes that finding, and a successful performance objective brings the metric inside its bound; PM021 ("driver resolves") then fires on the now-closed ticket unless PM rules skip terminal tickets, which is not stated. `metric:` and `telemetry:` sources live in untracked per-machine files, so CI and other clones cannot evaluate PM021/PM023 and get different results.
- Why it matters: rules that flip red on closed tickets and differ by machine erode trust in `frob check`.
- Suggested fix: evaluate drivers at transition time and record the resolved driver value in an event; PM rules on terminal tickets check the event, not current state; require tracked baselines (evidence records) instead of telemetry files.

### M14. PM rules cross the product boundary and put measurement on the close path
- Where: pm-enforcement.md lines 78-79 (PM025 runs the measurer at close; PM026 detects change to "a grimble `surface`"); architecture.md table line 61 (ticket mutation < 100 ms); boundaries.md lines 117-119 ("PM rules do not know about grimble").
- Finding: PM026 reading grimble surfaces contradicts boundaries 3.1; PM025 makes `close` run benchmarks (minutes) with no job/timeout contract.
- Suggested fix: PM026 uses the gob-symbols public-API graph only; declare `close` and `land` outside the 100 ms budget and give measurer runs the same job/timeout contract as tests.

### M15. Exception lifecycle relies on state that is not persisted
- Where: exceptions.md section 1 line 21 (REATTEST when "the bound symbol's body digest changes"), section 3 lines 76-79 (STALE from the incremental memo), lines 73-74 (`prune`), section 6 line 126 ("EXC004 Warn for 14 days then Error"); rules.md section 6 lines 205-208 and exceptions.md line 24 (baseline keys, pool only shrinks).
- Finding: an inline `frob:accept` carries no digest, so "changed since attested" has no stored attestation; "14 days" since what, with no recorded detection time; STALE from a memo is wrong after `--only` runs, rule version bumps or a deleted `.frob/` (unknown must not mean stale), so `prune` can delete valid exceptions. Baseline keys are "finding keys" with no fingerprint definition; if a key includes line numbers, an edit above a baselined finding makes it "new" (Error) and retires the old key, and pools can never re-add it.
- Suggested fix: store attested digest and date in `exceptions.toml` (or a lock entry) written by the accept verb; make `prune` and STALE require a fresh full evaluation of the rule for that file; define fingerprints as (rule id, symref or file, normalized message hash), never line numbers.

### M16. Capability matrix `n/a` silently passes, CAP-UNEXCUSED breaks repos on detector rollout, FOREIGN default is noisy
- Where: code-model.md section 7 lines 233-239 (`n/a` "never an error"; "nothing breaks repo-wide on day one"); grimble-model.md line 121 (CAP-UNEXCUSED: applicable atom neither granted nor excused) and line 177 (FOREIGN Warn until strict) and line 118 (SYS-UNMODELED for any public or effectful unclaimed symbol); rules.md section 1 line 25 ("unmeasured is not zero").
- Finding: a node in a language with no detectors gets a clean capability report, contrary to the "unmeasured is not zero" principle; conversely once a detector ships, CAP-UNEXCUSED requires every node to grant or excuse the atom, which is the repo-wide break code-model.md promises cannot happen. A repo adopting grimble with one node gets a Warn for every public symbol in the repo.
- Suggested fix: report `n/a` cells as Unresolved in the summary (one per node, not per cell); ship new atoms' CAP-UNEXCUSED as Advisory for one release via the baseline kind; make SYS-UNMODELED opt-in per selector (`[grimble] modeled = [...]`) rather than repo-wide Warn.

### M17. frob features that read grimble data contradict "frob never reads grimble"
- Where: tickets.md section 4 line 114 (`implements (-> grimble entity ...)`), grimble-model.md section 7 line 162 (`relates design:node/cli`); code-model.md section 6 lines 199-202 (affects, drift and test-evidence reach traverse `binds` edges) and line 154; grimble-model.md line 108 ("frob never reads them"); code-model.md line 239 (`frob check --census capabilities`).
- Finding: validating `design:node/cli` needs the grimble model parser; `binds` edges are `grimble:` directives resolved in grimble-bind, yet frob's evidence reach is supposed to cross them.
- Suggested fix: either move `binds` to a substrate namespace (`gob:binds` parsed by gob-symbols) or state frob gets grimble entities and binds only through `grimble --json` export (with an Unresolved fallback); fix the census verb to `grimble check --census`.

### M18. vet pre-install hook vs "grimble ships no hook"
- Where: boundaries.md line 93 (grimble-vet "pre-install hook") vs lines 159-162 ("grimble ships no hook"); notes/v1/ops-and-integrations.md line 343 (hook mode KEEP); git-io.md section 5 (one `frob hook` binary).
- Suggested fix: decide that `frob hook pre-tool` invokes `grimble vet --hook` as a sibling (allowed spawn) or that grimble ships `grimble hook`; update both sections.

### M19. Publishing: gob-* "never published" vs reserved and published names
- Where: monorepo.md line 11 ("shared gob-* crates that are never published") and line 68 (`publish = false`) vs line 98-100 ("only prefixed names ... are published"); products.md lines 84-88 (frob-cli on crates.io, gob names reserved).
- Finding: `cargo publish` of `frob-cli` requires every path dependency (all gob-* and frob-* crates) to be published too.
- Suggested fix: decide: either crates.io gets the full crate set (versioned in lockstep, as ruff does not) or crates.io gets nothing and distribution is cargo-dist binaries plus PyPI only; fix the three statements.

### M20. Migration loses or corrupts references
- Where: migration.md line 9 (new ULID per ticket, `aliases = ["T-0042"]`), line 11 (ack migration), lines 32-34 (old ids resolve forever); monorepo.md section 5 lines 87-88 (crunk tickets imported into the same ledger); goals.md lines 68-69 ("imports a v1 tickets/ tree and frob.lock; nothing else carries").
- Finding: (a) frob and crunk v1 ledgers both contain T-0001..T-NNNN; after importing crunk into the frob ledger, alias `T-0042` is ambiguous and "resolve forever" fails for one of them. (b) ULIDs minted at migration time all share one time prefix and lose creation order (H2 amplified); minting from v1 `created` dates (day granularity) clusters them instead. (c) "digests recomputed, acks carried" plus `frob ack --all` re-blesses every symbol that was stale under v1, hiding real drift. (d) `aliases` is not a field in tickets.md section 3. (e) goals.md's non-goal says only tickets and frob.lock migrate, while migration.md migrates config, waivers, directives and .strata files.
- Suggested fix: namespace aliases by source repo (`crunk:T-0042`), mint ULIDs from v1 created timestamps plus random bits and document the clustering, carry only acks that were current under v1 (re-verify with v1 hashing first, report stale ones), add `aliases` to the data model, update goals.md.

### M21. Documentation gates and generators are repo-internal tools presented as frob rules and verbs
- Where: documentation.md section 3 lines 56-58 and section 8 lines 127-139 (all inside `frob check`, GEN001 runs `cargo dev gen --check`), section 6 lines 100-103 (`cargo dev changelog` compiles CHANGELOG); build-test-ci.md lines 68-70; boundaries.md line 58 (gob-dev never shipped); boundaries.md line 73 (frob-release owns changelog fragments).
- Finding: GEN001 and changelog compilation call a binary that exists only in this workspace; consumer repos cannot use them, and `frob release` (frob-release) and `cargo dev changelog` (gob-dev) both claim changelog compilation. Running cargo doc, mdbook, lychee, typos, markdownlint and clippy "inside frob check" adds external spawns not in git-io.md's list and blows the check budget (H9).
- Suggested fix: express these as `[[check.tool]]` entries in this repo's frob.toml (not built-in rules), keep GEN001 as a repo-local tool stage, and give changelog compilation to frob-release with gob-dev calling it.

### M22. Authoritative state lives outside git despite the principle
- Where: goals.md lines 74-75 ("Nothing authoritative lives outside git"; `.frob/` delete-safe); rules.md lines 211-212 (`.frob/quarantine.json` circuit breaker that "clears only by disposition"); tickets.md lines 224-225 (`dir:.frob/artifacts` evidence store); cli.md lines 66-67 (plan tokens); H3 (job records); tickets.md section 6 (leases); M13 (telemetry baselines).
- Finding: deleting `.frob/` silently clears quarantine and loses the only copy of local evidence blobs (closed tickets degrade to Unmeasured).
- Suggested fix: move quarantine to a tracked file or ticket events, move the local artifact store default outside `.frob/` (e.g. `.git/frob/artifacts`) and state its non-authoritative status, and amend the principle to list the deliberate non-git state (leases, jobs, plans) with their loss semantics.

### M23. Idempotency is natural-key only; `new` dedupe can swallow distinct tickets; batch atomicity undefined
- Where: cli.md section 3 lines 57-68; notes/v1/agent-usage.md section 6.2 lines 514-516 (asks for client idempotency keys or natural keys and `--retry-for`).
- Finding: `new` with the same title within 10 minutes returns the existing ticket: two agents filing "fix flaky test in X" for different tests get one ticket, and the second body/scope is dropped with `ok: true`. No client-supplied idempotency key exists. `batch` is "one transaction" but may include verbs with non-git side effects (leases, worktrees), with no all-or-nothing rule or list of batchable verbs; `--apply <plan>` storage, TTL and "inputs changed" definition are absent.
- Suggested fix: add `--idempotency-key` (stored on the created event) and dedupe `new` only on (key) or on identical full request; restrict `batch` to ledger-only verbs with all-or-nothing semantics; define plan tokens as a digest of the inputs and the planned diff, stored nowhere (recomputed at apply).

### M24. Inline evidence transcripts are committed without redaction
- Where: tickets.md section 9 lines 229-230 (text under 16 KiB "may be stored inline in the event file"); notes/v1/ops-and-integrations.md line 346 (`security/redact` KEEP); architecture.md section 5 (telemetry records args shape).
- Finding: test and command transcripts routinely print environment, URLs with tokens, or secrets; inline storage puts them in tracked, append-only event files that are pushed. No crate owns redaction.
- Suggested fix: assign redaction to gob-log (or gob-exec output capture), apply it to evidence transcripts and telemetry, and add a SEC rule over `tickets/**/events/*.toml`.

### M25. The "second identity" review for accepts is bypassable
- Where: exceptions.md line 21 ("a `reviewed` event by a second identity or the owner") and section 5 line 106; tickets.md line 46 (actor from git identity or `FROB_AGENT`); gui.md line 29-30.
- Finding: the actor is any string the caller sets; an agent can set `FROB_AGENT=reviewer` and approve its own Error-severity accept. "Owner" is undefined.
- Suggested fix: say plainly this is an audit trail, not an authorization control, or require review evidence that is externally attested (signed commit by a listed key, or a GitHub review fetched by frob-gh); define "owner" in config.

### M26. ast-grep-core adopted for POL at grammar and IR level without resolving the noted risks
- Where: rules.md section 3 lines 144-146 ("Engine: `ast-grep-core` ... IR level implemented on the same matcher trait"); code-model.md line 178-179 (still "tentative"); notes/rust-ecosystem.md lines 435-436 and 779 (ast-grep ties its own tree-sitter version, "check before adopting"); architecture.md line 155 pins tree-sitter 0.27.
- Finding: if ast-grep-core resolves a different tree-sitter version, its patterns cannot run on gob-languages trees (two distinct `Tree` types); ast-grep's matcher is generic over its own `Doc`/`Node` traits, and an IR backend is an assumption, not a known extension point.
- Suggested fix: record a spike ticket (tree-sitter version unification, IR adapter for ast-grep's Doc trait) as a precondition and keep code-model.md and rules.md consistent ("decided pending spike").

### M27. README decision log is corrupted and stale
- Where: README.md lines 46 (D1 "single binary, ~22-crate workspace" vs three binaries and ~56 crates in architecture.md line 9), 62-64 and 66-67 (D18 and D20 rows have other table rows pasted into them, so D18's "Where" says exceptions.md and D20's says exceptions.md), line 70 (D10 after D22), line 17 (monorepo.md "frob + crunk"), line 3 ("Read in order" with no order matching the file set).
- Why it matters: the decision log is the authority that marks which file supersedes which.
- Suggested fix: rewrite the table (one row per decision, correct "Where", D-order), update D1, and add the supersession order (products, boundaries, exceptions, documentation, pm-enforcement win) to the README.

### M28. cli.md verb surface was not updated; several verbs have no owning crate
- Where: cli.md section 4 lines 80-109; tickets.md section 11 lines 250-255; boundaries.md section 2.
- Finding: verbs named in later files but missing from cli.md: `frob exceptions list|audit|convert|prune|budget` (exceptions.md line 69), `frob status` (exceptions.md line 95; boundaries.md line 135 says `status` is grimble-only), `frob narrative move` (documentation.md line 78), `frob rule test` (rules.md line 143), `frob batch`, `frob job ...` (as a group), `frob schema`, `frob tui` (gui.md line 51), `frob evidence fetch` (tickets.md line 227), `frob config sync` and `config show --effective` (architecture.md), `frob doctor --languages`, `frob migrate tickets|directives|config|waivers|exceptions`, `frob git -- ...` (git-io.md line 52), `log --since` (tickets.md line 172), `frob clean`, `frob2 compare` (migration.md line 24), `ticket unlink|body|migrate|reconcile|doctor` (tickets.md lines 251-254), `grimble migrate`, `grimble vet` (only "--only vet" exists), `grimble ack` (H7). cli.md line 81 keeps `migrate` while line 105 removes it; line 105 removes `merge-driver` while tickets.md line 70 requires a merge driver (git invokes it as a command). Owning crate is unnamed for: init, doctor, config, schema, stats, batch, exceptions, narrative, rule test, tui, clean, grimble explore (no grimble-explore crate; frob-explore is frob's).
- Suggested fix: regenerate cli.md section 4 from one verb table (verb, product, crate, idempotent?, exit codes) and resolve `status` and `migrate` naming; keep a hidden `frob merge-driver` entry point.

### M29. Ledger merge driver semantics and installation are undefined
- Where: tickets.md section 2 lines 67-71 ("last-writer-wins per field with an explicit `conflict` marker"); lines 60-61 (frontmatter is a cache of events).
- Finding: "last writer" has no clock (commit time, event ULID?); if the frontmatter is a cache of the events, the correct merge is to re-fold the merged event set, not LWW. A merge driver needs `.gitattributes` plus `git config merge.<name>.driver` in each clone (config is not cloned) and never runs on GitHub's server-side merge button, so web-merged PRs get textual conflicts or silent wrong merges.
- Suggested fix: define the driver as "union events, then re-fold frontmatter", have `frob init`/`doctor` install and verify the driver config, and add a TICK rule that re-folds and compares in CI to catch server-side merges.

### M30. Daemon fallback: version skew, staleness window, platform
- Where: git-io.md section 6 lines 86-91; build-test-ci.md line 80 (windows CI).
- Finding: the CLI transparently forwards to a running daemon, which may be an older binary (after upgrade) or may not yet have processed a file-watch event (agent edits a file, then immediately runs `frob check` and gets stale findings). Unix sockets and the watcher are not specified for Windows.
- Suggested fix: handshake on binary version and schema, refuse forwarding on mismatch; before serving a request the daemon re-stats inputs (or the CLI sends the git status snapshot); state Windows behaviour (named pipe or in-process only).

### M31. Quarantine and `[land] verify = "ci"` reintroduce the deferred verification D8 removed
- Where: rules.md section 6 lines 211-217 and section 7 lines 222-225; README.md D8 line 53; tickets.md section 10.
- Finding: quarantine is "raised by a red post-land verify", which only exists in `verify = "ci"` mode; who raises it (frob-gh polling CI?) and who disposes it (v1 `verify dispose` is KEEP in notes/v1/cli-surface.md line 219 but has no v2 verb) is undefined. `frob migrate` maps standard and fortress identically, so the distinction is lost without a note.
- Suggested fix: either drop `verify = "ci"` for milestone 1 or specify the CI-result ingestion path, the quarantine store (tracked), and a disposition verb.

### M32. KEEP items from the v1 inventories with no crate or verb
- Where: notes/v1/cli-surface.md lines 219 (`verify dispose`), 357 (`ticket done-report`, on the hot path per tickets.md line 211), 375 (`ticket tokens`, "filled from events automatically" with no producer named), 382 (`runs-last` for milestone tails, MILE001-004), 297-298 (`worktree sweep/remove`: frob-worktree mentions sweep, no verb), 114 and 270 (`clean`); notes/v1/ops-and-integrations.md lines 263 (flake quarantine), 496 (`ci_validity`, CI evidence staleness via affects), 604 (scaffold templates; code-model.md line 157 points to a "scaffold" feature that is not designed), 821 (tool-output parse library: rules.md line 186 "frob parses their output" with no owner).
- Suggested fix: add each to the boundaries.md capability map with an owner or to a "dropped" list with a reason (cut scope recorded, per goals.md line 84).

### M33. `[pm] strict`, `[check] strictness` and `[grimble] strict` overlap, and write-time refusal contradicts "Warn in a fresh repo"
- Where: pm-enforcement.md lines 19-21 ("Every field is checked at write time by the verb (refusal with the exact remedy)") vs lines 183-184 ("All PM rules are Warn in a fresh repo"); rules.md line 222; grimble-model.md line 177.
- Finding: if verbs refuse at write time regardless, `[pm] strict = false` changes nothing for new tickets and goals.md goal 6's "no errors" first use fails for stories.
- Suggested fix: write-time refusals follow the same severity as the rule (refuse only when the rule is Error), and document how the three strictness knobs compose.

### M34. Self-hosting milestone is defined to need all three products
- Where: build-test-ci.md table line 34 (self-hosting) and line 82 (self check merges grimble and crunk findings, plus `frob test`); monorepo.md section 5 line 80 (frob self-hosts first, grimble split later).
- Finding: the CI definition of self-hosting requires the bundle, grimble and crunk, contradicting the migration order where frob self-hosts before grimble exists.
- Suggested fix: define milestone 1 self-hosting as frob-only (see the cut below) and add sibling merging in a later milestone.

### M35. Evidence store URIs assume network clients and long-lived artifacts
- Where: tickets.md section 9 lines 224-231 (`gh-artifact:`, `gh-release:`, `s3:`/`gcs:`, https).
- Finding: no crate owns S3/GCS/HTTP clients or credentials (frob-gh is GitHub only); GitHub Actions artifacts expire (default 90 days), so closed tickets' blob evidence degrades to Unmeasured over time by design.
- Suggested fix: milestone 1 supports `dir:` and https only; state retention expectations and that Unmeasured on terminal tickets is not a finding.

### M36. Ticket narrative rules and ADR numbering reintroduce counters and v1 id syntax
- Where: documentation.md lines 14-15 (`(T-...)`, `TODO(T-...)`), line 74 (`frob:todo T-...`), section 5 lines 90-91 (ADRs "Numbered, never reused"), exceptions.md line 39 (`0007-...`); NARR003 line 70.
- Finding: sequential ADR numbers collide across concurrent worktrees, the exact problem D2 removed for tickets; NARR rules match `T-...` syntax that v2 ids do not have and cannot reliably detect 6-char ULID prefixes in prose.
- Suggested fix: use ULID (or date-slug) ADR file names with a generated display number in the index; define the ticket-id regex NARR uses (full 26-char ULID, `prefix-` display form, v1 aliases).

---

## LOW

### L1. Old names survive (strata, frob-*, gob-syntax, rules-*)
- Where: grimble-model.md line 1 (title "Strata: ..."), lines 24-43 (example `module frob`, `crates/frob-cli/**`, `crates/frob-syntax/...`), line 86 ("ported from strata-core"); code-model.md line 19 ("the gates crate"), line 257 (`StrataEntity`); goals.md line 118 ("every strata node"); architecture.md lines 49, 93 (`frob-diagnostics`), 94 (`frob-dev generate-all`); rules.md line 63 (`crates/rules-<family>/src/`); boundaries.md lines 45, 75, 106, 116, 131, 150, 168 (`gob-syntax`, which section 4 splits into gob-symbols/gob-ir) and section 2.1 omits gob-symbols, gob-ir and gob-serve; monorepo.md line 99 (`gob-syntax`); products.md line 13 (`<design goblin> (name below)`), line 67 ("file renamed grimble-model.md when accepted", already done), products.md line 87 (`gob-syntax` reserved: a crate name that no longer exists in the design); monorepo.md line 1 ("frob and crunk in one workspace") and line 71 ("covers both").
- Suggested fix: search-and-replace pass; reserve `gob-symbols`/`gob-ir` instead of `gob-syntax`.

### L2. Numbered references, stale placeholders and ordering
- Where: boundaries.md line 35 ("docs 01 to 13"); goals.md line 4 ("its own numbered file"); tickets.md lines 5-6 ("Sections 7 and 8 are placeholders until notes/jira.md and notes/v1/agent-usage.md land": both exist and the sections are written); code-model.md lines 4-5 and 179 ("tentative ... await notes/rust-ecosystem.md"); v1 ticket ids as rationale: code-model.md lines 57 (T-0556), 247 (T-4484), build-test-ci.md line 89 (T-4338); `T-...` placeholders in grimble-model.md lines 55, 155; goals.md list numbered 1-6, 8, 7 (lines 57-60); products.md sections ordered 1, 2, 3, 4, 6, 5; monorepo.md lines 75-76 (garbled "gob-* tickets are likewise").
- Suggested fix: replace numbered refs with file:section names, remove placeholder notes, renumber lists and sections.

### L3. Generated-artifact paths and generator command names disagree
- Where: build-test-ci.md section 3 (`docs/rules/<ID>.md`, `docs/directives.md`, `docs/config.md`, `docs/<product>/cli/*.md`, `cargo dev generate-all --mode check`); documentation.md sections 2-3 (`docs/<product>/reference/...`, `cargo dev gen <kind>`, `cargo dev gen --check`); rules.md line 59 (`docs/rules/`); code-model.md lines 103-104, 138 (`docs/languages.md`, `docs/directives.md`); architecture.md line 94 (`docs/errors.md`); `decisions/*.md` (architecture.md line 76, boundaries.md line 113) vs `docs/decisions/` (documentation.md, exceptions.md line 39); `invariants/*.md` vs `invariants/INV-*.md` (migration.md line 15).
- Suggested fix: one path table in documentation.md; others link to it.

### L4. Substrate layering statement is self-contradictory
- Where: architecture.md lines 30-32 ("text < db < ... < directives < rules; `gob-rules` and `gob-macros` depend on nothing else in the workspace"); boundaries.md line 37 ("library only, never a binary") vs gob-dev being the `cargo dev` binary (architecture.md line 24).
- Suggested fix: gob-rules needs gob-text spans at least; state the real DAG and mark gob-dev as the one substrate binary.

### L5. Rule metadata enums disagree
- Where: rules.md line 38-39 (`tier = Universal | Lang | Graph | Repo`, `fix = Manual | Deterministic | VerifyCommit | FixIt`) vs line 22 (`scope = Repo`) and lines 186-189 (tiers A/B/C); rules.md line 123 (`severity = "warn"` lowercase in TOML) vs enum `Warn`.
- Suggested fix: separate `tier` (universal/lang) from `scope` (file/repo) and map fix enum to A/B/C explicitly.

### L6. MCP flag spelling and tokio placement
- Where: cli.md line 99 (`grimble ... serve --mcp`) vs boundaries.md line 27 and architecture.md line 147 (`--mcp`); boundaries.md lines 203-204 (`grimble-check --mcp` uses tokio) vs architecture.md line 174 and build-test-ci.md line 11 (tokio only in serve and gh crates); crunk has no MCP in notes/crunk.md section 1 though boundaries.md line 27 gives every product `--mcp`.
- Suggested fix: one spelling (`serve --mcp`), put grimble MCP in a `grimble-serve` crate on gob-serve so grimble-check stays sync.

### L7. Goals and later files disagree on features
- Where: goals.md line 37-39 (watchers, automation rules) vs tickets.md line 172 (watchers: none); goals.md line 65 (consumes LSP/SCIP) and line 70 (optional PyO3 leaf crate) with no crate in boundaries.md.
- Suggested fix: align goals with tickets.md, or list LSP/SCIP/PyO3 as deferred in boundaries.md.

### L8. gh token from the gh config file is likely absent
- Where: git-io.md section 4 lines 67-69.
- Finding: current gh stores tokens in the OS keyring by default, not in hosts.yml, so "the gh keyring via its config file read-only" finds nothing.
- Suggested fix: env tokens only, or read the keyring explicitly via a keyring crate behind a feature.

### L9. Spawn list omits spawns the design itself requires
- Where: git-io.md section 3 lines 44-52 and line 56 (PROC001: only gob-git and gob-exec reference std::process, yet "every spawn goes through one gob-exec runner"); boundaries.md line 30 (sibling `--json`), documentation.md section 8 (cargo, mdbook, lychee), monorepo.md line 60 (node Tailwind, playwright), git merge driver invocation.
- Suggested fix: list all spawn classes with bounds in git-io.md section 3; let only gob-exec reference std::process.

### L10. Velocity and capacity definitions are inconsistent
- Where: pm-enforcement.md line 115 (velocity = points of stories), line 90-92 (PM029 counts chores and objectives in committed points), tickets.md line 179 ("capacity = concurrent leases per identity").
- Suggested fix: one definition of which types count toward velocity and capacity.

### L11. code-model.md section 10 contradicts section 6 on binds
- Where: code-model.md lines 269-271 ("`binds` is inferred from binding attributes ... directive only for `manual` or to override") vs lines 187-198 (directive per binding).
- Suggested fix: update section 6 to describe inference first.

### L12. Event ordering within one millisecond across processes
- Where: tickets.md lines 57-58 ("The ULID in the file name orders events by creation time").
- Finding: ULID monotonicity holds only within one generator; two processes in the same millisecond produce random order.
- Suggested fix: order by (ULID time, then `at`, then a per-ticket sequence check in the fold) and accept ties as concurrent.

### L13. Display prefix form `FRB-01J9QK` is not in the directive grammar
- Where: tickets.md lines 26-27.
- Suggested fix: say whether directives and commit messages accept the display prefix form or only bare ids.

### L14. `T-0001` itself is a v1-format id
- Where: every file's Status line ("DRAFT (T-0001)"); README.md line 4.
- Finding: harmless now, but the design's own acceptance tickets will need aliases at migration (M20).
- Suggested fix: note that T-0001 is a v1 ledger id that migrates with an alias.

### L15. `land` deliverables overlap REL003 and `[pm.done] changelog_fragment`
- Where: documentation.md lines 103-107 (REL003, land writes skeleton), pm-enforcement.md line 103, rules.md line 94 (VERSION "changelog fragment present").
- Suggested fix: one rule id for "fragment present".

### L16. `frob check --census capabilities` names grimble data on frob
- Where: code-model.md line 239.
- Suggested fix: `grimble check --census capabilities`.

### L17. Kotlin/partial-parse and per-file guards from v1 not carried
- Where: notes/v1/graph-lang-dsl.md section 8.1 ("per-file size cap and parse timeout"; binding rule "following within 2 lines beats enclosing"; frob:tests canonical reorientation) not stated in code-model.md sections 3-4.
- Suggested fix: add them to code-model.md as unchanged semantics.

### L18. Positive-control and pair-fixture doctrine not stated for rules
- Where: notes/v1/strata.md lines 794-796 and 853-855 (KEEP); rules.md section 8 mentions mdtests only; pm-enforcement.md line 180 uses "positive control" for PM015 only.
- Suggested fix: require every rule's mdtest to include a firing and a non-firing case (generated test).

### L19. JUnit emitter dropped silently
- Where: notes/v1/ops-and-integrations.md line 814 ("add SARIF and JUnit emitters"); boundaries.md line 49 (gob-diagnostics: text, JSON, SARIF, GitHub annotations).
- Suggested fix: add JUnit or record it as dropped.

### L20. `--ticket` scoping rule is described twice differently
- Where: rules.md lines 165-168 ("ticket's files plus one hop of dependents") vs cli.md and tickets.md (scope-and-lease context only).
- Suggested fix: one definition, with the hop count as a knob (M6).

### L21. `frob work` worktree location and naming unspecified
- Where: cli.md line 89, boundaries.md line 67.
- Finding: v1 telemetry shows `--worktree` was mandatory in practice (agent-usage.md line 563); v2 says nothing about where worktrees are created or how `work` finds an existing one for idempotency.
- Suggested fix: specify the path convention (e.g. sibling dir keyed by full ticket id) and reuse rule.

### L22. Scope creep visible in the set (deferrable for milestone 1)
- Where: gui.md (web GUI, SSE, TUI); pm-enforcement.md sections 4-6 (cycles, Monte Carlo forecasts, Little's law ETA, flow metrics); tickets.md section 7 (triage inbox, fractional rank, query language, saved queries, boards, custom fields, cross-repo links); tickets.md section 9 (s3/gcs/gh artifact stores); tickets.md section 6 (symbol-level and append-mode leases); code-model.md sections 5-7 (IR, binds, capability matrix); rules.md section 3 (declarative POL at two levels), SARIF; grimble-model.md section 5 (data packs); boundaries.md (frob-fleet, frob-gh, frob-release, frob-serve, grimble-vet, grimble-security, all crunk crates); git-io.md section 6 (daemon); exceptions.md section 4 (budgets, audit sampling).
- Finding: none of these is needed for frob to check its own repository; carrying them into the first milestone delays the self-hosting proof on which the rollout (migration.md section 2 step 1) depends.
- Suggested fix: adopt the milestone-1 cut below and record the rest as tickets in a later milestone.

---

## Notes

Checked and found consistent (no finding):
- Directive grammar carried from v1 (code-model.md section 4) matches notes/v1/graph-lang-dsl.md section 8.1 except the items in L17.
- Symref grammar and three-facet digests (code-model.md section 2) match the v1 KEEP list; acks remain endpoint-only.
- Cache key including parser identity (code-model.md section 8) addresses T-4484 correctly.
- License (MIT) and repository name decisions are stated once and consistently (monorepo.md section 6, goals.md line 90).
- Release tags `frob-v*`, `grimble-v*`, `crunk-v*` are consistent across products.md, monorepo.md and build-test-ci.md.
- Exception kinds, budgets and EXC ids are internally consistent within exceptions.md (the problems are cross-file, M3/H6/M15).
- PM rule ids are internally consistent within pm-enforcement.md (PM030 in section 1 is not in the section 7 table; minor, folded into M8's spirit of undefined ids).
- gix capability claims for reads (discover, status, diff, merge_base, rev_parse, blame, refs transactions, commit) are plausible and the design already keeps git fallbacks for worktree add, merge conflicts and push.

Skimmed or not verified:
- notes/jira.md, notes/documentation.md and notes/v1/gates-and-rules.md were used only for cross-reference spot checks (KEEP/MERGE tables), not read line by line; the 145 KEEP rule ids were not individually mapped to families.
- Crate versions (salsa, gix, tree-sitter, ast-grep, rmcp) were not checked against crates.io; M11 and M26 flag the API assumptions to verify in spikes.
- notes/rust-ecosystem.md itself disagrees on gix (0.81 at line 6, 0.88 at line 437) and tree-sitter (0.25.10 vs 0.27); not a design-file finding.

---

## Proposed milestone-1 cut (frob checks its own repository)

Goal: `frob check` and `frob land` run green on this repo with tickets
in the v2 ledger, using only Rust and markdown adapters. No grimble,
no crunk, no GUI, no daemon.

| Crate | Verbs | Rules | Why first |
|---|---|---|---|
| gob-text | - | - | spans for every finding |
| gob-config | `frob init`, `frob config show --effective` | CFG001 | materialized knobs from day one (owner rule) |
| gob-languages (features: rust, markdown, toml) | - | - | only grammars this repo needs |
| gob-symbols (symbols, digests, imports, call graph per M1) | - | PARSE | DRIFT/AFFECT/COV and test selection need it |
| gob-directives (`frob:` namespace only) | - | DSL | directives bind code to tickets and docs |
| gob-rules (registry, Finding, exception primitive: accept and defer only) | - | EXC001, EXC003, EXC005, EXC007 | suppression must exist before rules ship as Error |
| gob-macros (Rule, Directive, ConfigTable, Command, TicketField) | - | - | declare-once is the core productivity bet |
| gob-diagnostics (text and JSON envelope, exit-code table per H5) | `--json`, `--schema`, `frob schema` | - | agent contract is the hot path |
| gob-walk, gob-cache (parse and findings cache per H9) | - | - | speed target needs persisted findings |
| gob-git (reads, ledger commit per H1, CAS ref) | - | - | ledger writer story must be proven first |
| gob-exec (bounded pool, spawn counter) | - | PROC001 | test runners and git fallbacks |
| gob-cli, gob-log, gob-mdtest, gob-dev | `cargo dev gen` | GEN001 as a repo-local tool stage | generated docs and mdtests from the start |
| frob-ledger (ULID full ids per H2, events, index, merge driver per M29) | `ticket new/show/list/update/link/comment/accept/start/requeue/close/drop/reopen/doable/brief`, `frob merge-driver` (hidden) | TICK (integrity subset) | dogfood tickets in v2 |
| frob-lease (file-glob leases, lock per H4) | via `work`/`start`, `ticket contention` | SCOPE | multi-agent safety |
| frob-worktree | `frob work` | - | the agent entry point |
| frob-evidence (cargo test/nextest and command providers, `dir:` store) | `ticket evidence` | TEST (binding resolves) | evidence-bound closure is the differentiator |
| frob-tests (Rust touched-set) | `frob test --base` | - | proves work cheaply |
| frob-ack | `frob ack`, `frob graph why/affects` | DRIFT, AFFECT | doc drift is the original frob value |
| frob-obligations (subset) | - | COV, TODO, DOC, REF, INV | accounting gates for this repo |
| frob-check | `frob check [--ticket] [--fix] [--json]` | orchestration, Tier A fixes | the one command agents run |
| frob-land (synchronous, no jobs per H3) | `frob land [--dry-run]` | land preconditions | closes the loop: work -> check -> land |
| frob (bin) | `frob doctor` | - | install health |

Deferred to milestone 2 and later: gob-db/salsa (start with per-file
SQLite memo, add salsa when the daemon arrives), gob-ir and all
universal IR rules, gob-serve, frob-serve (MCP, HTTP, GUI, TUI), daemon,
jobs, frob-pm (cycles, forecasts, PM rules beyond optional story
fields), frob-release, frob-fleet, frob-gh, frob-hook (keep v1 hooks
meanwhile), exception kinds hotfix and baseline plus budgets and audit,
declarative POL rules, SARIF, symbol-level and append-mode leases,
Jira-parity features (triage inbox, query language, boards, rank,
custom fields), external evidence stores, every grimble crate, every
crunk crate, the `bundle` feature, migration tooling for consumer
repos (only this repo's own tickets are needed, and they can be
re-filed or imported by a one-off script).
