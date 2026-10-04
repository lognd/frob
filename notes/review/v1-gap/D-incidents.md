# v1 gap analysis, slice D: structural bugs and operational lessons

Status line (read this first): nothing is pending and nothing is blocked. 45 failure classes were
enumerated and every one has a status and a proposed action. Statuses: BUILT 16, TICKETED 7,
DESIGNED 5, DROPPED-ON-PURPOSE 3, MISSING 14. Section 4 lists 14 structural bugs in v2: 7
reproduced with the built binary (SB-1 to SB-6 and SB-12) and the rest established by reading
source. 22 tickets are proposed (section 3). Limits of the proof are stated in section 1.4 and
section 5; the main one is that ticket-to-class assignment for the 595-ticket corpus is
machine-assisted and hand-corrected, not an individual read of every body.

Scope and method: v1 is the Python frob (read only), v2 is the Rust rewrite (read only except this
file). v2 ticket ledger read through the built binary (`frob ticket list|show --json`, 481 tickets
at the final refresh, 3 of them filed by sibling slices while this pass ran). v2 behaviour probes
ran the built v2 binary against throwaway git repositories in the session scratchpad; no v2 or v1
file was edited and no v1 test or frob was run. The binary was built on 2026-10-04 at about 00:46
local, source read at branch `experimental` (HEAD at the time: e8813e4f0).

Sibling slices already written (A-keep-recommendations.md, B-backlog.md, C-features.md) overlap
this slice in places. Where a sibling proposes the same ticket it is referenced, not duplicated.
One sibling verdict is contradicted by a probe here: A S-20 and B structural bug 32 say leases
release on every terminal transition; they do not (SB-2).

## 1. Inventory

### 1.1 What was enumerated (denominator)

| Source | Count | Enumeration command (v1 checkout) | Accounted how |
|---|---|---|---|
| v1 tickets, live | 1,243 | `ls -d tickets/T-* \| wc -l` | scanned |
| v1 tickets, archived | 3,906 | `git ls-files tickets \| grep -c 'tickets/archive/.*/ticket.md'` | scanned |
| v1 tickets total | 5,149 | sum of the two | frontmatter parsed for all 5,149 |
| tickets with `kind: incident` | 2 | `grep -l '^kind: incident' tickets/*/ticket.md tickets/archive/*/ticket.md` | T-1323 (critical, done) and T-3338 (a baseline measurement, queued, not an incident) both read |
| strict title hits (data loss, corrupt, race, deadlock, hang, lock, revert, clobber, truncat, orphan, collision, disk, ...) | 366 | regex over titles, listing printed and read in full | clustered into classes |
| body hits not in the strict set (bug/security/incident kinds, not dropped: "incident", "data loss", "silently dropped/reverted", "clobber", "deadlock", "wiped", "resurrect") | 229 | regex over first 3,000 chars of body, titles printed and read in full | clustered into classes |
| incident corpus (strict union body) | 595 | union of the two | appendix A gives per-class counts and ids |
| broader title keyword set (not read one by one; used only to size the field) | 1,099 | broad regex over titles | context only |
| v1 CHANGELOG.md | 5,892 lines | `wc -l CHANGELOG.md` | 94 lines mention "revert"; the file is generated from tickets (T-2615: 101 duplicated id lines) so it is a secondary source only |
| v1 changelog.d fragments | 1,542 | `ls changelog.d \| wc -l` | derived from tickets; no independent evidence |
| v1 force-overrides.jsonl | 3 entries | `wc -l force-overrides.jsonl` | all 3 analysed (section 1.2) |
| v1 rapid-debt.jsonl | 3,384 entries over 1,215 distinct tickets | `wc -l rapid-debt.jsonl`, python tally | all 6 reasons analysed (section 1.3) |
| v1 lock files | 4 | `ls frob*.lock*` | ratchet 5,689 entries in 2 pools, deprecated-baseline 4 entries plus 2 pins, coverage 477 module floors, frob.lock 133 commits of churn |
| v1 git history | 19,211 commits (18,931 non-merge) | `git log --oneline \| wc -l` | subject greps: revert 12 (all read), hotfix 3, incident 38, corrupt 50, deadlock 43, data loss 1, race 72, regression 493; about 210 non-ticket-filing subject lines read |
| v2 design | docs/design/*.md (33 files), notes/v1/tickets.md | read for the sections cited | decision log D1-D87 |
| v2 ledger | 481 tickets (243 todo, 226 done, 9 in progress, 3 new) | `frob ticket list --json` | grepped by 40+ terms, 8 tickets read in full |
| v2 code | 12 frob-* and 15 gob-* crates | read: frob-ledger, frob-land, frob-lease, frob-worktree/gc, gob-git/ledger, gob-cache, gob-exec, gob-check/fix, frob-check/product, gob-trust, frob-release | cited per finding |

### 1.2 force-overrides.jsonl (3 of 3 accounted)

Each line is a guard that blocked something the operator judged legitimate and that was forced
through with a recorded reason. Read as: either the guard was wrong, or the world around it was
leaking state.

| Entry | Guard that blocked | Reason recorded | Reading | v2 |
|---|---|---|---|---|
| 2026-08-26 `ticket land --finish`, target T-2935 | T-1715 worktree-in-use refusal | own work landed and verified; epic T-2920 deliberately left open; tree clean | guard conflated "worktree shared by a series" with "in use"; v1 shared one worktree across a series of tickets | v2 has one ticket per worktree (lease holder worktree, `check_worktree`); series worktrees are not a v2 shape (B PT-10 asks the owner to decide). BUILT by absence |
| 2026-09-20 `ticket archive`, 71 targets | T-0843 live-cross-worktree-lease refusal | whole-ledger archive of done tickets during a paused land window | leases of terminal tickets were still "live" (v1 T-4172, T-4388, T-4383 reconciliation chain) so archiving done tickets was refused | v2 has no archive operation (archive is a view, tickets.md 2), so the symptom cannot occur, but the cause (lease of a closed ticket stays live) reproduces in v2: SB-2 |
| 2026-09-20 `ticket archive`, 41 targets | same | automatic archive after the land queue drained | same | same |

### 1.3 rapid-debt.jsonl (3,384 of 3,384 accounted)

A rapid-debt line is a gate skipped at land time because it was too slow, to be paid by a deferred
sweep. 1,215 of 5,149 tickets (24 percent) landed with at least one deferred gate.

| Reason | Lines | Tickets | v1 meaning | v2 disposition |
|---|---|---|---|---|
| land-evidence-scope-unbound | 1,733 | 1,079 | land could not bind evidence to scope within budget | DROPPED-ON-PURPOSE: land is synchronous, evidence is bound per criterion by events (rules.md 6, 7; D36). Guard against reintroducing the pressure: P-22 |
| post-land-unscoped-sweep-deferred | 1,153 | 1,129 | unscoped check deferred to a detached sweep | DROPPED-ON-PURPOSE (same) |
| close-rel001-preflight-skipped | 361 | 237 | REL001 version-bump preflight skipped | BUILT replacement: per-ticket changelog fragments plus `release cut`, no per-land bump (REL003, REL002, frob-release bump.rs) |
| post-land-sweep-attribution-skipped-stale-baseline | 58 | 42 | sweep could not attribute a regression | DROPPED-ON-PURPOSE (no sweep) |
| missing-evidence-or-done-report | 47 | 37 | close with no evidence recorded | BUILT: DoneGuard/EvidenceGuard; bypass only with a reason and an `evidence-bypass` event |
| evidence-scope-unbound | 31 | 28 | variant of the first | DROPPED-ON-PURPOSE |
| (a single `{"test": "repro"}` row) | 1 | 1 | test noise | none |
| Total | 3,384 | | | |

Related v1 cost evidence: 1,153 "post-land sweep regression from ..." tickets were filed by the
machinery itself (T-2477 ... T-6xxx), the quarantine circuit breaker deadlocked the fleet four
times (T-2312, T-3051 "UNFIXED", T-3378, T-3082), and T-3025 records one trivial unattributed
finding disabling fleet-wide landing. All of that machinery is deliberately not rebuilt in v2.

### 1.4 Limits of the proof

1. The 595-ticket corpus was clustered by title; bodies were read for roughly 60 tickets that
   carry the load of the findings (T-0889, T-0907, T-0959, T-1323, T-1536, T-1721, T-2255,
   T-3195, T-4159, T-4287, T-4343 and others). Appendix A is an index, not a classification
   proof; 98 tickets landed in "v1-internal tooling or docs, no v2 analogue".
2. Probes (section 4) are against the built debug binary of 2026-10-04 00:46; tickets landed
   after that are not reflected.
3. Windows behaviour was not probed (Linux host).
4. Single-ticket-per-worktree is assumed; the `frob start` (no worktree) path was probed only for
   lease behaviour.

## 2. Ranking and findings table

Ranking rule: data loss and ledger corruption first, then wrong gate decisions, then
availability, then usability. Within a tier, by v1 severity and recurrence. "Prevented" is a v2
verdict: yes (design and code, with a test or probe), partial, no. Ticket ids are v1 (`T-nnnn`)
or v2 handles (`~XXXXXXX`). Paths are `v1/` or `v2/` relative.

### Tier 1: data loss and ledger corruption (F-01 to F-14)

| Rank | Failure class (v1 failure mode) | v1 evidence | Status | v2 evidence | Prevented |
|---|---|---|---|---|---|
| F-01 | Stale-snapshot or whole-file ledger write clobbers, reverts or resurrects other tickets; land splice and archive clobber | T-0889 (stale in-memory map reverted 3 done tickets to queued), T-0633, T-0764, T-0959 (62 archive blocks wiped by one land), T-1154 ("3rd occurrence" of wrong-side merge), T-1437, T-1617, T-1721 (critical, "silent ledger data loss"), T-1914, T-2328, T-3163; v1 ledger-v2.md section 0 "incident museum" | BUILT | one directory per ticket plus append-only event files and a fold (tickets.md 2, 2a; D7 no splice, no mirror); every write is a CAS ref update from the ref tree (v2/crates/gob-git/src/ledger.rs, frob-ledger/src/ledger.rs). Tests: v2/crates/frob-ledger/tests/ledger.rs `concurrent_writers_on_one_ticket_lose_no_events_and_leave_the_frontmatter_consistent`, `merge_driver_unions_events_and_refolds`; v2/crates/gob-git/tests/ledger.rs `concurrent_writers_lose_nothing`. Probe: 24 parallel `ticket new` and 50 concurrent `ticket comment` on one ticket lost no event and left the tree clean | yes |
| F-02 | Killed or crashed land resets main to a stale tip or unwinds past landed commits; staged residue strands the fleet | T-0907 (about 60 commits off-branch, SIGTERM mid land), T-1495, T-1522, T-2714, T-2189 (dry run made a real merge on main); v1 docs/design/land-checkpoint-durability.md (gap 3 never fault-injected) | BUILT | land never resets or unwinds: it merges the base into the ticket branch, then fast-forwards the base by `git merge --ff-only` or `update-ref old new` CAS (v2/crates/frob-land/src/land.rs, `Publish::advance`); nothing is written before the CAS, a crash resumes by rerunning. Tests `dry_run_plan_is_deterministic_and_changes_nothing`, `conflicting_base_refuses_with_paths_and_leaves_the_worktree_clean`, `wait_retries_a_base_that_moved_*`. Gap: no fault-injection test of the steps after the CAS (F-34, P-09) | yes (structure), untested after CAS |
| F-03 | Ticket id collisions: counter allocators, draft ids, promote, renumber, quarantined drafts, lost drafts | T-0012, T-0162 ("structurally impossible"), then T-1090, T-1179, T-2092, T-2105, T-2122 (11 collisions in one window), T-3638, T-3639, T-4436, T-5415 | BUILT | ULID at creation, no counters, no drafts, no promote, no renumber (tickets.md 2). Handles are display only and ambiguity refuses (test `handles_resolve_and_ambiguous_suffixes_refuse`, `alias_ambiguity_lists_both_candidates`) | yes |
| F-04 | In-band delimiters inside ledger text corrupt the document (a done-report line equal to a section marker forged a boundary and corrupted a neighbour) | T-1536 (duplicate foreign block broke whole-store YAML load), T-1541 (audit of marker-lookalike entry points), T-0740, T-2270 (evidence silently dropped the Done report body when re-serialising), T-0367 | MISSING | v2 removed section markers (events are separate TOML files), but reintroduced the class with the `+++` fence of `ticket.md`: any frontmatter text field containing a line that is exactly `+++` makes the file unparseable and the ticket disappears from a rebuilt index; `ticket doctor --fix` cannot repair it. Probe SB-1. Code: v2/crates/frob-ledger/src/doc.rs `split_fenced` | no |
| F-05 | Tier-A auto-fix corrupts or deletes user files; killed fix leaves half-applied rewrite; fixer edits out of scope | T-1900 (SYS-IFACE-ORDER corrupted design/frob.strata on every land; six repair commits e1a603603e, 3fc5b3ffc0, e2370a6ca9, c9e4939a3b, e04f8592bc, f184bb172f), T-1903, T-3526, T-5289 (wrong source lines deleted, per-file line numbers from the pre-fix snapshot), T-6535, T-2284, COV002 fixer corrupting non-Python files (5bdf02c3e3) | MISSING | v2/crates/gob-check/src/fix.rs: writes with `std::fs::write` (truncate then write, not atomic), applies byte ranges computed at check time with no check that the file is unchanged (no digest precondition), never re-parses the result, records a fix in `applied` before its edits run and only warns when an edit is skipped as out of range, returns an error after earlier files are already written (no rollback). Latent today (no shipped Deterministic fix yet, test comment in frob-check/tests/check.rs) but D78 and ~R5QDX7H build on it. SB-7. Related: B PT-5 (read-only verbs leave the tree unchanged) | no |
| F-06 | Waivers or exceptions deleted by a degraded or mass-invalidating run | T-1323 (incident, critical: land WIP snapshot stripped 50 PERF waivers), T-1326, T-1579 (revert 7597ba37a0: WAIVE004 self-heal deleted 55 live waivers), T-3858 family | DESIGNED | exceptions.md 3: STALE is decided only from a fresh full evaluation, never from a cached memo, an `--only` run, a rule version bump or a deleted `.frob/`; `exceptions prune` evaluates itself before removing. Not built (no EXC013, no prune: crates/frob-obligations/src/exc.rs has only EXC001/003/005/007) and not ticketed (only ~B7VH1B4 for EXC016/017). B PT-11 touches waivers but not this guard | partial (nothing deletes yet) |
| F-07 | Ledger or tooling writes dirty or absorb the shared checkout; a stale or dirty checkout silently reverts a ledger commit; staged index content swept into a commit | T-1054, T-1432, T-1698, T-1699, T-1779 (five stalls and one corrupted ticket state), T-1841, T-1936, T-2026, T-2046, T-2274 (bystander edit absorbed), T-2481, T-2671, T-2714, T-3126, T-4199; T-0505 (off-branch write reverted a finalised ticket) | MISSING | v2 builds commits from the ref tree, never the index (test `staged_unrelated_file_is_untouched`; D23) and syncs other checkouts under index.lock, but `CommitOutcome.unsynced` (checkouts left stale because of local edits) is dropped above gob-git (grep: no consumer outside v2/crates/gob-git/src/ledger.rs). Probe SB-3: the verb reported success with `warnings: []` while the primary checkout showed the new event file as a staged deletion; a `git commit -a` there reverts the ledger commit | partial |
| F-08 | A ticket reaches done while its work is on no mainline ref; worktree or branch removed without merging; empty land proof | T-3195 (done-report with no changed files and no evidence reached main), T-3288 (`land --finish` DELETED a worktree without merging), T-1920, T-1950, T-1934/T-1955, T-3064/T-3087/T-3092 (done while blocked) | TICKETED | ~CKZS2R3 (in progress, filed by slice C this session) covers unmerged branch commits at close and a doctor check. Not covered: tickets.md 3 also names `no_open_blockers` and `lease_free` guards; code has only the outcome, evidence, criteria, children and fragment guards (SB-12, P-11). v2 gc keeps the branch of an unmerged closed ticket (v2/crates/frob-worktree/src/gc/worktrees.rs `delete_branch: merged`) so commits survive; A S-7, B PT-1, C P-01 | partial |
| F-09 | Derived state corrupt or stale bricks every verb or serves old answers (index, caches) | T-0019, T-0141, T-0243, T-0517, T-0798, T-1416 (recreate on a concurrency error destroyed a shared cache), T-2723 (cache not invalidated by an upgrade), T-3607 (SIGBUS), T-3634, T-4159 (PRAGMA integrity_check failed; a consumer served a stale finding), T-4412, T-0570 | MISSING | stale-by-engine is BUILT (v2/crates/gob-cache/src/lib.rs `default_engine`, test `engines_never_share_findings_or_repo_rules`, ~1EZ3QHP). But a corrupt `.frob/tickets.sqlite` makes every ticket verb fail with E-INTERNAL and `frob check` degrades silently (SB-4), and a corrupt cache.sqlite becomes a permanent null cache with no recovery or notice (gob-cache `open_with`). Distinguish corruption from busy (T-1416, T-4412 lesson) | partial |
| F-10 | A cache of a gate result is keyed by input only, not by the engine that computed it | T-0798, T-2723, T-4159; v2 ~1EZ3QHP found the same in repo-level rules | MISSING | land's base finding set is cached per base oid with no engine or config key (v2/crates/frob-land/src/ratchet.rs `BaseSet {oid, findings}`, `read_cache` checks only the oid). A newer binary or changed rule set reuses an older binary's base set, so the ratchet mis-classifies findings as new or pre-existing. SB-8 | no |
| F-11 | Decision-bearing derived state is writable by the repository, tamperable or torn | T-0859 (DERIVED001 TOCTOU), T-0570 (integrity manifest); v2 security.md 2.2 (I4) | TICKETED | ~TX6YZZE (in progress: MAC, outside the work tree, atomic writes), ~H2DAC49, ~FSG8SMS, ~WESVR7H done (gob-trust, tests `mac_verifies_and_one_byte_change_fails`, `concurrent_first_use_yields_one_key`) | in progress |
| F-12 | Ratchet, baseline and coverage locks: failed run lowers floors, committed ceilings race concurrent lands, bulk baselines hide a rule, abandoned producers | T-1363 (a failed coverage run overwrote a good stamp and lowered ratchet floors), T-1236 (deflation guard), T-1676, T-4007 (strictness changed with no durable record), T-4633 and T-4671 ("five-ticket ratchet-race regression chain": a committed SYS111 ceiling raced every land), T-3228, T-3279, T-2595; v1 frob-ratchet.lock.json holds 5,689 entries of which 5,660 are one rule (DOCARCH002) baselined on one day (2026-09-19) | DESIGNED | the land ratchet avoids the committed-ceiling race by comparing against the base tip (BUILT, ~QAFRXM3, rules.md 6, land.rs `verify_check`). The tracked pools (`frob-ratchet.lock.json`, exceptions.md 2-3, "pools only shrink", RETIRED keys dropped) and a coverage stamp (boundaries.md, one table cell) are designed but unbuilt and unticketed. P-18 | partial |
| F-13 | Release version desync, non-monotonic version, version parse truncation, changelog regeneration conflicts | T-0992 (two incidents), T-1078 (quartet desync), T-1760, T-1769, T-1810, T-4270 (pre-release suffix truncated), T-5034, T-2445 and T-2462 (every land wrote CHANGELOG and version), T-2615, T-2642 | BUILT | per-ticket fragments `changelog.d/<ULID>.<type>.md` (REL003), REL001/REL002, `release cut` is the only bump and refuses downgrades, semver crate parsing (v2/crates/frob-release/src/bump.rs `allow_downgrade`, Cargo.toml `semver = "1"`) | yes |
| F-14 | Shared global config or skills synchronised from a stale checkout reverts a sibling's fix | T-3408, T-2386, T-2384 | DROPPED-ON-PURPOSE (inferred) | v2 has no sync-claude-config or sync-skills verb (verb list: schema, doctor, init, config, lease, board, ticket, milestone, cycle, release, work, start, requeue, test, ack, graph, check, land). The drop is implied by D36 milestone-1 scope, not recorded; see open question 6 | n/a |

### Tier 2: wrong gate decisions (F-15 to F-24)

| Rank | Failure class | v1 evidence | Status | v2 evidence | Prevented |
|---|---|---|---|---|---|
| F-15 | Truncated, partial or failed measurement reads as clean (tool stage, partial parse, budget) | T-1703 (post-land sweep CLEAN on a dirty tree), T-2235 (`--budget` silently dropped whole gate families, 41 errors became 3), T-2456, T-2713, T-2793, T-3001, T-3204, T-4315, T-0905 (partial parse dropped symbols), T-1664, T-2091 | BUILT | no `--budget` (rules.md 4 "Removed"); a tool stage that cannot run or times out is TOOL001, a required Unresolved (v2/crates/gob-check/src/tools.rs, rules.rs; ~APQCEPT); partial-parse files are Unresolved or NotApplicable (~5NFTK3H); default `fail_on_unresolved = required` (gob-check/src/config.rs). Residual: F-16 | yes for tools and parse |
| F-16 | A rule whose evaluation failed returns zero findings ("not evaluated" is only a log line) | same family as F-15; T-1664 "never silently pass when they cannot analyse" | MISSING | 10 sites in v2/crates/frob-check/src/product.rs and snapshot.rs turn `Err` into `Vec::new()` plus `tracing::warn!` (TICK001/003, TICK004, TICK005, PM034, PM001/002, PM013, PM033). Probe SB-4: with a corrupt ticket index `frob check` exits 0, `ok: true`, zero findings, no warning in the envelope. ~YPRBJPF is about NotApplicable reasons, not failures; ~KAD47SZ (new, slice C) covers unreadable files only | no |
| F-17 | Ratchet is count-blind or attributes by file not diff: a second identical finding hides behind the first | T-3132 (pre-land gate attributed findings to the file, not the diff), T-4633 and the SYS111 `accepted_count` ceilings exist because counts mattered | MISSING | v2 land builds a `HashSet` of base fingerprints and calls a head finding pre-existing when its fingerprint is present (v2/crates/frob-land/src/ratchet.rs `verdict`); the fingerprint is (rule, anchor, message with numbers and whitespace removed), proven by test `fingerprint_ignores_numbers_and_whitespace_but_not_anchor` (v2/crates/gob-rules/tests/derive.rs). A ticket that adds a second finding with the same rule, anchor and normalised message is invisible. SB-9 | no |
| F-18 | Land guard fails open or orphans other tickets' evidence (deleted or renamed test; collection failure) | T-1946, T-2017, T-2060, T-2066, T-2255 (fails OPEN on collection failure; floor 35 to 59), T-2256, T-2275 | DROPPED-ON-PURPOSE | evidence is an immutable event with a commit; Unmeasured on a terminal ticket is never a finding (tickets.md 9, architecture.md 3), so deleting a test cannot orphan history. Land verify errors propagate (`?`) rather than being swallowed (land.rs `verify_check`) | yes |
| F-19 | Same commit, different gate answer (cache or concurrency nondeterminism); lease cross-talk | T-4343 (five runs at one commit: three reported 3 errors, two reported 1), T-3249, T-2191, T-2204, T-2585 (REDUNDANT_RERUN asserts "cannot differ" from the tree hash alone), T-0766 | BUILT | per-file results keyed by content digest, rule version, side-input digest and engine; no shared mutable derived lock; atomic SQLite rows (gob-cache). No test runs N concurrent checks at one commit and compares the sets: P-17 | yes (structure), untested |
| F-20 | Cross-ticket leakage, passenger code and scope false refusals (denominator confusion) | T-1390 (every land needed `--allow-cross-ticket`), T-1370, T-1356, T-1618 (a dropped sibling's code rode along and deleted 55 live waivers), T-2082, T-2711, T-3882/3883, T-4050 (five defects, one unanswered question), T-4120, T-4140, T-4271, COV002 grace-window chain (T-0214, T-0320, T-0564, T-0590, T-0965, T-1582) | BUILT | lease overlap plus SCOPE001 over the ticket diff; ledger directory, `frob.lock`, own fragment and generated lockfiles exempt (~SF903MG, ~FJT8C2Q, ~YP2Y2R3, ~CTKE1J4, ~8C6Y5DZ, all done); one ticket per worktree; base is merged in, never squashed. Tests in v2/crates/frob-lease/tests/lease.rs (`scope001_flags_outside_paths_only`, `shared_files_are_exempt`, `two_tickets_each_leasing_their_own_fragment_do_not_conflict`). B structural bug 5 | yes |
| F-21 | Touched-set test selection under-approximates (mocks faking a changed signature) so evidence omits the broken test | T-4643, T-4644 (still queued in v1), T-4151 (text scan where a call graph was needed) | MISSING | v2/crates/frob-tests/src/select.rs: reach over `affects` and unique-name calls, widened to same-file functions for non-function items; no fallback when a changed public function is only referenced by name inside test doubles. Not worth more than a low ticket: P-20 | partial |
| F-22 | Forced overrides without reason or audit; gate gaming (kind change dodges BUG002, acceptance weakened, evidence rebound silently) | T-1762 (every `--force` family), T-1616, T-1422, T-1733; force-overrides.jsonl | BUILT | `--no-evidence`, `--no-changelog`, `--steal` all require `--reason` and write an `evidence-bypass`, `changelog-exempt` or lease-history event; field and acceptance changes are events with old and new values and `moved` maps (tickets.md 2a); test `append_writes_land_and_bypass_and_refuses_create`, `missing_evidence_refuses_unless_bypassed_with_a_reason` | yes |
| F-23 | Deferred verification: rapid debt, post-land sweeps, watermark, quarantine breaker, attribution bisect | 3,384 rapid-debt lines over 1,215 tickets; 1,153 sweep-filed regression tickets; T-2312, T-3051, T-3082, T-3378 quarantine deadlocks; T-2324, T-3886 drain spins forever; T-2997 rapid-debt.jsonl grows unbounded | DROPPED-ON-PURPOSE | rules.md 6 and 7: land runs the full check synchronously; "the deferred-verify machinery (queue, watermark, coalescing worker, bisect ladder, backpressure, rapid debt) is not built"; D36. Risk: if land gets slow the pressure returns: P-22 | n/a |
| F-24 | Close with disclosed unfinished work erases it (follow-up never filed) | T-1648 (T-1420 and T-1204 closed with 54 and 47 warnings unowned), T-2738 | MISSING | no done requirement relates disclosed gaps to follow-up tickets (v2/crates/frob-evidence/src/done.rs `DoneRequirement` set: criteria, children, objective, docs, fragment). Low: P-21 | no |

### Tier 3: availability (F-25 to F-35)

| Rank | Failure class | v1 evidence | Status | v2 evidence | Prevented |
|---|---|---|---|---|---|
| F-25 | Lock deadlocks, dead-holder locks, starvation | derived.lock chain T-0918, T-0933 plus three duplicate reports T-0934, T-0939, T-0944 (dropped), T-0981, T-0982, T-1224; T-1356, T-1370, T-1433 (futex), T-1619, T-1634, T-2155 (a dead pid deadlocked 4 lands for 25 minutes), T-3296, T-3378 | BUILT | no derived-state lock (rules.md "Removed: ... the derived-state lock"; architecture.md 9 "no locks of our own around derived state"); land and lease locks are `flock` (kernel releases on death): v2/crates/frob-land/src/lock.rs, frob-lease/src/store.rs with a 5 s `lock_timeout_ms`; tests `lock_contention_refuses_retryably_naming_the_holder`, `concurrent_overlapping_globs_grant_exactly_one`, `admission_count_and_acquire_are_one_critical_section`. Open sub-items: unfair lease waits ~3WMXBBJ (todo), land FIFO (B PT-17), P-16 | yes |
| F-26 | Lease leaks and orphans: close or fail leaves the lease; terminal ticket's lease blocks work and archive; no release path; one corrupt lease blocks all | T-1050/T-1131, T-1743, T-1789, T-2007, T-2175 (error said a process holds it when none did), T-2271, T-3259, T-4172, T-4342/T-4348/T-4404 (orphaned lock files), T-4383, T-4388, T-4684; force-overrides entries 2 and 3 (112 tickets) | DESIGNED | tickets.md 3: "Leases release automatically on every terminal transition and on `requeue`". Code releases only in `requeue` (frob-worktree/src/work.rs:147,350) and `land` (land.rs `release`). `ticket close` and `drop` leave the lease; there is no release verb (~992AN0Q removed the remedy that named one); a garbage lease file fails every lease verb. SB-2 and SB-5. Contradicts A S-20 and B structural bug 32 | no |
| F-27 | Orphaned worker processes, forkserver leaks, swap exhaustion | T-2443 (94 orphans, 17 GB swap), T-2849 (about 150 reaped by hand), T-2880, T-3072, T-3106, T-3139, T-3407, T-4686, T-2517, T-2818 | BUILT | no process pools: rayon threads (architecture.md 9, rules.md "Removed: the forkserver pool"); `gob-exec` runs each child in its own process group and kills the group on timeout (test `timeout_leaves_no_grandchild`); GC pass removes abandoned `land-base-*` checkouts (architecture.md 3). Residual: F-28 | yes |
| F-28 | Children survive the death of their parent (SIGKILL, harness timeout) | T-2849, T-2880 (PDEATHSIG fix "loaded but forkservers still leak"), T-2991 | MISSING | v2/crates/gob-exec/src/runner.rs `cmd.process_group(0)` and `kill_group` only on timeout; nothing kills the group when frob itself is killed, and drain threads join after a kill so a grandchild that escaped the group and holds the pipe blocks `collect`. P-15 | partial |
| F-29 | No machine-wide admission: N concurrent full checks each size to all cores and memory | T-2473, T-3256 (six concurrent checks, zero free memory), T-3287 (per-worktree admission registry), T-6604; memory note frob-v2-disk-guard (disk filled 3 times) | DESIGNED | architecture.md 9: "Memory admission from v1 is kept in spirit: the pool size is reduced when MemAvailable divided by a per-task estimate is lower than the core count". Not built (grep for MemAvailable or sysinfo: nothing); the semaphore in v2/crates/gob-exec/src/semaphore.rs is per `Runner`, per process; unticketed in v2. Siblings: B PT-8, C P-17 | no |
| F-30 | SQLite "database is locked", WAL sidecar races, first-open races | T-0029, T-0122, T-0232, T-1423, T-3130, T-3607, T-3634, T-4282, T-4389, T-4412 (11 tickets) | TICKETED | WAL, 5 s busy_timeout, immediate-transaction migration, best-effort writes, null-cache fallback (gob-cache/src/lib.rs); ~CE69AVN (todo): the two-process fresh-cache test fails about 1 in 3, so lossless concurrent first open is unproven (A S-14) | partial |
| F-31 | CAS starvation: bounded retries with no backoff fail under fleet load | T-1423, T-2937 (new blocked 5 minutes behind a land), T-3270 | MISSING | v2/crates/gob-git/src/ledger.rs `commit_paths_with` retries `cas_retries` (5) times immediately; land has full jitter (`jitter`) but ledger writes do not. Probe SB-6: 24 concurrent `ticket new` on a 12-core host: 14 succeeded, 10 exited 3 `E-LEDGER-CAS` (retryable, no loss). 8 and 12 concurrent were clean. P-12 | partial |
| F-32 | CI and platform hangs (suite aborts, silent 99 percent stalls, Windows rounds) | T-0692, T-2980, T-3192, T-3250, T-3420, T-3540, T-3560 (round 3), T-3577, T-3589 (round 6), T-3608, T-4028, T-4274, T-4353, T-5228 | BUILT | `.config/nextest.toml` terminate-after hang guard (120 s) with reviewed per-test overrides, `timeout-minutes` on every workflow job, CI005 designed (cicd.md); `File::try_lock` on all platforms so locks cannot silently no-op (v1 T-2918); Windows CI exists. Open: ~Z9C6V0F, ~EDPHHFS (see F-43) | yes |
| F-33 | Perf-induced hangs and unbounded scans (per-ticket `git log --follow`, regex on large bodies, a 1,268 s stage under a 480 s budget) | T-1677, T-2715, T-5131 (flow hung 10+ minutes), T-5153, T-5160, T-3731, T-0887, T-0938 (`doable` over 120 s at 1,245 tickets) | TICKETED | SQLite index and linear-time regex by construction; cold check 29 s with 20 s in file rules (~AKMV3C3 todo), warm graph assembly (~36ZXTMR in progress); B structural bug 30 watches the reversal of `--budget` | partial |
| F-34 | Partial multi-step operations left half done (work: lease then transition; close; land after the CAS; reconcile mid-land) | T-0456, T-2026, T-2046, T-2291, T-2292 (reconcile requeued a LIVE ticket mid-land), T-3050 (auto-heal committed a false done), T-1554 gap 3 | MISSING | land resumes by rerun (analysis in F-02) but `Ledger::append` of the `land` event is not idempotent, so a crash between the `land` event and the close adds a second `land` event on resume; `work` takes the lease before the in-progress transition, a crash between them leaves a lease with no in-progress ticket until TTL (2 h); no test injects a kill at any step and `doctor` has no "stranded state" report (lease without ticket, in-progress without lease, done with unmerged branch). P-09 | no |
| F-35 | The land lock is held while waiting and re-checking | T-2774 (SIGKILLed mid work: the guard bounded only the wait), T-3270, T-3050 | MISSING | land.rs `publish` takes `LandLock` once and holds it across the whole stale-retry loop, including `std::thread::sleep(pause)` and a full `verify_check` re-run in `recover_stale`; other lands wait on a lock whose holder is sleeping. P-16 | partial |

### Tier 4: usability (F-36 to F-45)

| Rank | Failure class | v1 evidence | Status | v2 evidence | Prevented |
|---|---|---|---|---|---|
| F-36 | Log or debug output on stdout corrupts `--json`; debug spam | T-2484, T-2486, T-2979 (default output is debug spam), T-3809 (traceback dropped), B structural bug 29 | BUILT | tracing writes to stderr only (v2/crates/gob-log/src/init.rs `with_writer(std::io::stderr)`); probe: `ticket list --json` stdout parses as one JSON document with a warning on stderr | yes |
| F-37 | A flag, field or config key is parsed and silently dropped | T-2004, T-2387, T-2390, T-3081 (`points` dropped by `new`), T-0839, T-1968, T-0269, T-2216 | BUILT | typed `Command` derive, `TicketField` derive (~A7J9FD5), `deny_unknown_fields`. Probes: `ticket new --points 5 --scope --label --acceptance` all persisted; `update --set bogus=1` refused with the settable list; an unknown `[check]` key refused with a suggestion. Cosmetic: `points=banana` says "got -1" | yes |
| F-38 | Changelog generation churn, duplicates, land-owned file conflicts | T-2615, T-2641, T-2642, T-3489, T-3545, T-4325, T-1994, T-2445 | BUILT | see F-13: own fragment per ticket, always in scope | yes |
| F-39 | Remedies name commands that do not exist; null remedies; hand-edit recipes | T-1636, T-0458, T-1882 (renumber with no args renumbers everything) | TICKETED | ~992AN0Q done (remedies tested against the CLI registry), ~S4GVE49 todo (structured remedies). Probe found two null remedies: `E-GIT-LOCAL-EDITS` and `E-LEDGER-INDEX`; folded into P-04 and P-08 | partial |
| F-40 | Worktrees and build output accumulate until the disk fills | T-2261 (107 worktrees, 67 GB, 95 idle), T-0457; v2 disk filled 3 times (memory frob-v2-disk-guard) | BUILT | ~BZXZK29 throttled GC in work and land; removes only clean, merged-or-pushed worktrees, never `--force`, branch deleted only when merged (frob-worktree/src/gc/worktrees.rs; tests/gc.rs, 721 lines) | yes |
| F-41 | History rewrite or edited events go undetected (append-only is a convention) | T-1762, T-4143 (agents hand-edited the ledger), T-0537 (terminal to non-terminal regression lint) | DESIGNED | tickets.md 2a "never edited afterwards" and "deleting history is visible as a deletion"; TICK001 re-folds frontmatter but no rule flags a modified or deleted existing event file (rules.rs has TICK001 to TICK005 only); `scrub` events legitimately rewrite. P-19 | partial |
| F-42 | Writes resolved from cwd land in the wrong checkout or capture a stale worktree | T-0131, T-1674, T-3983, T-4085, T-4002 | BUILT | repository from the git common dir, never cwd (tickets.md 2, Writer story); leases under the common dir; B structural bug 3 | yes |
| F-43 | Platform semantics: locks no-op, POSIX-only regex on lease records, verbatim paths, separators | T-2918, T-3661, T-3664, T-3820 (os.replace WinError 5 under concurrent access), T-4404 | TICKETED | ~EDPHHFS (in progress), ~Z9C6V0F (todo), ~ATR5EP7 path-discipline epic (todo); locks are portable. Unprobed: lease file rename while another process reads it (open question 5) | partial |
| F-44 | Mutation or fixture harness leaves mutants on disk; stale backup journal restore clobbers live edits | T-0857, T-1327 | MISSING (no ticket warranted) | v2 has no mutation harness; C P-24 proposes cargo-mutants evidence. Carry the lesson into that ticket: journal originals, refuse restore over changed files | n/a |
| F-45 | Ledger ref rewritten or force-pushed; trunk protection unknown | v1 force-overrides, T-1762 | TICKETED | ~ZK2SR2P (doctor and a TICK rule check ledger-branch protection through the hosting API) | partial |

### Status tally (45 classes)

| Status | Count | Classes |
|---|---|---|
| BUILT | 16 | F-01, F-02, F-03, F-13, F-15, F-19, F-20, F-22, F-25, F-27, F-32, F-36, F-37, F-38, F-40, F-42 |
| TICKETED | 7 | F-08, F-11, F-30, F-33, F-39, F-43, F-45 |
| DESIGNED | 5 | F-06, F-12, F-26, F-29, F-41 |
| DROPPED-ON-PURPOSE | 3 | F-14, F-18, F-23 |
| MISSING | 14 | F-04, F-05, F-07, F-09, F-10, F-16, F-17, F-21, F-24, F-28, F-31, F-34, F-35, F-44 |
| Total | 45 | |

## 3. Proposed tickets

Ordered by priority. Every acceptance is a regression test. "Probe" means the failure was
reproduced in this pass (section 4). Overlap notes name sibling-slice proposals so they are not
filed twice.

### P-01: ticket.md fence injection: frontmatter text containing a line `+++` makes the ticket unreadable
- Type: bug. Priority: critical. Covers F-04. Probe SB-1.
- Why: v1 T-1536 ("a Done-report line byte-identical to a ledger marker forged a section boundary and corrupted a neighbour", whole-store load broke) and T-1541 (audit of every free-text entry point) are the same class. v2 removed v1's markers but `split_fenced` closes the frontmatter at the first line whose trimmed text is `+++`, and `toml::to_string` writes multi-line strings as `"""` blocks that may contain such a line. A title, persona, outcome text or acceptance text with a `+++` line writes an unparseable `ticket.md`; the next index rebuild skips it ("skipping unreadable ticket while indexing") so `ticket show` answers E-TICKET-NOT-FOUND; `ticket doctor --fix` reports E-DOCTOR-UNREADABLE and repairs nothing. The events are intact, so the fold can always restore it. The same `fenced` helper writes milestone and cycle objects.
- Fix shape: render frontmatter so no physical line can equal the fence (escape newlines in basic strings or pick a collision-free fence), refuse control characters in single-line fields (title, labels, scope, aliases) at write, make `doctor --fix` and `reconcile` re-render `ticket.md` from the fold, and make TICK001 fire on an unreadable ticket.
- Acceptance:
  - Given a title, persona, outcome text and acceptance text each containing a line `+++`, When created through `ticket new` and `ticket update`, Then the ticket round-trips: delete `.frob/`, run `ticket show`, the text is returned intact.
  - Given property-test strings drawn from arbitrary Unicode including `+++`, `\r\n`, `---` and `"""`, When any text field of Ticket, Milestone or Cycle is rendered and parsed, Then the value is identical.
  - Given an already corrupt `ticket.md` (frontmatter terminated early), When `ticket doctor --fix` runs, Then the file is re-rendered from the events and a `scrub`-style audit event records it; `frob check` reports TICK001 before the fix.

### P-02: gob-fs write_atomic and validated, atomic, precondition-checked `--fix`
- Type: bug. Priority: high. Covers F-05. Overlap: B PT-5 (read-only verbs leave tree unchanged; fixes only in scope), ~R5QDX7H (scope).
- Why: v1 T-1900 corrupted a tracked design file on every land (six repair commits), T-3526 left a killed `check --fix` half-applied, T-5289 deleted wrong lines from a stale snapshot, T-6535 corrupted Python. v2 `gob-check/src/fix.rs` has the same ingredients: truncate-then-write, ranges from check time with no digest precondition, no re-parse, `applied` recorded before the edit and kept when an edit is "skipped as out of range", partial multi-file writes with no rollback. Separately there are at least eight hand-rolled tmp-and-rename copies (lease store, gob-lock, evidence store, release bump, GC stamp, grimble ack, trust key, release lib) and several direct writers (fix.rs, grimble fmt, init, config materialize, checkout sync); extract one helper (project rule: no duplication) and use it everywhere an authoritative or user file is written.
- Acceptance:
  - Given a fault-injection hook that aborts after N bytes, When any writer using `write_atomic` is killed, Then the target is wholly old or wholly new, never truncated (test per writer).
  - Given a file edited between the check and `--fix`, When `--fix` runs, Then the fix is refused with E-FIX-STALE naming the file and nothing is written.
  - Given a fix whose edits produce text that no longer parses in its language, When applied, Then it is rolled back and reported as failed, not applied.
  - Given a fix with one out-of-range edit, When applied, Then the whole fix is skipped and not listed in `applied`.
  - Given a two-file fix where the second write fails, When applied, Then the first file is restored.

### P-03: `ticket close` and `ticket drop` release the lease; terminal leases are reaped
- Type: bug. Priority: high. Covers F-26. Probe SB-2. Contradicts A S-20 and B structural bug 32.
- Why: tickets.md 3 says leases release on every terminal transition; only `requeue` and `land` do. After `ticket close` of an in-progress ticket the lease persists, `lease list` still shows it, a second `start` by the same holder fails with E-LEASE-WIP (limit 1), and the only remedy offered by `requeue` ("frob ticket reopen") is nonsense for a done ticket. Any frob verb run from that worktree renews the heartbeat, so the 2 h TTL may never fire. This is v1's lease-of-a-terminal-ticket class (T-1050, T-4684, T-2031, T-4172) and forced two archive overrides covering 112 tickets.
- Acceptance:
  - Given an in-progress ticket with a live lease, When `ticket close` or `ticket drop` completes, Then `lease list` no longer shows it and the same holder can `start` another ticket.
  - Given a lease file whose ticket is terminal in the ledger (left by an older binary), When any lease verb runs, Then it is pruned with an info log naming the ticket.
  - Given a heartbeat from a verb run in the lease's worktree, When the ticket is terminal, Then the heartbeat does not renew it.

### P-04: surface checkouts a ledger commit could not sync, and flag tracked-ledger drift
- Type: bug. Priority: high. Covers F-07. Probe SB-3.
- Why: v1 T-0505 and T-2563 ("verb success message true, effect unreachable"), T-1432 and T-2274 (staged or dirty content swept into a commit), and the DirtyMain chain (T-1698, T-1699, T-1936, T-2026, T-2671, T-2714). `commit_paths` reports `unsynced` checkouts but `Ledger::commit_events` drops them. With a local edit in the primary checkout's `tickets/<id>/ticket.md`, a worktree's `ticket comment` returned `ok: true, warnings: []` and left the new event file staged-deleted in the primary; a `git commit -a` there silently reverts the ledger commit. `E-GIT-LOCAL-EDITS` carries `remedy: null`.
- Acceptance:
  - Given a primary checkout with a local edit to a ticket path, When a linked worktree writes an event to that ticket, Then the envelope `warnings` name the primary checkout, the paths and a one-line remedy, and the exit stays 0.
  - Given a primary checkout whose `tickets/` index or worktree differs from the ledger ref tip, When `ticket doctor` runs, Then it reports `stale-ledger-checkout` with the same remedy; `doctor --fix` restores only paths whose content equals a previous tip.
  - Given `E-GIT-LOCAL-EDITS`, Then the refusal carries a non-null remedy.

### P-05: an evaluation error is Unresolved, never zero findings
- Type: bug. Priority: high. Covers F-16. Probe SB-4. Sibling: ~KAD47SZ (unreadable files); this ticket generalises to every rule producer.
- Why: v1 T-1664 ("semantic checks must report UNRESOLVED, never silently pass when they cannot analyse"), T-1703, T-2235, T-3204. Ten call sites in `frob-check/src/product.rs` and `snapshot.rs` log "not evaluated" and return no findings (TICK001/003, TICK004, TICK005, PM034, PM001/002, PM013, PM033). With a corrupt ticket index `frob check` printed `ok: true`, zero findings, exit 0.
- Acceptance:
  - Given an unreadable ticket index, unreadable pm config or unreadable milestones, When `frob check --json` runs, Then each affected rule yields a required Unresolved finding (reason `evaluation-failed`, naming the rule and the error) and the run fails under the default `fail_on_unresolved`.
  - Given a lint over rule producers, When a producer maps `Err` to an empty vector without emitting a finding, Then CI fails (an inventory test over `product.rs`, `snapshot.rs` and the sibling adapters).
  - Given the report, Then the count of not-evaluated rules appears in the envelope summary.

### P-06: the land ratchet counts findings, not only fingerprints
- Type: bug. Priority: high. Covers F-17. Probe SB-9 (code and the existing fingerprint test).
- Why: v1 needed `accepted_count` ceilings (SYS111) and wrote T-3132 because attribution by file rather than diff let new findings hide. v2 `verdict` marks a head finding pre-existing when its fingerprint is in the base set; the fingerprint strips numbers and whitespace, so a second finding with the same rule, anchor and normalised message is classified pre-existing and never blocks.
- Acceptance:
  - Given a base with one finding F in file X and a ticket that adds a second finding with the same rule, anchor and message modulo numbers, When `frob land` runs, Then it refuses naming "count grew 1 to 2 for F" and lists the new occurrence.
  - Given a ticket that fixes one of two identical findings, Then land reports one resolved and passes.
  - Given a base cache written by an older format, Then it is ignored and recomputed (versioned `BaseSet`).

### P-07: key the land base-set cache by engine and configuration
- Type: bug. Priority: medium. Covers F-10. Probe SB-8 (code).
- Why: v1 T-0798, T-2723 and T-4159 are one class: a cached gate result reused across an engine change. v2 fixed it for gob-cache (~1EZ3QHP, `engines_never_share_findings_or_repo_rules`) but `frob-land/src/ratchet.rs` caches the base finding set at `<common>/frob/land-base/<oid>.json` keyed by the commit alone.
- Acceptance:
  - Given a base set cached under engine fingerprint A, When land runs under engine B (different binary or rule version) at the same oid, Then the base is recomputed.
  - Given a changed `frob.toml` check table at the base oid, Then the cached set is not reused.
  - Same-engine reruns still hit the cache (the second-land-on-same-base test `a_second_ticket_on_the_same_base_reuses_the_shared_base_set_without_a_base_check` stays green).

### P-08: self-heal a corrupt ticket index; keep busy and corrupt apart
- Type: bug. Priority: medium. Covers F-09. Probe SB-4.
- Why: v1 T-0019 and T-0141 added recovery for a corrupt `cache.db`; T-1416 and T-4412 then showed that treating a concurrency error as corruption destroyed a shared cache. v2 `.frob/tickets.sqlite` is declared delete-safe but a non-database file makes every ticket verb fail with E-INTERNAL "file is not a database" (remedy null), and gob-cache turns an unopenable `cache.sqlite` into a permanent null cache without a notice.
- Acceptance:
  - Given `.frob/tickets.sqlite` replaced with garbage, When `ticket list` runs, Then a warn names the quarantined file (renamed `.corrupt-<ts>`), the index is rebuilt and the list is correct.
  - Given a second process holding a write lock (SQLITE_BUSY), Then no file is renamed and the reader waits or fails retryably.
  - Given a garbage `cache.sqlite`, When `frob check` runs, Then the file is quarantined and recreated, and `doctor` reports the event; `null cache` is a visible state in `doctor`.

### P-09: fault-injection suite for work, close and land, plus idempotent land event and a stranded-state report
- Type: task. Priority: medium. Covers F-34, F-02. Overlap: C P-05 (stranded branches), ~CKZS2R3 (unmerged close).
- Why: v1 land-checkpoint-durability.md names a window never tested with a real SIGTERM (T-1554); T-0907 and T-1495 were the cost of untested unwinds. v2's design is resumable but unproven: the `land` event is not idempotent (resume adds a second), `work` takes the lease before the in-progress transition, and `doctor` cannot list a lease without an in-progress ticket, an in-progress ticket without a lease, or a done ticket with an unmerged branch.
- Acceptance:
  - Given a kill injected after the fast-forward, after the `land` event, before the close, and during worktree removal, When `frob land` is rerun, Then the ticket ends done once, with exactly one `land` event, the lease released and no data lost (one test per kill point, using a hook between steps).
  - Given a kill between lease acquisition and the in-progress transition in `work`, When `doctor` runs, Then it reports `lease-without-progress` and `doctor --fix` releases it.
  - Given an in-progress ticket without a lease or a done ticket whose `ticket/<h>` has unmerged commits, Then `doctor` lists each with the command that resolves it.

### P-10: exceptions prune and auto-removal never act on a degraded evaluation
- Type: task. Priority: medium. Covers F-06. Overlap: B PT-11.
- Why: v1 T-1323 (50 PERF waivers stripped by a land snapshot) and T-1579 (55 live waivers deleted by a self-heal, reverted 7597ba37a0). exceptions.md 3 already forbids it; nothing is built or ticketed. Put the v1 acceptance tests on the ticket that builds `exceptions prune` and EXC013.
- Acceptance:
  - Given a run where a tool stage failed, a rule was Unresolved at the site, `--only` skipped the rule, or the rule version bumped, When `exceptions prune` runs, Then it deletes nothing and says why.
  - Given one rule suddenly marking more than a configured fraction (default 10 percent, minimum 5) of its exceptions STALE, Then prune refuses (mass invalidation) and names the rule.
  - Given a land whose diff deletes an exception directive outside the ticket scope, Then land refuses.
  - Given a healthy run below the threshold, Then stale exceptions are removed with one `scrub`-style audit event.

### P-11: close guard `no_open_blockers` (and `lease_free`) as named in tickets.md 3
- Type: bug. Priority: medium. Covers F-08 (remaining part). Probe SB-12. Overlap: ~CKZS2R3 covers unmerged work only; A S-7.
- Why: v1 T-3064, T-3087, T-3092 (done while blocked). tickets.md 3 lists `no_open_blockers` among the guards; the code has none. `ticket close B --outcome done` succeeded while B was `blocked-by` an open ticket.
- Acceptance:
  - Given B blocked-by open A, When `ticket close B --outcome done`, Then it refuses `E-DONE-OPEN-BLOCKERS` naming A; wont-fix, duplicate and invalid outcomes are exempt.
  - Given A becomes terminal, Then closing B passes.

### P-12: jittered backoff between CAS retries in `commit_paths`
- Type: bug. Priority: medium. Covers F-31. Probe SB-6.
- Why: land has full-jitter backoff; the ledger writer retries five times back to back. 24 concurrent `ticket new` failed 10 of 24 with `E-LEDGER-CAS`. Fleets of agents hit this under load (v1 T-1423, T-2937).
- Acceptance:
  - Given the `before_cas` churn hook of gob-git, When 24 writers race, Then at least 99 percent succeed within the configured retry budget (property test over seeds) and the rest exit 3 with `retry_after_ms`.
  - Given a single writer, Then no sleep is added.

### P-13: tolerate a corrupt lease file and add `frob lease release`
- Type: bug. Priority: medium. Covers F-26. Probe SB-5. Sibling: ~992AN0Q removed the remedy that named `frob lease release` because it does not exist.
- Why: v1 T-2342 ("one corrupt entry crashes fleet-wide"), T-1789, T-2175. A garbage file under `.git/frob/leases/` makes `lease list`, `start`, `work` and `land` fail for the whole clone; the only remedy is hand deletion.
- Acceptance:
  - Given a garbage lease file, When `lease list` runs, Then other leases are listed and the bad file appears as a `corrupt` entry naming its ticket id.
  - Given the same, When `start` runs for a ticket whose scope does not overlap a readable lease, Then it succeeds with a warning; a corrupt entry blocks only its own ticket id.
  - Given `frob lease release <ticket> --reason <why>`, Then the lease is removed with an event, whether it is live, expired or corrupt.

### P-14: machine-wide admission control for heavy steps
- Type: feature. Priority: medium. Covers F-29. Overlap: B PT-8 and C P-17 propose the same; file one ticket and merge acceptance.
- Why: v1 T-3256 (six concurrent checks, zero free memory), T-3287, T-2473, and the owner's disk-fill incidents. architecture.md 9 keeps memory admission "in spirit" but nothing implements it and `gob-exec`'s semaphore is per `Runner`.
- Acceptance: as C P-17 (slots under the common dir, FIFO, stale-holder reclaim) plus: Given six concurrent `frob check` runs, Then the sum of rayon threads and child processes stays within the configured machine cap, and MemAvailable below the per-task estimate reduces the pool once with a logged notice.

### P-15: kill the child process group when frob dies; bound drain after kill
- Type: bug. Priority: low. Covers F-28.
- Why: v1 T-2849 and T-2880 (children outliving a killed parent). `gob-exec` puts each child in its own group and kills it only on timeout; a SIGKILLed frob leaves running children, and `collect` joins the drain threads even when a descendant escaped the group and still holds the pipe.
- Acceptance:
  - Given a running child and a SIGKILL of the frob process, Then the child group is gone within 5 s (Linux PDEATHSIG or a supervisor pipe; job object on Windows).
  - Given a timed-out child whose grandchild holds stdout open, Then `run` returns within the timeout plus a grace period.

### P-16: do not hold the land lock while sleeping or re-checking
- Type: bug. Priority: low. Covers F-35. Overlap: B PT-17 (FIFO fairness).
- Why: v1 T-2774, T-3270. `publish` holds the flock across the stale-retry loop including backoff sleeps and a full re-check.
- Acceptance: Given a stale base, When land backs off, Then the lock is released during the sleep and the re-check and reacquired for the CAS; a second land can publish meanwhile (two-process test with the `before_attempt` hook).

### P-17: determinism under concurrency
- Type: test. Priority: low. Covers F-19.
- Why: v1 T-4343 measured three different answers for one commit. Structure should prevent it but nothing asserts it.
- Acceptance: Given N=8 concurrent `frob check --json` runs over one commit of a fixture repository with a warm shared cache, Then all finding sets (fingerprints) are identical; repeat with a cold cache and with a concurrent writer to the cache.

### P-18: invariants for the ratchet pools and coverage floors when they are built
- Type: task. Priority: medium. Covers F-12.
- Why: v1 T-1363, T-1236, T-4007, T-4633/T-4671, T-3228/T-3279 and a 5,660-entry single-rule pool. Put the acceptance on the pool and coverage-stamp tickets before they are written.
- Acceptance: Given a failed or partial coverage run, Then floors and the stamp are untouched; Given any sequence of runs, Then a pool never grows except by an explicit baseline verb with a reason; Given a baseline of more than 500 keys or more than 50 percent of a rule's findings, Then the verb requires a second reason flag and records it; Given a pool entry whose finding is gone, Then it is dropped by `prune` and the drop is an event; Given a producer abandoned (no change to its code globs since the stamp), Then `doctor` says so.

### P-19: ledger event immutability gate
- Type: task. Priority: low. Covers F-41.
- Acceptance: Given a commit on the ledger ref that modifies or deletes an existing `events/<ULID>.toml` other than as part of a recorded `scrub`, When `ticket doctor` or the TICK rule runs in CI, Then it fails naming the commit and file.

### P-20: touched-set selection falls back when only doubles reference a changed symbol
- Type: bug. Priority: low. Covers F-21.
- Why: v1 T-4643 and T-4644 (queued): tests that fake a function signature are not selected.
- Acceptance: Given a changed public function referenced by name only in a test double or mock, When `frob test` selects tests, Then the owning test file is selected or an Unresolved TEST001 names the gap.

### P-21: close with disclosed unfinished work needs a follow-up link
- Type: feature. Priority: low. Covers F-24.
- Why: v1 T-1648: two tickets closed with 54 and 47 unowned warnings.
- Acceptance: Given a done report or comment of subtype `decision` that declares not-attempted work, When the ticket closes without a `discovered-from` or `spawned` link naming a ticket for it, Then the close warns (error under `[pm.done]` requirement `followups_filed`).

### P-22: land wall-time budget as a regression test
- Type: test. Priority: low. Covers F-23 (guard).
- Why: 24 percent of v1 tickets landed with deferred gates because land was too slow (rapid-debt); v2 already lost ground once (~TSK0M4Y: land took about 10 minutes before the shared cache).
- Acceptance: Given the fixture repository of the check bench, When `frob land` runs with a warm cache excluding tests, Then wall time is under the design budget (tickets.md performance table, 5 s) or CI reports the regression against the previous run.

### Top 10 (by severity and unpreventedness)
P-01 fence injection; P-02 atomic validated fixes and write_atomic; P-03 close releases lease;
P-04 surface unsynced checkouts; P-05 evaluation error is Unresolved; P-06 count-aware ratchet;
P-07 engine-keyed land base cache; P-08 index self-heal; P-09 fault-injection suite; P-10 exceptions
prune safety.

## 4. Structural bugs

Failure modes v2 must prevent. "Confirmed" means reproduced with the built binary in a throwaway
repository in this pass; "by reading" means established from source and an existing test. Each
repro is a ready regression test seed.

| Id | Failure mode | v1 evidence | Does v2 prevent it | Evidence |
|---|---|---|---|---|
| SB-1 | In-band fence in `ticket.md` (F-04) | T-1536, T-1541 | NO, confirmed | `frob ticket new --title $'bad\n+++\nrest'` (also `--persona`, `--acceptance`): the file holds `title = """` with a `+++` line; `ticket doctor` says E-DOCTOR-UNREADABLE and `--fix` changes nothing; after `rm -rf .frob`, `ticket list` logs "skipping unreadable ticket while indexing" and `ticket show` returns E-TICKET-NOT-FOUND. 14 other tickets in the same repository were unaffected |
| SB-2 | Lease survives close or drop (F-26) | T-1050, T-4684, T-4172; force-overrides 2 and 3 | NO, confirmed twice | `frob start S` then commit then `frob ticket close S --outcome done --no-evidence --no-changelog --reason x`: ticket done, `lease list` still shows it, `frob start` for another ticket fails E-LEASE-WIP, `frob requeue S` says "done and cannot be requeued" and points at `reopen`. Same for a `frob work` ticket with a worktree. v2 code releases only in work.rs (requeue) and land.rs |
| SB-3 | Ledger commit leaves another checkout stale with no signal (F-07) | T-0505, T-2563 | NO, confirmed | edit `tickets/<B>/ticket.md` in the primary, run `frob ticket comment <B>` from a linked worktree: exit 0, `warnings: []`, `git status` in the primary shows `D  tickets/<B>/events/<new>.toml` and `MM ticket.md`. `commit_paths` returned `unsynced` and `commit_events` discards it |
| SB-4 | Corrupt derived index bricks verbs and `check` reads clean (F-09, F-16) | T-0019, T-0141, T-1664 | NO, confirmed | overwrite `.frob/tickets.sqlite` with text: `ticket list` returns E-INTERNAL "E-LEDGER-INDEX: file is not a database" (remedy null); `frob check --json` exits 0 with `ok: true`, zero findings and no warning (stderr only: "PM013 not evaluated") |
| SB-5 | One corrupt lease file blocks the clone (F-26) | T-2342 | NO, confirmed | write `garbage = [` into a file under `.git/frob/leases/`: `lease list` and `start` fail E-LEASE-FORMAT "remove <path> and rerun" (a hand-edit remedy); `ticket new` still works |
| SB-6 | CAS retries without backoff starve under load (F-31) | T-1423, T-2937 | PARTIAL, measured | 24 concurrent `ticket new` on 12 cores: 14 ok, 10 exit 3 `E-LEDGER-CAS` (retryable, no corruption: `git fsck` shows only dangling commits). 8 and 12 concurrent: all ok. Same-ticket 10-way comment storms (5 rounds): all ok, 50 events present, `doctor` clean, tree clean |
| SB-7 | Non-atomic, unvalidated source rewrite (F-05) | T-1900, T-3526, T-5289, T-6535 | NO, by reading | gob-check/src/fix.rs: `std::fs::write` on the check-time byte ranges, `applied` pushed before the edit, out-of-range edit only warned. Latent while no Deterministic fix ships |
| SB-8 | Base finding set cached without engine key (F-10) | T-0798, T-2723, T-4159 | NO, by reading | frob-land/src/ratchet.rs `BaseSet`/`read_cache` (oid only) |
| SB-9 | Count-blind ratchet (F-17) | T-3132, T-4633 | NO, by reading and test | `HashSet<fingerprint>` in `verdict`; fingerprint test strips numbers and whitespace (gob-rules/tests/derive.rs) |
| SB-10 | Lock held across sleep and re-check (F-35) | T-2774 | NO, by reading | land.rs `publish` holds `_lock` through `recover_stale`'s `std::thread::sleep` and `verify_check` |
| SB-11 | Non-idempotent `land` event on resume (F-34) | T-0456, T-1554 | NO, by reading | `Ledger::append` always writes a new event; `ledger_step` is re-entered by a rerun after a crash between `append_land` and `close` |
| SB-12 | Close ignores open blockers (F-08) | T-3064, T-3087, T-3092 | NO, confirmed | B blocked-by open A: `ticket close B --outcome done --no-evidence --no-changelog --reason x` succeeds (with default guards it fails only for the missing evidence and fragment, not the blocker) |
| SB-13 | Parent death leaves children (F-28) | T-2849, T-2880 | NO, by reading | gob-exec runner: process group set, killed only on timeout |
| SB-14 | `E-GIT-LOCAL-EDITS` and `E-LEDGER-INDEX` have null remedies (F-39) | T-1636, T-3859 | PARTIAL | observed in SB-3 and SB-4 |

Prevented, with evidence (so nobody re-litigates them):

| Failure mode | Why v2 prevents it | Evidence |
|---|---|---|
| Stale snapshot clobbering other tickets (F-01) | per-ticket directories, append-only events, ref CAS, fold equality | tests named in F-01; 24-way and 10-way probes |
| Squash from a stale base reverting landed work, reset of main (F-02) | merge base into branch, then ff-only or `update-ref` with the old value; no unwind code (grep for `reset` in frob-land and frob-worktree finds none) | land tests; land.rs `advance` |
| Id collisions and drafts (F-03) | ULIDs | ledger tests |
| Staged or dirty index swept into ledger commit | tree built from the ref tip | `staged_unrelated_file_is_untouched` |
| Reopening a ticket stranding forked worktrees (T-4287) | ledger is not branch-local; a land carries no ledger diff (tickets.md 2) | design |
| Derived-state lock deadlocks and dead-holder locks (F-25) | no derived lock; kernel `flock` | rules.md, lock tests |
| `--json` polluted by logs (F-36) | stderr logging, single renderer | probe |
| Forkserver orphans (F-27) | no process pools | architecture.md 9 |
| Silent flag, field or config drops (F-37) | typed derives, deny unknown | probes |
| Release version desync (F-13) | fragments plus `release cut`, REL002, downgrade refusal | frob-release/src/bump.rs |

## 5. Open questions

1. Binary currency: probes used the debug binary of 2026-10-04 00:46. Re-run SB-1 to SB-6 and SB-12
   against HEAD before filing; ~CKZS2R3 (in progress) may change SB-12's neighbourhood.
2. P-01: escape or refuse? Refusing newlines in title, labels, scope and aliases is simple and
   matches how they render; multi-line fields (persona, outcome text, acceptance text, body)
   need an escape or a collision-free fence. Owner call on whether existing ledgers need a
   migration (`ticket doctor --fix` re-render is enough for correctness).
3. P-03: should the heartbeat ever renew a lease of a terminal ticket? Reading says any verb from
   that worktree renews; not probed over time.
4. `ref_mode = "branch"` changes F-07 and F-02 (ledger commits ride the ticket branch). All probes
   here are trunk mode, the default. Branch mode needs its own pass.
5. Windows: the lease store renames over a file that readers (`live_snapshot`) may hold open;
   v1 T-3820 and T-4028 hit WinError 5 on the same shape. Not probed. Slice owners with a Windows
   host should run `concurrent_overlapping_globs_grant_exactly_one` with parallel readers.
6. F-14 is classed DROPPED-ON-PURPOSE by inference (no verb exists; D36 scope). If the owner wants
   a global-config sync verb later, T-3408 is the cautionary ticket (a stale worktree reverted a
   sibling's in-flight fix); record the decision in the README log.
7. `frob.lock` is a tracked file that every acking ticket edits. Entries are sorted and stable
   (gob-lock test `save_load_round_trips_and_is_sorted_and_stable`) so disjoint acks merge, but two
   acks inserting at the same position conflict; land refuses non-Cargo lockfile conflicts with a
   hand-merge remedy (E-LAND-CONFLICT). v1's `frob.lock` had 133 commits of churn. Not probed; a
   two-branch concurrent-ack test would settle it.
8. The land `--wait` budget bounds lock wait plus retry time (land.rs `budget`), not the caller's
   own timeout; v1 T-2774 was a SIGKILL by the caller. The resume path makes a kill safe, which is
   exactly what P-09 should prove.
9. CHANGELOG.md and changelog.d were not used as independent evidence because they are generated
   from tickets (and T-2615 recorded 101 duplicated id lines); "fixed more than once" was derived
   from ticket chains instead. Chains found: ids (9 tickets), derived lock (8), orphaned evidence
   (7), DirtyMain (13), truncated sweep (9), forkserver (10), Windows hangs (11), SQLite lock (11),
   quarantine deadlock (5), Tier-A corruption (7), version regress (10).
10. v1 `rapid-debt.jsonl` shows 24 percent of tickets skipped gates because land was slow. v2's
    answer is to be fast; P-22 only guards it. If land regresses, the owner must decide between a
    budget regime (v1's) and removing checks from land, not a quiet return of deferral.

## Appendix A: accounting of the 595-ticket incident corpus

Machine-assisted (title keyword rules) and hand-corrected for about 60 tickets; each ticket is
counted once under its best class. Treat as an index. Ids are `T-` numbers without the prefix. F-99
means v1-internal gate, test, language-support or docs tooling with no v2 analogue, or noise.

| Class | Count | v1 tickets |
|---|---|---|
| F-01 | 50 | 0206 0323 0475 0476 0479 0505 0537 0538 0633 0764 0787 0857 0889 0959 1153 1154 1179 1323 1327 1437 1583 1588 1617 1630 1721 1750 1914 1924 2122 2140 2256 3163 3297 3313 3340 3408 3468 3638 3684 3958 4002 4140 4287 4383 4388 4436 4572 5176 5289 5358 |
| F-02 | 6 | 0907 1495 1522 1634 2189 2714 |
| F-03 | 26 | 0012 0032 0162 0453 0458 0473 0588 0812 0859 1090 1880 1882 1984 2092 2116 2219 2271 2281 2328 2496 2738 2878 3639 5106 5415 6580 |
| F-04 | 5 | 0740 1536 1541 2270 3892 |
| F-05 | 30 | 0450 0455 1155 1326 1424 1548 1559 1640 1751 1775 1799 1803 1853 1900 1903 1911 2036 2078 2284 2521 2721 2884 3526 3677 4235 4379 4913 5347 6535 6594 |
| F-07 | 18 | 1432 1790 1891 1936 2007 2026 2034 2098 2118 2274 2291 2481 2524 3050 3126 3471 4199 4224 |
| F-08 | 9 | 1920 1934 1950 1955 2300 3094 3195 3288 3731 |
| F-09 | 42 | 0019 0029 0122 0141 0243 0248 0347 0457 0517 0570 0798 0918 0933 0934 0939 0944 0981 0982 1148 1224 1416 1423 1810 2165 2723 2797 3130 3217 3607 3634 3820 4159 4257 4282 4389 4390 4412 4444 4450 5808 5814 6598 |
| F-12 | 30 | 0484 1096 1235 1333 1335 1363 1405 1408 1426 1433 1434 1676 1677 2527 2980 3296 3420 3429 3436 3437 3750 3756 4007 4242 4331 4404 4633 4662 4671 5179 |
| F-13 | 32 | 0156 0326 0488 0731 0789 0992 1078 1381 1413 1743 1760 1769 1789 1814 1994 2175 2445 2462 2573 2615 2641 2642 3489 3545 4001 4270 4325 4470 4684 5034 5162 5293 |
| F-14 | 2 | 2384 2386 |
| F-15 | 31 | 0100 0269 0438 0839 0902 0905 0994 1351 1616 1664 1674 1703 1784 2004 2091 2105 2235 2387 2390 2473 2480 2611 3001 3081 3204 3284 3809 4085 4151 4274 4315 |
| F-16 | 2 | 2364 2684 |
| F-17 | 1 | 3132 |
| F-18 | 16 | 0821 1161 1178 1946 2017 2060 2066 2255 2620 3038 3266 4017 4108 4143 6547 6595 |
| F-19 | 5 | 2191 2204 2585 3249 4343 |
| F-20 | 30 | 0214 0241 0320 0564 0590 0965 1331 1370 1390 1582 1645 1855 1868 1966 1993 2082 2177 2351 2561 2711 3080 3404 3724 3882 3883 4121 4271 4453 6548 6609 |
| F-21 | 2 | 4643 4644 |
| F-22 | 1 | 1762 |
| F-23 | 37 | 0463 1694 1698 1699 1702 1710 1716 1728 1841 1873 1952 2312 2324 2342 2478 2595 2671 2713 2938 2997 3025 3051 3065 3082 3083 3220 3222 3378 3379 3431 3459 3470 3635 3886 4553 4560 5784 |
| F-24 | 1 | 4152 |
| F-25 | 51 | 0074 0125 0232 0692 0693 0694 0697 0698 0769 0770 0794 0828 0887 1779 2093 2155 2180 2249 2484 2580 2715 2779 2918 2992 3076 3093 3174 3192 3247 3250 3274 3571 3577 3589 3608 3689 3713 3730 3735 3738 3741 3953 4028 4265 4289 4348 5131 5153 5160 5228 6604 |
| F-26 | 15 | 0431 0456 0766 1347 1356 1619 1806 1875 2222 2556 3319 3422 3661 3983 4120 |
| F-27 | 28 | 0028 0396 0467 0477 0478 1024 1515 2134 2170 2286 2443 2517 2818 2849 2880 2916 2991 3072 3106 3139 3256 3287 3407 4329 4342 4686 6539 6544 |
| F-32 | 19 | 1596 2087 2937 3270 3316 3426 3540 3560 3659 3664 3725 3778 3785 3793 4130 4351 4353 4366 4452 |
| F-34 | 2 | 2046 2292 |
| F-36 | 2 | 2486 2979 |
| F-37 | 2 | 2216 2433 |
| F-40 | 1 | 2261 |
| F-42 | 1 | 0131 |
| F-99 | 98 | 0005 0044 0057 0181 0273 0316 0325 0416 0421 0562 0643 0647 0701 0970 1053 1089 1132 1266 1352 1377 1403 1439 1480 1560 1615 1662 1679 1737 1805 1815 1829 1874 1895 1959 1968 2019 2067 2075 2099 2179 2188 2213 2229 2272 2273 2275 2279 2338 2358 2379 2454 2499 2550 2664 2696 2712 2844 2851 2885 2888 2995 2996 3034 3131 3271 3349 3424 3815 3894 3899 3940 4050 4082 4203 4252 4306 4418 4419 4420 4421 4427 4628 4629 4630 4631 4632 4640 4641 4645 4649 5143 5190 5215 5527 5638 6399 6403 6420 |
| Total | 595 | |

Classes with no v1 ticket in the corpus (F-06, F-10, F-11, F-28, F-29, F-30, F-31, F-33, F-35, F-38, F-39, F-41, F-43, F-44, F-45) were supported by tickets cited in section 2 that the keyword pass assigned to a neighbouring class (for example T-2774 under F-35 sits in F-32 here) or by commits, locks and logs, not by the corpus alone. Class F-25 includes the generic "race or concurrency" titles; F-32 includes pytest and CI timeouts.
